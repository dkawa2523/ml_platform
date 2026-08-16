from __future__ import annotations

from typing import Any

from ml_platform_core.value_coercion import as_bool
from ml_platform_tabular.manifest import get_tabular_manifest

from .param_bindings import binding_map_for_config
from .param_transport import normalize_clearml_param_value

_RUN_DEFAULT_KEYS = ("Run/task", "Run/name", "Run/seed")
_MODEL_SOURCE_KEYS = (
    "Model/source_type",
    "Model/source_task_id",
    "Model/model_selector",
    "Model/local_model_path",
)
_MISSING = object()


def build_default_connected_params(cfg: dict[str, Any]) -> dict[str, Any]:
    """Return the small ClearML runtime parameter surface for a task config."""
    bindings = binding_map_for_config(cfg)
    params: dict[str, Any] = {}
    _add_defaults(params, cfg, bindings, _RUN_DEFAULT_KEYS, include_missing=True)
    if "stage" in (cfg.get("run") or {}):
        _add_defaults(params, cfg, bindings, ("Run/stage",))
    _add_section_defaults(params, cfg, bindings, "split")
    _add_section_defaults(params, cfg, bindings, "data", include_missing=True, defaults={"Input/id_columns": []})
    _add_model_defaults(params, cfg, bindings)
    _add_metric_defaults(params, cfg, bindings)
    _add_section_defaults(params, cfg, bindings, "features", normalize=True)
    _add_output_defaults(params, cfg, bindings)
    _add_stage_input_defaults(params, cfg)
    allowed = {parameter.name for parameter in get_tabular_manifest().task(str(cfg["task"])).parameters}
    return {key: value for key, value in params.items() if key in allowed}


def _add_model_defaults(params, cfg, bindings) -> None:
    if "model" not in cfg:
        return
    _add_defaults(params, cfg, bindings, ("Model/name", "Model/selection_metric"))
    _add_json_model_default(params, cfg, "params", default={})
    _add_json_model_default(params, cfg, "candidates", default=[])
    _add_defaults(params, cfg, bindings, _MODEL_SOURCE_KEYS)
    _add_defaults(params, cfg, bindings, ("Model/artifact_path", "Model/info_path"))
    _add_ensemble_defaults(params, cfg)


def _add_json_model_default(params, cfg, leaf, *, default) -> None:
    path = ("model", leaf)
    if _path_exists(cfg, path):
        params[f"Model/{leaf}"] = normalize_clearml_param_value(_path_get(cfg, path, default) or default)


def _add_ensemble_defaults(params: dict[str, Any], cfg: dict[str, Any]) -> None:
    ensemble = (cfg.get("model") or {}).get("ensemble")
    if not isinstance(ensemble, dict):
        return
    params["Model/ensemble_enabled"] = as_bool(ensemble.get("enabled"))
    if "methods" in ensemble:
        params["Model/ensemble_methods"] = normalize_clearml_param_value(ensemble.get("methods") or [])
    params["Model/ensemble_method"] = ensemble.get("method", "mean_topk")
    params["Model/ensemble_top_k"] = int(ensemble.get("top_k") or 3)


def _add_metric_defaults(params, cfg, bindings) -> None:
    binding = bindings.get("Model/evaluation_metrics")
    if binding is None:
        return
    metric_names = _path_get(cfg, binding.config_path)
    if metric_names is not None:
        params[binding.key] = normalize_clearml_param_value(metric_names)


def _add_output_defaults(params, cfg, bindings) -> None:
    _add_section_defaults(params, cfg, bindings, "output", keys=("Output/prediction_name",))
    if _path_exists(cfg, ("output", "upload_plots")):
        params["Output/upload_plots"] = as_bool(_path_get(cfg, ("output", "upload_plots")), default=True)


def _add_stage_input_defaults(params: dict[str, Any], cfg: dict[str, Any]) -> None:
    if "stage_inputs" not in cfg:
        return
    for key, value in (cfg.get("stage_inputs") or {}).items():
        params[f"Input/{key}"] = normalize_clearml_param_value(value)


def _add_section_defaults(
    params, cfg, bindings, section, *, include_missing=False, defaults=None, keys=None, normalize=False
) -> None:
    if section not in cfg:
        return
    selected = _selected_bindings(bindings, section, keys)
    _add_defaults(
        params, cfg, bindings, selected, include_missing=include_missing, defaults=defaults, normalize=normalize
    )


def _selected_bindings(bindings, section, keys) -> tuple[str, ...]:
    if keys is not None:
        return keys
    return tuple(
        binding.key
        for binding in bindings.values()
        if binding.config_path[:1] == (section,) and len(binding.config_path) > 1
    )


def _add_defaults(params, cfg, bindings, keys, *, include_missing=False, defaults=None, normalize=False) -> None:
    defaults = defaults or {}
    for key in keys:
        binding = bindings.get(key)
        if binding is None or not binding.config_path:
            continue
        if include_missing or _path_exists(cfg, binding.config_path):
            value = _path_get(cfg, binding.config_path, defaults.get(key))
            params[key] = normalize_clearml_param_value(value) if normalize else value


def _path_exists(cfg: dict[str, Any], path: tuple[str, ...]) -> bool:
    return _path_get(cfg, path, _MISSING) is not _MISSING


def _path_get(cfg: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    target: Any = cfg
    for part in path:
        if not isinstance(target, dict) or part not in target:
            return default
        target = target[part]
    return target
