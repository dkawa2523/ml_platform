"""CLI for repository quality commands."""

from __future__ import annotations

import argparse

from quality.gates import QualityFailure
from quality.runner import (
    run_fast,
    run_nightly,
    run_pr,
    run_precommit_ruff,
    update_baseline,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("fast", "pr", "nightly", "baseline", "precommit-ruff"))
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()
    commands = {
        "fast": run_fast,
        "pr": run_pr,
        "nightly": run_nightly,
        "baseline": update_baseline,
        "precommit-ruff": lambda: run_precommit_ruff(args.files),
    }
    try:
        commands[args.command]()
    except QualityFailure as exc:
        parser.exit(1, f"quality gate failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
