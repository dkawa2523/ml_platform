from __future__ import annotations

import argparse
import sys
from pathlib import Path


_CLEARML_DIR = Path(__file__).resolve().parent
if str(_CLEARML_DIR) not in sys.path:
    sys.path.insert(0, str(_CLEARML_DIR))

from _entrypoint_bootstrap import add_clearml_entrypoint_paths

add_clearml_entrypoint_paths()

from ml_platform_core.config import load_run_config
from ml_platform_core.config_validation import validate_run_config
from ml_platform_core.value_coercion import as_bool, as_str_list
from ml_platform_tabular import run_task

from adapter import (
    ClearMLAdapter,
    clearml_projects,
    clearml_stage_project,
    clearml_tags,
    prefixed_task_name,
    stage_task_label,
    validate_clearml_runtime,
)
from param_apply import apply_connected_params_to_config
from param_defaults import build_default_connected_params
from reports import report_result


def _is_prefixed_name(name: str | None) -> bool:
    return bool(name and name.startswith(("template/", "internal/", "pipeline/", "stage/", "task/")))


def _ensemble_method(cfg: dict) -> str | None:
    ensemble_cfg = _ensemble_cfg(cfg)
    if ensemble_cfg is None:
        return None
    return _first_ensemble_method(ensemble_cfg) or _configured_ensemble_method(ensemble_cfg)


def _ensemble_cfg(cfg: dict) -> dict | None:
    ensemble_cfg = cfg.get("model", {}).get("ensemble", {}) or {}
    if not isinstance(ensemble_cfg, dict):
        return None
    return ensemble_cfg


def _first_ensemble_method(ensemble_cfg: dict) -> str | None:
    methods = as_str_list(ensemble_cfg.get("methods")) or []
    return str(methods[0]) if methods else None


def _configured_ensemble_method(ensemble_cfg: dict) -> str | None:
    method = ensemble_cfg.get("method")
    return str(method) if method else None


def _stage_name(cfg: dict) -> str:
    return str(cfg.get("run", {}).get("stage") or "stage")


def _stage_model_name(cfg: dict) -> str | None:
    return str(cfg.get("model", {}).get("name") or "") or None


def _stage_ensemble_method(cfg: dict, stage: str) -> str | None:
    return _ensemble_method(cfg) if stage == "build_ensemble" else None


def _stage_label_parts(
    stage: str,
    model_name: str | None,
    ensemble_method: str | None,
) -> tuple[str | None, str | None]:
    return model_name if stage == "train_model" else None, ensemble_method if stage == "build_ensemble" else None


def _stage_metadata(cfg: dict) -> tuple[str, str | None, str | None, str, list[str]]:
    stage = _stage_name(cfg)
    model_name = _stage_model_name(cfg)
    ensemble_method = _stage_ensemble_method(cfg, stage)
    label_model, label_ensemble = _stage_label_parts(stage, model_name, ensemble_method)
    label = stage_task_label(stage, label_model, label_ensemble)
    tags = clearml_tags(
        "stage",
        internal=True,
        stage=stage,
        model=label_model,
        ensemble=label_ensemble,
    )
    return stage, model_name, ensemble_method, label, tags


def _initial_clearml_target(cfg: dict) -> tuple[str, str, list[str], str]:
    return _clearml_target(cfg, keep_prefixed_run_name=False)


def _runtime_clearml_metadata(cfg: dict) -> tuple[str | None, str, list[str], str]:
    return _clearml_target(cfg, keep_prefixed_run_name=True)


def _clearml_target(cfg: dict, *, keep_prefixed_run_name: bool) -> tuple[str, str, list[str], str]:
    clearml_cfg = cfg.get("clearml", {})
    projects = clearml_projects(clearml_cfg)
    task = cfg.get("task")
    run = cfg.get("run", {}) or {}
    run_name = str(run.get("name") or task or "run")
    handlers = {
        "tabular_infer": _infer_clearml_target,
        "tabular_stage": _stage_clearml_target,
    }
    handler = handlers.get(task, _experiment_clearml_target)
    return handler(cfg, projects, run_name, keep_prefixed_run_name)


def _infer_clearml_target(
    cfg: dict,
    projects: dict[str, str],
    run_name: str,
    keep_prefixed_run_name: bool,
) -> tuple[str, str, list[str], str]:
    return (
        projects["infer"],
        _clearml_task_name(run_name, "task", "tabular_infer", keep_prefixed_run_name),
        clearml_tags("task", user_facing=True),
        "User-facing tabular inference task.",
    )


def _stage_clearml_target(
    cfg: dict,
    projects: dict[str, str],
    run_name: str,
    keep_prefixed_run_name: bool,
) -> tuple[str, str, list[str], str]:
    stage, _, _, label, tags = _stage_metadata(cfg)
    return (
        clearml_stage_project(projects, stage),
        _clearml_task_name(run_name, "stage", label, keep_prefixed_run_name),
        tags,
        "Internal stage task for the tabular training pipeline graph.",
    )


def _experiment_clearml_target(
    cfg: dict,
    projects: dict[str, str],
    run_name: str,
    keep_prefixed_run_name: bool,
) -> tuple[str, str, list[str], str]:
    return (
        projects["experiments"],
        run_name,
        clearml_tags("task"),
        "Compatibility or experiment task.",
    )


def _clearml_task_name(run_name: str, prefix: str, label: str, keep_prefixed_run_name: bool) -> str:
    if keep_prefixed_run_name and _is_prefixed_name(run_name):
        return run_name
    return prefixed_task_name(prefix, label, run_name)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ClearML task application entrypoint.")
    parser.add_argument("--task", required=True, help="Path to task config YAML.")
    parser.add_argument("--profile", required=True, help="Path to profile config YAML.")
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        help="Optional KEY=VALUE override before connecting runtime params.",
    )
    return parser.parse_args()


def _init_adapter(cfg: dict) -> ClearMLAdapter:
    clearml_cfg = cfg.get("clearml", {})
    project_name, task_name, tags, comment = _initial_clearml_target(cfg)
    validate_clearml_runtime()
    return ClearMLAdapter.init(
        project_name=project_name,
        task_name=task_name,
        output_uri=clearml_cfg.get("artifact_output_uri"),
        tags=tags,
        comment=comment,
    )


def _connect_runtime_params(adapter: ClearMLAdapter, cfg: dict) -> dict:
    connected = adapter.connect_params(build_default_connected_params(cfg))
    metadata_cfg = apply_connected_params_to_config(cfg, connected)
    runtime_project, runtime_name, runtime_tags, runtime_comment = _runtime_clearml_metadata(metadata_cfg)
    adapter.apply_metadata(
        project_name=runtime_project,
        task_name=runtime_name,
        tags=runtime_tags,
        comment=runtime_comment,
        replace_tags=True,
    )
    return connected


def _resolved_dataset_path(adapter: ClearMLAdapter, cfg: dict, connected: dict) -> str | None:
    if not _needs_dataset_resolution(cfg, connected):
        return None
    return adapter.resolve_dataset(
        connected.get("Input/clearml_dataset_id"),
        connected.get("Input/local_path"),
    )


def _needs_dataset_resolution(cfg: dict, connected: dict) -> bool:
    if "data" not in cfg:
        return False
    stage = connected.get("Run/stage") or cfg.get("run", {}).get("stage")
    return not (cfg.get("task") == "tabular_stage" and stage != "preprocess_features")


def _runtime_task_config(adapter: ClearMLAdapter, cfg: dict, connected: dict) -> dict:
    resolved_local_path = _resolved_dataset_path(adapter, cfg, connected)
    cfg = apply_connected_params_to_config(cfg, connected, resolved_local_path=resolved_local_path)
    task_id = adapter.task.id
    if task_id:
        cfg.setdefault("runtime", {})["clearml_task_id"] = task_id
    cfg = _resolve_runtime_sources(adapter, cfg)
    validate_run_config(cfg)
    return cfg


def _resolve_runtime_sources(adapter: ClearMLAdapter, cfg: dict) -> dict:
    if cfg.get("task") == "tabular_infer":
        cfg = adapter.resolve_infer_model_source(cfg)
    else:
        artifact_path = cfg.get("model", {}).get("artifact_path")
        if artifact_path:
            cfg["model"]["artifact_path"] = adapter.resolve_artifact_path(artifact_path)
    return adapter.resolve_stage_inputs(cfg)


def main() -> None:
    args = _parse_args()
    cfg = load_run_config(args.task, args.profile, overrides=args.overrides)
    adapter = _init_adapter(cfg)
    try:
        connected = _connect_runtime_params(adapter, cfg)
        cfg = _runtime_task_config(adapter, cfg, connected)
        result = run_task(cfg)
        upload_plots = as_bool(cfg.get("output", {}).get("upload_plots"), default=True)
        report_result(adapter, result, upload_plots=upload_plots)
    finally:
        adapter.close()


if __name__ == "__main__":
    main()
