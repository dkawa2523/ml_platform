from __future__ import annotations

import argparse
import sys
from pathlib import Path


_CLEARML_DIR = Path(__file__).resolve().parent
if str(_CLEARML_DIR) not in sys.path:
    sys.path.insert(0, str(_CLEARML_DIR))

from _entrypoint_bootstrap import add_clearml_entrypoint_paths

add_clearml_entrypoint_paths()

from pipeline_controller import register_tabular_pipeline
from pipeline_plan import build_pipeline_plan, print_pipeline_plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Register or dry-run the ClearML tabular training pipeline graph.")
    parser.add_argument(
        "--task", default="config/tasks/tabular_pipeline.yaml", help="Path to pipeline task config YAML."
    )
    parser.add_argument("--profile", default="config/profiles/clearml-dev.yaml", help="Path to profile config YAML.")
    parser.add_argument("--dry-run", action="store_true", help="Print the pipeline DAG without requiring ClearML SDK.")
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        help="Override config value with dotted path syntax for local dry-run inspection.",
    )
    args = parser.parse_args()

    plan = build_pipeline_plan(task_path=args.task, profile_path=args.profile, overrides=args.overrides)
    if args.dry_run:
        print_pipeline_plan(plan)
        return
    register_tabular_pipeline(task_path=args.task, profile_path=args.profile, overrides=args.overrides)


if __name__ == "__main__":
    main()
