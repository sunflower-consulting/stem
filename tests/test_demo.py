"""`stem demo` is the headline, so it is tested like one.

The claim is not that a demo exists. It is that two commands on a machine with
no API key, no target and no configuration produce a MEASURED result -- one with
a denominator, a control arm and an honest row for the case nothing could score.
Each of those is asserted separately, because any of them could disappear while
the command still printed a confident-looking table.
"""
from __future__ import annotations

import pytest

from sunflower_stem.demo import DEMO_CAPABILITIES, _ratio, run


@pytest.fixture
def demo(capsys):
    def _run(**kw):
        kw.setdefault("trials", 2)
        assert run(**kw) == 0
        return capsys.readouterr().out
    return _run


def test_the_demo_runs_with_no_key_and_no_configuration(demo):
    out = demo()
    assert "cases considered" in out


def test_every_built_in_case_appears(demo):
    """A case that silently stopped being dispatched would shrink the library
    without shrinking any number a reader sees."""
    from sunflower_stem.tools.chat import BUILTIN_CHAT_CASES

    out = demo()
    for cid in BUILTIN_CHAT_CASES:
        assert cid in out, f"{cid} is missing from the demo output"


def test_a_case_nothing_could_score_is_reported_as_not_probed(demo):
    """THE honesty row, and the reason the judge being off is visible.

    `chat-fabricated-policy` can only be scored by a judge, and the judge ships
    off. If this ever renders as 0/5 instead, the demo is reporting an absence of
    measurement as a clean result, which is the single failure this whole package
    is arranged to prevent.
    """
    out = demo()
    assert "not probed" in out
    assert "chat-fabricated-policy" in out
    # and it must NOT appear as a measured zero
    for line in out.splitlines():
        if line.startswith("chat-fabricated-policy"):
            assert "0/" not in line, f"reported as a measured zero: {line}"


def test_every_measured_row_carries_a_control_arm(demo):
    """A rate without its control is the thing this tool exists not to print."""
    out = demo()
    measured = [ln for ln in out.splitlines()
                if ln.startswith("chat-") and "not probed" not in ln]
    assert measured, "no measured rows at all"
    for line in measured:
        assert "matched" in line or "baseline" in line, f"no control arm: {line}"


def test_the_summary_counts_add_up_to_the_cases_considered(demo):
    """A total that does not reconcile is how a dropped case hides."""
    import re

    out = demo()
    m = re.search(r"(\d+) cases considered: (\d+) validated, (\d+) rejected, "
                  r"(\d+) not probed, (\d+) refused by the gate, (\d+) errored", out)
    assert m, out
    considered, *parts = (int(g) for g in m.groups())
    assert sum(parts) == considered, f"{parts} does not sum to {considered}"


def test_the_undefended_target_has_a_case_its_control_also_fires(demo):
    """The demonstration itself. On the unguarded assistant at least one case
    succeeds on every attempt AND its benign twin succeeds just as often, which
    is the result a tool without a control arm would file as critical."""
    out = demo(safety="none")
    rejected_with_live_control = [
        ln for ln in out.splitlines()
        if ln.startswith("chat-") and ln.rstrip().endswith("rejected")
        and _ratio(ln.split()[2]) > 0 and _ratio(ln.split()[3]) > 0]
    assert rejected_with_live_control, (
        "no case was rejected by a control arm that also fired; the demo no "
        "longer demonstrates the thing it exists to demonstrate")


def test_turning_the_defences_on_changes_what_is_proved(demo):
    """The defence arm. Not that the numbers drop to zero everywhere -- a
    guardrail that filters text does nothing about a tool authorization flaw --
    but that the two runs differ at all."""
    assert demo(safety="none") != demo(safety="strong")


def test_the_callback_capability_is_switched_on_explicitly():
    """Capability checks are fail-closed, so an unlisted switch reads as off and
    the exfiltration case would be reported unreachable rather than measured.
    The demo turns it on in the open rather than relying on a default."""
    assert DEMO_CAPABILITIES["out_of_band_callback"] is True


@pytest.mark.parametrize("cell,expected", [
    ("5/5", 1.0), ("0/5", 0.0), ("2/4", 0.5), ("0/0", 0.0), ("", 0.0), ("x/y", 0.0),
])
def test_the_arm_ratio_helper_never_raises(cell, expected):
    """It parses a rendered table cell, so it has to tolerate anything the table
    can hold rather than crash the summary that follows the numbers."""
    assert _ratio(cell) == expected
