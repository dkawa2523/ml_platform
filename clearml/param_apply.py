from __future__ import annotations

from copy import deepcopy
from typing import Any

from ml_platform_core.value_coercion import as_bool, as_candidates, as_dict, as_str_list

from param_bindings import binding_map_for_config
from param_transport import coerce_connected_params


_EMPTY_OK_KEYS = {
    "Input/clearml_dataset_id",
    "Input/dataset_file",
    "Input/target_column",
    "Model/source_type",
    "Model/source_task_id",
    "Model/model_selector",
    "Model/local_model_path",
    "Model/feature_spec_path",
    "Model/preprocess_bundle_path",
    "Model/info_path",
}
_LIST_DEFAULTS = {
    "Input/id_columns": [],
    "Features/drop_columns": [],
    "Features/passthrough_columns": [],
    "Model/ensemble_methods": [],
}
_MODEL_PARAM_KEYS = ("Model/model_params_by_name", "Model/params")


def apply_connected_params_to_config(
    cfg: dict[str, Any],
    connected_params: dict[str, Any],
    *,
    resolved_local_path: str | None = None,
) -> dict[str, Any]:
    """Apply ClearML runtime parameter values to nested config."""
    cfg = deepcopy(cfg)
    connected = coerce_connected_params(connected_params)
    bindings = binding_map_for_config(cfg)
    _apply_local_path(cfg, connected, bindings, resolved_local_path)
    _apply_model_params(cfg, connected, bindings)
    for key, value in connected.items():
        if key in {"Input/local_path", *_MODEL_PARAM_KEYS}:
            continue
        binding = bindings.get(key)
        if binding and _should_apply(cfg, binding, value):
            _set_path(cfg, binding.config_path, _value_for_apply(key, value, binding))
    return cfg


def _apply_local_path(cfg, connected, bindings, resolved_local_path: str | None) -> None:
    binding = bindings.get("Input/local_path")
    if binding is None:
        return
    if resolved_local_path is not None:
        _set_path(cfg, binding.config_path, resolved_local_path)
    elif connected.get("Input/local_path"):
        _set_path(cfg, binding.config_path, connected["Input/local_path"])


def _apply_model_params(cfg, connected, bindings) -> None:
    for key in _MODEL_PARAM_KEYS:
        if key in connected and key in bindings:
            _set_path(cfg, bindings[key].config_path, as_dict(connected.get(key)))
            return


def _should_apply(cfg, binding, value) -> bool:
    if not binding.config_path:
        return False
    if binding.config_path[0] == "stage_inputs":
        return "stage_inputs" in cfg
    if binding.value_type in {"bool", "dict", "candidates", "list"}:
        return True
    if binding.value_type in {"int", "float"}:
        return _has_value(value)
    return _has_value(value) or binding.key in _EMPTY_OK_KEYS


def _has_value(value: Any) -> bool:
    return value is not None and value != ""


def _value_for_apply(key, value, binding):
    if binding.value_type == "bool":
        return as_bool(value, default=(key == "Output/upload_plots"))
    if binding.value_type == "int":
        return int(value)
    if binding.value_type == "float":
        return float(value)
    if binding.value_type == "list":
        parsed = as_str_list(value)
        return parsed if parsed is not None else _LIST_DEFAULTS.get(key)
    if binding.value_type == "dict":
        return as_dict(value)
    if binding.value_type == "candidates":
        return as_candidates(value)
    return value


def _set_path(cfg, path, value) -> None:
    target = cfg
    for part in path[:-1]:
        target = target.setdefault(part, {})
    target[path[-1]] = value
