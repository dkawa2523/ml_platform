from __future__ import annotations

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import argparse
import json

from _bootstrap import add_repo_paths

add_repo_paths()

from ml_platform_core.config import apply_overrides, load_run_config
from ml_platform_tabular import run_task


def main() -> None:
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

    cfg = load_run_config(args.task, args.profile)
    cfg = apply_overrides(cfg, args.overrides)
    result = run_task(cfg)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
