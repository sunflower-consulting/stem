"""The `stem` command.

Subcommands are registered here only once they work. A help listing that
advertises a command which then prints "not implemented" costs a reader more
trust than the missing feature costs them time, and this tool's entire argument
is about not overclaiming.
"""
from __future__ import annotations

import argparse
import sys

from sunflower_stem import __version__


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="stem",
        description="Measure whether an attack on an LLM application actually "
                    "worked, against a control, proved out of band.",
        epilog="Authorized targets only. `stem doctor` reports what this "
               "installation can and cannot prove.",
    )
    p.add_argument("--version", action="version", version=f"stem {__version__}")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    d = sub.add_parser("doctor", help="report what this installation can prove")
    d.set_defaults(func=_doctor)

    lab = sub.add_parser(
        "lab", help="serve the bundled vulnerable chat app on loopback",
        description="Serve the deliberately vulnerable chat application that "
                    "ships with stem. Loopback only, and no model is needed.")
    lab.add_argument("--port", type=int, default=5005)
    lab.add_argument(
        "--safety", choices=("none", "weak", "strong"), default="none",
        help="how hard the app defends itself. Running the same assessment "
             "against 'strong' is the control for the defences themselves: if "
             "the result does not move, the assessment is measuring something "
             "other than what the defences do.")
    lab.add_argument(
        "--model", default="",
        help="use a local Ollama model as the app's brain instead of the "
             "scripted one. Optional, and off by default: the scripted brain "
             "needs no model, no GPU and no network, which is what makes a run "
             "reproducible and what makes the quickstart keyless.")
    lab.set_defaults(func=_lab)
    return p


def _lab(args: argparse.Namespace) -> int:
    from sunflower_stem.lab import serve

    # Loopback is not a flag. This is an application built to be exploitable,
    # and a --host option is how one ends up answering on a laptop's wifi
    # address in a cafe. Anyone who genuinely needs it reachable can forward a
    # port deliberately, which is a decision with a person attached to it.
    srv, _app = serve(port=args.port, safety=args.safety,
                     deterministic=not args.model,
                     **({"model": args.model} if args.model else {}))
    brain = f"model={args.model}" if args.model else "scripted brain (no model)"
    port = srv.server_address[1]
    # flush=True because what follows is serve_forever(): without it the banner
    # sits in a buffer until the process exits, so anyone piping or redirecting
    # the output sees nothing at all while the server is in fact up.
    print(f"lab on http://127.0.0.1:{port}  safety={args.safety}  {brain}", flush=True)
    print(f"  scoreboard: http://127.0.0.1:{port}/api/Challenges", flush=True)
    print("  stop with ctrl-c", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()
        print()
    return 0


def _doctor(_args: argparse.Namespace) -> int:
    from sunflower_stem.doctor import report

    print(report())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
