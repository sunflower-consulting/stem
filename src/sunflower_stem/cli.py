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
    return p


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
