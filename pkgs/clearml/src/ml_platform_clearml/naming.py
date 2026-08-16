"""ClearML project, task, and tag naming."""

from __future__ import annotations

from typing import Any

from ml_platform_core.stages import StageName, as_stage_name


def clearml_projects(clearml_cfg: dict[str, Any] | None) -> dict[str, str]:
    """Return the configured ClearML project layout."""
    clearml_cfg = clearml_cfg or {}
    root = str(clearml_cfg.get("project_root") or "MLPlatform/Dev").rstrip("/")
    configured = clearml_cfg.get("projects") or {}
    if not isinstance(configured, dict):
        configured = {}
    return _project_layout(root, configured)


def _project_layout(root: str, configured: dict[str, Any]) -> dict[str, str]:
    stages = _setting(configured, "stages", f"{root}/Runs/Tabular/Stages")
    tasks = _setting(configured, "tasks", f"{root}/Runs/Tabular/Tasks")
    defaults = {
        "templates": f"{root}/Templates/Tabular",
        "pipelines": f"{root}/Pipelines/Tabular",
        "preprocess": _setting(configured, "stages", f"{root}/Runs/Tabular/Preprocess"),
        "train": _setting(configured, "stages", f"{root}/Runs/Tabular/Train"),
        "ensemble": _setting(configured, "stages", f"{root}/Runs/Tabular/Ensemble"),
        "evaluate": _setting(configured, "stages", f"{root}/Runs/Tabular/Evaluate"),
        "infer": _setting(configured, "tasks", f"{root}/Runs/Tabular/Infer"),
        "stages": stages,
        "tasks": tasks,
        "experiments": f"{root}/Experiments/Tabular",
    }
    return {key: _setting(configured, key, value) for key, value in defaults.items()}


def _setting(configured: dict[str, Any], key: str, default: str) -> str:
    return str(configured.get(key) or default)


def clearml_stage_project(projects: dict[str, str], stage: StageName | str) -> str:
    project_key = {
        "preprocess_features": "preprocess",
        "train_model": "train",
        "build_ensemble": "ensemble",
        "evaluate_models": "evaluate",
    }[as_stage_name(str(stage))]
    return projects[project_key]


def clearml_template_name(template_name: str) -> str:
    return {
        "tabular_train_pipeline_template": "template/tabular_train_pipeline",
        "tabular_infer_template": "template/tabular_infer",
        "tabular_stage_template": "internal/tabular_stage",
    }.get(template_name, template_name)


def clearml_tags(
    run_type: str,
    *,
    user_facing: bool = False,
    internal: bool = False,
    stage: str | None = None,
    model: str | None = None,
    ensemble: str | None = None,
) -> list[str]:
    tags = ["domain:tabular", f"run_type:{run_type}"]
    tags.extend(
        tag
        for enabled, tag in (
            (user_facing, "user_facing:true"),
            (internal, "internal:true"),
            (bool(stage), f"stage:{stage}"),
            (bool(model), f"model:{model}"),
            (bool(ensemble), f"ensemble:{ensemble}"),
        )
        if enabled
    )
    return tags


def prefixed_task_name(prefix: str, name: str, run_name: str | None = None) -> str:
    if name.startswith(("template/", "internal/", "pipeline/", "stage/", "task/")):
        return name
    suffix = f"/{run_name}" if run_name else ""
    return f"{prefix}/{name}{suffix}"


def stage_task_label(
    stage: StageName | str,
    model_name: str | None = None,
    ensemble_method: str | None = None,
) -> str:
    stage_name = as_stage_name(str(stage))
    if stage_name == "train_model" and model_name:
        return f"train_{model_name}"
    if stage_name == "build_ensemble" and ensemble_method:
        return f"build_ensemble_{ensemble_method}"
    return stage_name
