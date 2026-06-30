from __future__ import annotations

import json
from typing import Any

from ml_platform_core.value_coercion import as_bool

from param_keys import FEATURE_DEFAULT_KEYS, MODEL_SOURCE_DEFAULT_KEYS
from param_transport import normalize_clearml_param_value


def _section(cfg: dict[str, Any], name: str) -> dict[str, Any] | None:
    if name not in cfg:
        return None
    value = cfg.get(name) or {}
    return value if isinstance(value, dict) else {}


def build_default_connected_params(cfg: dict[str, Any]) -> dict[str, Any]:
    """Return the small ClearML runtime parameter surface for a task config."""
    params: dict[str, Any] = {}
    _add_run_defaults(params, cfg)
    _add_split_defaults(params, cfg)
    _add_data_defaults(params, cfg)
    _add_model_defaults(params, cfg)
    _add_metric_defaults(params, cfg)
    _add_feature_defaults(params, cfg)
    _add_output_defaults(params, cfg)
    _add_stage_input_defaults(params, cfg)
    return params


def _add_run_defaults(params: dict[str, Any], cfg: dict[str, Any]) -> None:
    run = cfg.get("run", {})
    params["Run/task"] = cfg.get("task")
    params["Run/name"] = run.get("name")
    params["Run/seed"] = run.get("seed")
    if "stage" in run:
        params["Run/stage"] = run.get("stage")


def _add_split_defaults(params: dict[str, Any], cfg: dict[str, Any]) -> None:
    split = _section(cfg, "split")
    if split is None:
        return
    _add_prefixed_defaults(
        params,
        split,
        "Split",
        ("method", "valid_size", "group_column", "time_column", "valid_filter_column", "valid_filter_value"),
    )


def _add_data_defaults(params: dict[str, Any], cfg: dict[str, Any]) -> None:
    data = _section(cfg, "data")
    if data is None:
        return
    params.update(
        {
            "Input/local_path": data.get("local_path"),
            "Input/clearml_dataset_id": data.get("clearml_dataset_id"),
            "Input/dataset_file": data.get("dataset_file"),
            "Input/target_column": data.get("target_column"),
            "Input/feature_columns": data.get("feature_columns"),
            "Input/id_columns": data.get("id_columns", []),
        }
    )


def _add_model_defaults(params: dict[str, Any], cfg: dict[str, Any]) -> None:
    if "model" not in cfg:
        return
    model = cfg.get("model", {})
    _add_model_identity_defaults(params, model)
    _add_ensemble_defaults(params, model)
    _add_model_source_defaults(params, model)


def _add_model_identity_defaults(params: dict[str, Any], model: dict[str, Any]) -> None:
    _add_prefixed_defaults(params, model, "Model", ("name", "selection_metric"))
    _add_json_default(params, model, "params", default={})
    _add_json_default(params, model, "candidates", default=[])


def _add_model_source_defaults(params: dict[str, Any], model: dict[str, Any]) -> None:
    for key in MODEL_SOURCE_DEFAULT_KEYS:
        if key in model:
            params[f"Model/{key}"] = model.get(key)
    if "artifact_path" in model:
        params["Model/artifact_path"] = model.get("artifact_path")
    if "info_path" in model:
        params["Model/info_path"] = model.get("info_path")


def _add_ensemble_defaults(params: dict[str, Any], model: dict[str, Any]) -> None:
    ensemble = _section(model, "ensemble")
    if ensemble is None:
        return
    params["Model/ensemble_enabled"] = as_bool(ensemble.get("enabled"))
    if "methods" in ensemble:
        params["Model/ensemble_methods"] = normalize_clearml_param_value(ensemble.get("methods") or [])
    params["Model/ensemble_method"] = ensemble.get("method", "mean_topk")
    params["Model/ensemble_top_k"] = int(ensemble.get("top_k") or 3)


def _add_metric_defaults(params: dict[str, Any], cfg: dict[str, Any]) -> None:
    if "metrics" not in cfg:
        return
    metric_names = cfg.get("metrics", {}).get("names")
    if metric_names is not None:
        params["Model/evaluation_metrics"] = normalize_clearml_param_value(metric_names)


def _add_feature_defaults(params: dict[str, Any], cfg: dict[str, Any]) -> None:
    features = _section(cfg, "features")
    if features is None:
        return
    for key in FEATURE_DEFAULT_KEYS:
        if key in features:
            params[f"Features/{key}"] = normalize_clearml_param_value(features.get(key))


def _add_output_defaults(params: dict[str, Any], cfg: dict[str, Any]) -> None:
    output = _section(cfg, "output")
    if output is None:
        return
    if "prediction_name" in output:
        params["Output/prediction_name"] = output.get("prediction_name")
    if "chunk_size" in output:
        params["Output/chunk_size"] = output.get("chunk_size")
    if "upload_plots" in output:
        params["Output/upload_plots"] = as_bool(output.get("upload_plots"), default=True)


def _add_stage_input_defaults(params: dict[str, Any], cfg: dict[str, Any]) -> None:
    if "stage_inputs" not in cfg:
        return
    for key, value in (cfg.get("stage_inputs") or {}).items():
        params[f"Input/{key}"] = normalize_clearml_param_value(value)


def _add_prefixed_defaults(
    params: dict[str, Any],
    source: dict[str, Any],
    prefix: str,
    keys: tuple[str, ...],
) -> None:
    for key in keys:
        if key in source:
            params[f"{prefix}/{key}"] = source.get(key)


def _add_json_default(
    params: dict[str, Any],
    source: dict[str, Any],
    key: str,
    *,
    default: list[Any] | dict[str, Any],
) -> None:
    if key in source:
        params[f"Model/{key}"] = json.dumps(source.get(key, default) or default)
