from __future__ import annotations

from copy import deepcopy
from typing import Any

from ml_platform_core.value_coercion import as_bool, as_candidates, as_dict, as_str_list

from param_keys import (
    DATA_INPUT_KEYS,
    DATA_PARAM_TO_CONFIG,
    FEATURE_PARAM_TO_CONFIG,
    MODEL_SOURCE_PARAM_TO_CONFIG,
    SPLIT_PARAM_TO_CONFIG,
)
from param_transport import coerce_connected_params


def apply_connected_params_to_config(
    cfg: dict[str, Any],
    connected_params: dict[str, Any],
    *,
    resolved_local_path: str | None = None,
) -> dict[str, Any]:
    """Apply ClearML runtime parameter values to nested config."""
    cfg = deepcopy(cfg)
    connected = coerce_connected_params(connected_params)
    _ensure_config_sections(cfg, connected)
    _apply_run_params(cfg, connected)
    _apply_split_params(cfg, connected)
    _apply_data_params(cfg, connected, resolved_local_path)
    _apply_model_params(cfg, connected)
    _apply_metric_params(cfg, connected)
    _apply_feature_params(cfg, connected)
    _apply_output_params(cfg, connected)
    _apply_stage_inputs(cfg, connected)
    return cfg


def _has_connected_value(value: Any) -> bool:
    return value is not None and value != ""


def _ensure_config_sections(cfg: dict[str, Any], connected: dict[str, Any]) -> None:
    cfg.setdefault("run", {})
    required_sections = (
        ("data", "data" in cfg or _has_any_connected_key(connected, DATA_INPUT_KEYS)),
        ("model", _has_connected_prefix(connected, "Model/")),
        ("metrics", "Model/evaluation_metrics" in connected),
        ("features", _has_connected_prefix(connected, "Features/")),
        ("output", _has_connected_prefix(connected, "Output/")),
    )
    for name, required in required_sections:
        if required:
            cfg.setdefault(name, {})


def _has_any_connected_key(connected: dict[str, Any], keys: set[str]) -> bool:
    return any(key in keys for key in connected)


def _has_connected_prefix(connected: dict[str, Any], prefix: str) -> bool:
    return any(key.startswith(prefix) for key in connected)


def _apply_run_params(cfg: dict[str, Any], connected: dict[str, Any]) -> None:
    if connected.get("Run/task"):
        cfg["task"] = connected["Run/task"]
    if connected.get("Run/name"):
        cfg["run"]["name"] = connected["Run/name"]
    if connected.get("Run/seed") is not None:
        cfg["run"]["seed"] = int(connected["Run/seed"])
    if connected.get("Run/stage"):
        cfg["run"]["stage"] = connected["Run/stage"]


def _apply_split_params(cfg: dict[str, Any], connected: dict[str, Any]) -> None:
    updates = _split_updates(connected)
    if not updates:
        return
    cfg.setdefault("split", {})
    cfg["split"].update(updates)


def _split_updates(connected: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if "Split/valid_size" in connected and _has_connected_value(connected.get("Split/valid_size")):
        updates["valid_size"] = float(connected["Split/valid_size"])
    _copy_present_connected_values(updates, connected, tuple(SPLIT_PARAM_TO_CONFIG.items()))
    return updates


def _apply_data_params(
    cfg: dict[str, Any],
    connected: dict[str, Any],
    resolved_local_path: str | None,
) -> None:
    if "data" not in cfg:
        return
    _apply_local_path_param(cfg, connected, resolved_local_path)
    _copy_connected_values(cfg["data"], connected, DATA_PARAM_TO_CONFIG)
    _apply_list_connected_value(cfg["data"], connected, "Input/feature_columns", "feature_columns")
    _apply_list_connected_value(cfg["data"], connected, "Input/id_columns", "id_columns", default=[])


def _apply_local_path_param(
    cfg: dict[str, Any],
    connected: dict[str, Any],
    resolved_local_path: str | None,
) -> None:
    if resolved_local_path is not None:
        cfg["data"]["local_path"] = resolved_local_path
    elif connected.get("Input/local_path"):
        cfg["data"]["local_path"] = connected["Input/local_path"]


def _copy_connected_values(
    target: dict[str, Any],
    connected: dict[str, Any],
    mapping: tuple[tuple[str, str], ...],
) -> None:
    for param_key, config_key in mapping:
        if param_key in connected:
            target[config_key] = connected[param_key]


def _apply_list_connected_value(
    target: dict[str, Any],
    connected: dict[str, Any],
    param_key: str,
    config_key: str,
    *,
    default: list[str] | None = None,
) -> None:
    if param_key in connected:
        target[config_key] = as_str_list(connected.get(param_key)) or default


def _apply_model_params(cfg: dict[str, Any], connected: dict[str, Any]) -> None:
    if not _has_connected_prefix(connected, "Model/"):
        return
    _apply_model_identity_params(cfg, connected)
    _apply_model_candidate_params(cfg, connected)
    _apply_ensemble_params(cfg, connected)
    _apply_model_source_params(cfg, connected)


def _apply_model_identity_params(cfg: dict[str, Any], connected: dict[str, Any]) -> None:
    if connected.get("Model/name"):
        cfg["model"]["name"] = connected["Model/name"]
    if "Model/model_params_by_name" in connected:
        cfg["model"]["params"] = as_dict(connected.get("Model/model_params_by_name"))
    elif "Model/params" in connected:
        cfg["model"]["params"] = as_dict(connected.get("Model/params"))


def _apply_model_candidate_params(cfg: dict[str, Any], connected: dict[str, Any]) -> None:
    if "Model/candidates" in connected:
        cfg["model"]["candidates"] = as_candidates(connected.get("Model/candidates"))
    if connected.get("Model/selection_metric"):
        cfg["model"]["selection_metric"] = connected["Model/selection_metric"]


def _apply_model_source_params(cfg: dict[str, Any], connected: dict[str, Any]) -> None:
    _copy_connected_values(cfg["model"], connected, MODEL_SOURCE_PARAM_TO_CONFIG)
    if connected.get("Model/artifact_path"):
        cfg["model"]["artifact_path"] = connected["Model/artifact_path"]


def _apply_ensemble_params(cfg: dict[str, Any], connected: dict[str, Any]) -> None:
    ensemble_updates = _ensemble_updates(connected)
    if ensemble_updates:
        cfg["model"].setdefault("ensemble", {})
        cfg["model"]["ensemble"].update(ensemble_updates)


def _ensemble_updates(connected: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if "Model/ensemble_enabled" in connected:
        updates["enabled"] = as_bool(connected.get("Model/ensemble_enabled"))
    if "Model/ensemble_methods" in connected:
        updates["methods"] = as_str_list(connected.get("Model/ensemble_methods")) or []
    _copy_present_connected_values(updates, connected, (("Model/ensemble_method", "method"),))
    _apply_int_connected_value(updates, connected, "Model/ensemble_top_k", "top_k")
    return updates


def _apply_metric_params(cfg: dict[str, Any], connected: dict[str, Any]) -> None:
    if "Model/evaluation_metrics" in connected:
        cfg["metrics"]["names"] = as_str_list(connected.get("Model/evaluation_metrics"))


def _apply_feature_params(cfg: dict[str, Any], connected: dict[str, Any]) -> None:
    if not _has_connected_prefix(connected, "Features/"):
        return
    _copy_present_connected_values(cfg["features"], connected, FEATURE_PARAM_TO_CONFIG)
    _apply_list_connected_value(cfg["features"], connected, "Features/drop_columns", "drop_columns", default=[])
    _apply_list_connected_value(
        cfg["features"], connected, "Features/passthrough_columns", "passthrough_columns", default=[]
    )


def _copy_present_connected_values(
    target: dict[str, Any],
    connected: dict[str, Any],
    mapping: tuple[tuple[str, str], ...],
) -> None:
    for param_key, config_key in mapping:
        if param_key in connected and _has_connected_value(connected.get(param_key)):
            target[config_key] = connected[param_key]


def _apply_output_params(cfg: dict[str, Any], connected: dict[str, Any]) -> None:
    if not _has_connected_prefix(connected, "Output/"):
        return
    if connected.get("Output/prediction_name"):
        cfg["output"]["prediction_name"] = connected["Output/prediction_name"]
    _apply_int_connected_value(cfg["output"], connected, "Output/chunk_size", "chunk_size")
    if "Output/upload_plots" in connected:
        cfg["output"]["upload_plots"] = as_bool(connected.get("Output/upload_plots"), default=True)


def _apply_int_connected_value(
    target: dict[str, Any],
    connected: dict[str, Any],
    param_key: str,
    config_key: str,
) -> None:
    if param_key in connected and _has_connected_value(connected.get(param_key)):
        target[config_key] = int(connected[param_key])


def _apply_stage_inputs(cfg: dict[str, Any], connected: dict[str, Any]) -> None:
    if "stage_inputs" not in cfg:
        return
    cfg.setdefault("stage_inputs", {})
    for key in list(cfg.get("stage_inputs", {})):
        param_key = f"Input/{key}"
        if param_key in connected:
            cfg["stage_inputs"][key] = connected[param_key]
