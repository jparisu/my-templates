"""Default CLI entrypoint for {{ project_name }}."""

from __future__ import annotations

import argparse

from {{ package_name }} import __version__


def build_parser() -> argparse.ArgumentParser:
    """Create the default command-line parser."""
    parser = argparse.ArgumentParser(
        prog="{{ project_slug }}",
        description="{{ project_name }} command-line interface.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main() -> int:
    """Run the default CLI entrypoint."""
    build_parser().parse_args()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
