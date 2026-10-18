"""The one way out to a model that is not the target.

Driven against a real loopback server rather than a mocked socket, because the
things that have gone wrong here are wire-level: an empty `content` with the
answer somewhere else, a reply cut off at the token cap, a 500 from a server
talking about its own template. A test that stubs the transport cannot see any of
them.
"""
from __future__ import annotations

import json
import threading
import typing
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from sunflower_stem.modelcall import (
    ChatTransport,
    Message,
    ModelCallError,
    ModelReply,
    ScriptedTransport,
)


class _Handler(BaseHTTPRequestHandler):
    # (status, body) queue, plus a record of what arrived. Class attributes rather
    # than instance ones because the stdlib server constructs a fresh handler per
    # request, so there is nowhere per-instance for a test to look afterwards. The
    # fixture clears both, which is what keeps them from leaking between tests.
    script: typing.ClassVar[list] = []
    seen: typing.ClassVar[list] = []

    def log_message(self, *_a):
        pass

    def _respond(self):
        status, body = self.script.pop(0) if self.script else (200, {})
        blob = json.dumps(body).encode() if not isinstance(body, str) else body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)

    def do_GET(self):
        self.seen.append(("GET", self.path, None))
        self._respond()

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode() if length else ""
        self.seen.append(("POST", self.path, json.loads(raw) if raw else None))
        self._respond()


@pytest.fixture
def server():
    _Handler.script, _Handler.seen = [], []
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv, _Handler
    srv.shutdown()


def _transport(srv, **kw) -> ChatTransport:
    host, port = srv.server_address[0], srv.server_address[1]
    return ChatTransport(f"http://{host}:{port}/v1", "test-model",
                         timeout_s=5, retries=kw.pop("retries", 0), **kw)


def _ok(content="hi", **msg) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content, **msg},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 11}}


def test_a_completion_goes_to_the_chat_completions_path_under_the_base_url(server):
    """The base URL carries a prefix (`/v1`) and the path is appended to it. Getting
    this wrong produces a 404 that reads like an unreachable endpoint."""
    srv, h = server
    h.script.append((200, _ok()))
    _transport(srv).complete([Message(role="user", content="q")])
    method, path, body = h.seen[0]
    assert (method, path) == ("POST", "/v1/chat/completions")
    assert body["model"] == "test-model"
    assert body["messages"] == [{"role": "user", "content": "q"}]


def test_the_reply_carries_its_usage_and_raw_body(server):
    """`raw` is not decoration: it is where the truncation signal lives, and a
    caller that cannot see it cannot tell a cut-off reply from a short one."""
    srv, h = server
    h.script.append((200, _ok()))
    reply = _transport(srv).complete([Message(role="user", content="q")])
    assert isinstance(reply, ModelReply)
    assert reply.text == "hi"
    assert (reply.usage.prompt_tokens, reply.usage.completion_tokens) == (7, 11)
    assert reply.raw["choices"][0]["finish_reason"] == "stop"


def test_an_answer_that_arrived_only_in_reasoning_is_still_the_answer(server):
    """gpt-oss returns its turn in `reasoning` with `content` empty. Without the
    fallback every call against it reads as an empty reply."""
    srv, h = server
    h.script.append((200, _ok(content="", reasoning='{"score": 3}')))
    assert _transport(srv).complete([Message(role="user", content="q")]).text == '{"score": 3}'


def test_a_cap_is_sent_by_default_and_removable_on_purpose(server):
    """An uncapped local model can ramble until the timeout; a cap of 512 made a
    reasoning model hit `finish_reason: length` on every call. So there is a
    default, and a falsy value is an explicit escape hatch rather than an accident."""
    srv, h = server
    h.script.extend([(200, _ok()), (200, _ok())])
    t = _transport(srv)
    t.complete([Message(role="user", content="q")])
    assert h.seen[0][2]["max_tokens"] == t.max_tokens
    t.complete([Message(role="user", content="q")], max_tokens=0)
    assert "max_tokens" not in h.seen[1][2]


def test_a_truncated_reply_says_so(server):
    """The only authoritative signal that the model ran out of budget mid-answer.
    What it is for lives in the judge; that it is READ lives here."""
    srv, h = server
    body = _ok()
    body["choices"][0]["finish_reason"] = "length"
    h.script.append((200, body))
    assert _transport(srv).complete([Message(role="user", content="q")]).truncated


def test_a_bad_request_is_not_retried_but_a_rate_limit_is(server):
    """4xx is deterministic, so repeating it only wastes the budget -- except 429,
    which is the one 4xx that means retry."""
    srv, h = server
    h.script.append((400, {"error": "bad"}))
    with pytest.raises(ModelCallError):
        _transport(srv, retries=3).complete([Message(role="user", content="q")])
    assert len(h.seen) == 1, "a 400 must be asked once"

    h.script.clear(); h.seen.clear()
    h.script.extend([(429, {"error": "slow down"}), (200, _ok())])
    _transport(srv, retries=2).complete([Message(role="user", content="q")])
    assert len(h.seen) == 2, "a 429 must be retried"


def test_a_server_error_is_retried_because_ollama_returns_them_on_its_own_template(server):
    """Measured on the reference engine: Ollama intermittently returns HTTP 500
    parsing its own model's tool call. One retry was not enough -- a long run died
    partway through on an upstream hiccup that clears immediately."""
    srv, h = server
    h.script.extend([(500, {"error": "error parsing tool call"}), (200, _ok())])
    _transport(srv, retries=2).complete([Message(role="user", content="q")])
    assert len(h.seen) == 2


def test_an_unparseable_body_is_an_error_and_not_an_empty_answer(server):
    """A proxy returning an HTML error page must not read as a model that said
    nothing, which for a judge is indistinguishable from "did not answer"."""
    srv, h = server
    h.script.append((200, "<html>gateway timeout</html>"))
    with pytest.raises(ModelCallError, match="non-JSON"):
        _transport(srv).complete([Message(role="user", content="q")])


def test_an_unexpected_response_shape_names_itself(server):
    srv, h = server
    h.script.append((200, {"not": "a completion"}))
    with pytest.raises(ModelCallError, match="unexpected response shape"):
        _transport(srv).complete([Message(role="user", content="q")])


def test_an_unreachable_endpoint_is_an_error_rather_than_a_hang():
    t = ChatTransport("http://127.0.0.1:1/v1", "test-model", timeout_s=2, retries=0)
    with pytest.raises(ModelCallError, match="unreachable"):
        t.complete([Message(role="user", content="q")])


def test_the_probe_never_raises_and_says_what_it_could_not_do():
    """It is a reachability check, and a check that throws is one a caller has to
    wrap before it can report anything."""
    result = ChatTransport("http://127.0.0.1:1/v1", "m", timeout_s=2, retries=0).probe()
    assert result["ok"] is False
    assert result["error"]


def test_the_probe_lists_what_the_server_serves(server):
    srv, h = server
    h.script.append((200, {"data": [{"id": "qwen3:8b"}, {"id": "gpt-oss:20b"}]}))
    result = _transport(srv).probe()
    assert result["ok"] is True
    assert result["served_models"] == ["qwen3:8b", "gpt-oss:20b"]
    assert h.seen[0][1] == "/v1/models"


def test_an_api_key_is_read_from_the_environment_and_never_from_an_argument(server, monkeypatch):
    """Nothing secret belongs in a config file or a command line, where it reaches
    a shell history and a process listing."""
    srv, h = server
    monkeypatch.setenv("STEM_TEST_KEY", "sk-secret")
    h.script.append((200, _ok()))
    t = _transport(srv, api_key_env="STEM_TEST_KEY")
    assert t._headers()["Authorization"] == "Bearer sk-secret"
    t.complete([Message(role="user", content="q")])


def test_no_authorization_header_is_sent_when_no_key_is_configured(server):
    """A local Ollama ignores auth, and sending an empty bearer token is how a
    stricter gateway starts rejecting requests for no reason."""
    srv, _h = server
    assert "Authorization" not in _transport(srv)._headers()


def test_the_scripted_transport_records_what_it_was_asked(server):
    """It is what the dry calibration pass runs on, so it has to be inspectable:
    proving a judge prompt never shows the attack means reading the prompt."""
    t = ScriptedTransport("mock-judge-yes", '{"score": 5, "reason": "constant yes"}')
    t.complete([Message(role="system", content="s"), Message(role="user", content="u")])
    assert [m.content for m in t.calls[0]] == ["s", "u"]
    assert t.complete([Message(role="user", content="again")]).text.startswith('{"score": 5')
