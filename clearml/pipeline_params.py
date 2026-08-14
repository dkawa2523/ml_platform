from __future__ import annotations

from pathlib import Path
from typing import Any

from ml_platform_core.config import load_yaml
from ml_platform_core.value_coercion import as_str_list
from ml_platform_tabular.manifest import get_tabular_manifest
from ml_platform_tabular.policy import pipeline_runtime_defaults
from param_bindings import runtime_keys_for_config_section
from param_transport import coerce_connected_params


PIPELINE_ARG_PREFIX = "Args/"


def pipeline_runtime_params(
    task_path: str | Path = "config/tasks/tabular_pipeline.yaml",
    profile_path: str | Path = "config/profiles/clearml-dev.yaml",
) -> dict[str, Any]:
    pipeline_cfg = load_yaml(task_path)
    _require_training_config(pipeline_cfg)
    return _training_pipeline_runtime_params(pipeline_cfg, load_yaml(profile_path))


def pipeline_params_from_task(defaults: dict[str, Any], task_params: dict[str, Any]) -> dict[str, Any]:
    """Translate PipelineController's Args/* namespace to runtime parameters."""
    values = {key: task_params.get(f"{PIPELINE_ARG_PREFIX}{key}", value) for key, value in defaults.items()}
    return coerce_connected_params(values)


def model_params_overridden(overrides: list[str] | dict[str, Any] | None) -> bool:
    if isinstance(overrides, dict):
        model = overrides.get("model")
        return isinstance(model, dict) and "params" in model
    paths = [item.split("=", 1)[0].strip() for item in overrides or []]
    return any(path == "model.params" or path.startswith("model.params.") for path in paths)


def runtime_param_sets(
    pipeline_cfg: dict[str, Any],
    profile: dict[str, Any],
    runtime_params: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    defaults = coerce_connected_params(_training_pipeline_runtime_params(pipeline_cfg, profile))
    supplied = coerce_connected_params(runtime_params or {})
    explicit = {key: value for key, value in supplied.items() if key not in defaults or value != defaults[key]}
    return {**defaults, **supplied}, explicit


def preprocess_parameter_overrides(params: dict[str, Any]) -> dict[str, Any]:
    return {
        **_section_overrides(params, "data", include_empty=True),
        **_section_overrides(params, "split", float_keys=("Split/valid_size",)),
        **_section_overrides(params, "features"),
    }


def _training_pipeline_runtime_params(
    pipeline_cfg: dict[str, Any], profile: dict[str, Any] | None = None
) -> dict[str, Any]:
    profile = profile or {}
    clearml_cfg = profile.get("clearml", {}) or {}
    defaults = pipeline_runtime_defaults(
        pipeline_cfg,
        remote_default_dataset_id=clearml_cfg.get("default_dataset_id"),
        remote_default_dataset_file=clearml_cfg.get("default_dataset_file"),
        use_clearml=bool(profile.get("runtime", {}).get("use_clearml")),
    )
    allowed = {parameter.name for parameter in get_tabular_manifest().task("tabular_pipeline").parameters}
    return {key: value for key, value in defaults.items() if key in allowed}


def _section_overrides(
    params: dict[str, Any],
    section: str,
    *,
    include_empty: bool = False,
    float_keys: tuple[str, ...] = (),
) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    list_keys = set(runtime_keys_for_config_section(section, value_type="list"))
    for key in runtime_keys_for_config_section(section):
        if key not in params:
            continue
        value = params[key]
        if key in list_keys:
            overrides[key] = as_str_list(value) or []
        elif include_empty or value not in {None, ""}:
            overrides[key] = float(value) if key in float_keys else value
    return overrides


def _require_training_config(config: dict[str, Any]) -> None:
    if "data" not in config:
        raise ValueError("ClearML pipeline planning requires the official stage-based training config.")
