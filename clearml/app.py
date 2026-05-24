from __future__ import annotations

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLEARML_DIR = Path(__file__).resolve().parent
for p in (str(CLEARML_DIR), str(REPO_ROOT / "pkgs/core/src"), str(REPO_ROOT / "pkgs/tabular/src"), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from ml_platform_core.config import apply_overrides, load_run_config
from ml_platform_tabular import run_task

from adapter import ClearMLAdapter, apply_ui_params, default_ui_params
from reports import report_result


def main() -> None:
    parser = argparse.ArgumentParser(description="ClearML task application entrypoint.")
    parser.add_argument("--task", required=True, help="Path to task config YAML.")
    parser.add_argument("--profile", required=True, help="Path to profile config YAML.")
    parser.add_argument("--set", dest="overrides", action="append", default=[], help="Optional KEY=VALUE override before connecting UI params.")
    args = parser.parse_args()

    cfg = apply_overrides(load_run_config(args.task, args.profile), args.overrides)
    clearml_cfg = cfg.get("clearml", {})
    project_name = clearml_cfg.get("project_root", "MLPlatform/Dev")
    task_name = cfg.get("run", {}).get("name", cfg.get("task", "ml_task"))

    adapter = ClearMLAdapter.init(project_name=project_name, task_name=task_name, output_uri=clearml_cfg.get("artifact_output_uri"))
    try:
        connected = adapter.connect_params(default_ui_params(cfg))
        resolved_local_path = None
        if "data" in cfg:
            dataset_file = connected.get("Input/dataset_file") or cfg.get("data", {}).get("dataset_file")
            resolved_local_path = adapter.resolve_dataset(
                connected.get("Input/clearml_dataset_id"),
                connected.get("Input/local_path"),
                dataset_file=dataset_file,
            )
        cfg = apply_ui_params(cfg, connected, resolved_local_path=resolved_local_path)
        artifact_path = cfg.get("model", {}).get("artifact_path")
        if artifact_path:
            cfg["model"]["artifact_path"] = adapter.resolve_artifact_path(artifact_path)
        result = run_task(cfg)
        report_result(adapter, result)
    finally:
        adapter.close()


if __name__ == "__main__":
    main()
