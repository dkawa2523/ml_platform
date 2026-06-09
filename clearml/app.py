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

from adapter import (
    ClearMLAdapter,
    apply_ui_params,
    as_list,
    as_bool,
    clearml_projects,
    clearml_stage_project,
    clearml_tags,
    default_ui_params,
    prefixed_task_name,
    stage_task_label,
)
from reports import report_result


def _is_prefixed_name(name: str | None) -> bool:
    return bool(name and name.startswith(("template/", "internal/", "pipeline/", "stage/", "task/")))


def _ensemble_method(cfg: dict) -> str | None:
    ensemble_cfg = cfg.get("model", {}).get("ensemble", {}) or {}
    if not isinstance(ensemble_cfg, dict):
        return None
    methods = as_list(ensemble_cfg.get("methods")) or []
    if methods:
        return str(methods[0])
    method = ensemble_cfg.get("method")
    return str(method) if method else None


def _stage_metadata(cfg: dict) -> tuple[str, str | None, str | None, str, list[str]]:
    stage = str(cfg.get("run", {}).get("stage") or "stage")
    model_name = str(cfg.get("model", {}).get("name") or "") or None
    ensemble_method = _ensemble_method(cfg) if stage == "build_ensemble" else None
    label = stage_task_label(
        stage,
        model_name if stage == "train_model" else None,
        ensemble_method if stage == "build_ensemble" else None,
    )
    tags = clearml_tags(
        "stage",
        internal=True,
        stage=stage,
        model=model_name if stage == "train_model" else None,
        ensemble=ensemble_method if stage == "build_ensemble" else None,
    )
    return stage, model_name, ensemble_method, label, tags


def _initial_clearml_target(cfg: dict) -> tuple[str, str, list[str], str]:
    clearml_cfg = cfg.get("clearml", {})
    projects = clearml_projects(clearml_cfg)
    task = cfg.get("task")
    run = cfg.get("run", {}) or {}
    run_name = str(run.get("name") or task or "run")
    if task == "tabular_infer":
        return (
            projects["infer"],
            prefixed_task_name("task", "tabular_infer", run_name),
            clearml_tags("task", user_facing=True),
            "User-facing tabular inference task.",
        )
    if task == "tabular_stage":
        stage, _, _, label, tags = _stage_metadata(cfg)
        return (
            clearml_stage_project(projects, stage),
            prefixed_task_name("stage", label, run_name),
            tags,
            "Internal stage task for the tabular training pipeline graph.",
        )
    return (
        projects["experiments"],
        run_name,
        clearml_tags("task"),
        "Compatibility or experiment task.",
    )


def _runtime_clearml_metadata(cfg: dict) -> tuple[str | None, str, list[str], str]:
    clearml_cfg = cfg.get("clearml", {})
    projects = clearml_projects(clearml_cfg)
    task = cfg.get("task")
    run = cfg.get("run", {}) or {}
    run_name = str(run.get("name") or task or "run")
    if task == "tabular_infer":
        name = run_name if _is_prefixed_name(run_name) else prefixed_task_name("task", "tabular_infer", run_name)
        return projects["infer"], name, clearml_tags("task", user_facing=True), "User-facing tabular inference task."
    if task == "tabular_stage":
        stage, _, _, label, tags = _stage_metadata(cfg)
        name = run_name if _is_prefixed_name(run_name) else prefixed_task_name("stage", label, run_name)
        return (
            clearml_stage_project(projects, stage),
            name,
            tags,
            "Internal stage task for the tabular training pipeline graph.",
        )
    return projects["experiments"], run_name, clearml_tags("task"), "Compatibility or experiment task."


def main() -> None:
    parser = argparse.ArgumentParser(description="ClearML task application entrypoint.")
    parser.add_argument("--task", required=True, help="Path to task config YAML.")
    parser.add_argument("--profile", required=True, help="Path to profile config YAML.")
    parser.add_argument("--set", dest="overrides", action="append", default=[], help="Optional KEY=VALUE override before connecting UI params.")
    args = parser.parse_args()

    cfg = apply_overrides(load_run_config(args.task, args.profile), args.overrides)
    clearml_cfg = cfg.get("clearml", {})
    project_name, task_name, tags, comment = _initial_clearml_target(cfg)

    adapter = ClearMLAdapter.init(
        project_name=project_name,
        task_name=task_name,
        output_uri=clearml_cfg.get("artifact_output_uri"),
        tags=tags,
        comment=comment,
    )
    try:
        connected = adapter.connect_params(default_ui_params(cfg))
        resolved_local_path = None
        stage = connected.get("Run/stage") or cfg.get("run", {}).get("stage")
        needs_dataset = "data" in cfg and not (cfg.get("task") == "tabular_stage" and stage != "preprocess_features")
        if needs_dataset:
            dataset_file = connected.get("Input/dataset_file") or cfg.get("data", {}).get("dataset_file")
            resolved_local_path = adapter.resolve_dataset(
                connected.get("Input/clearml_dataset_id"),
                connected.get("Input/local_path"),
                dataset_file=dataset_file,
            )
        cfg = apply_ui_params(cfg, connected, resolved_local_path=resolved_local_path)
        runtime_project, runtime_name, runtime_tags, runtime_comment = _runtime_clearml_metadata(cfg)
        adapter.apply_metadata(
            project_name=runtime_project,
            task_name=runtime_name,
            tags=runtime_tags,
            comment=runtime_comment,
        )
        if cfg.get("task") == "tabular_infer":
            cfg = adapter.resolve_infer_model_source(cfg)
        else:
            artifact_path = cfg.get("model", {}).get("artifact_path")
            if artifact_path:
                cfg["model"]["artifact_path"] = adapter.resolve_artifact_path(artifact_path)
        cfg = adapter.resolve_stage_inputs(cfg)
        result = run_task(cfg)
        report_plots = as_bool(cfg.get("output", {}).get("report_plots"), default=True)
        report_result(adapter, result, report_plots=report_plots)
    finally:
        adapter.close()


if __name__ == "__main__":
    main()
