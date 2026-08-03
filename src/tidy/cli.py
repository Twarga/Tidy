"""Tidy CLI entry point.

Phase 0: minimal surface so `tidy --version` works.
Phase 2: full command set (status, add, schedule, backup, serve, tui, ...).
"""

from __future__ import annotations

import argparse
import sys

from tidy import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tidy",
        description="Keep your folders tidy — backup & sync any git repo.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"tidy {__version__}",
    )
    # Phase 2 will register subcommands here.
    parser.parse_args(argv)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
