"""CLI entrypoint."""

from __future__ import annotations

import argparse
import sys

from .app import run_score, run_setup


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jobfit",
        description="Evaluate resume-to-job fit and log results to Google Sheets.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("setup", help="Create profile templates and validate configuration.")
    subparsers.add_parser("score", help="Score a pasted job description.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "setup":
        return run_setup()
    if args.command == "score":
        return run_score()

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
