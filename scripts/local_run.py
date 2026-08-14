from __future__ import annotations

import argparse
import json


def main() -> None:
    from ml_platform_core.config import load_run_config
    from ml_platform_tabular import run_task

    parser = argparse.ArgumentParser(description="Run a local ML platform task.")
    parser.add_argument("--task", required=True, help="Path to task config YAML.")
    parser.add_argument("--profile", required=True, help="Path to profile config YAML.")
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        help="Override config value with dotted path syntax, e.g. --set model.name=ridge",
    )
    args = parser.parse_args()

    cfg = load_run_config(args.task, args.profile, overrides=args.overrides)
    result = run_task(cfg)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
