"""Translate nested run configuration into ClearML-compatible flat defaults."""

from __future__ import annotations

import json
from typing import Any

from ml_platform_core.value_coercion import as_bool

from .model_catalog import SUPPORTED_MODELS


def basic_config(pipeline_cfg: dict[str, Any]) -> dict[str, Any]:
    raw = pipeline_cfg.get("basic") or pipeline_cfg.get("Basic") or {}
    return raw if isinstance(raw, dict) else {}


def pipeline_runtime_defaults(
    pipeline_cfg: dict[str, Any],
    *,
    remote_default_dataset_id: object | None = None,
    remote_default_dataset_file: object | None = None,
    use_clearml: bool = False,
) -> dict[str, Any]:
    run = pipeline_cfg.get("run", {})
    data = pipeline_cfg.get("data", {})
    split = pipeline_cfg.get("split", {}) or {}
    features = pipeline_cfg.get("features", {}) or {}
    model = pipeline_cfg.get("model", {})
    metrics = pipeline_cfg.get("metrics", {}) or {}
    output = pipeline_cfg.get("output", {}) or {}
    ensemble = model.get("ensemble", {}) or {}
    if not isinstance(ensemble, dict):
        ensemble = {}
    return {
        **_basic_defaults(basic_config(pipeline_cfg), run, ensemble),
        **_split_defaults(split),
        **_data_defaults(
            data,
            remote_default_dataset_id=remote_default_dataset_id,
            remote_default_dataset_file=remote_default_dataset_file,
            use_clearml=use_clearml,
        ),
        **_feature_defaults(features),
        **_model_defaults(model, metrics, ensemble),
        "Output/upload_plots": as_bool(output.get("upload_plots"), default=True),
    }


def _basic_defaults(basic: dict[str, Any], run: dict[str, Any], ensemble: dict[str, Any]) -> dict[str, Any]:
    return {
        "Basic/model_suite": basic.get("model_suite", "default"),
        "Basic/quality_mode": basic.get("quality_mode", "standard"),
        "Basic/use_ensemble": basic.get("use_ensemble", as_bool(ensemble.get("enabled"), default=True)),
        "Basic/notes": basic.get("notes") or run.get("description", ""),
        "Run/name": run.get("name"),
        "Run/seed": run.get("seed"),
    }


def _split_defaults(split: dict[str, Any]) -> dict[str, Any]:
    return {
        "Split/method": split.get("method", "random"),
        "Split/valid_size": split.get("valid_size", 0.2),
        "Split/selection_size": split.get("selection_size", 0.2),
        "Split/group_column": split.get("group_column"),
        "Split/time_column": split.get("time_column"),
        "Split/valid_filter_column": split.get("valid_filter_column"),
        "Split/valid_filter_value": split.get("valid_filter_value"),
    }


def _data_defaults(
    data: dict[str, Any],
    *,
    remote_default_dataset_id: object | None,
    remote_default_dataset_file: object | None,
    use_clearml: bool,
) -> dict[str, Any]:
    dataset_id = data.get("clearml_dataset_id")
    dataset_file = data.get("dataset_file")
    local_path = data.get("local_path")
    if use_clearml and remote_default_dataset_id and not dataset_id:
        dataset_id = remote_default_dataset_id
        dataset_file = dataset_file or remote_default_dataset_file
        local_path = ""
    return {
        "Input/local_path": local_path,
        "Input/clearml_dataset_id": dataset_id,
        "Input/dataset_file": dataset_file,
        "Input/source_manifest": data.get("source_manifest"),
        "Input/target_column": data.get("target_column"),
        "Input/feature_columns": data.get("feature_columns") or [],
        "Input/id_columns": data.get("id_columns", []),
    }


def _feature_defaults(features: dict[str, Any]) -> dict[str, Any]:
    return {
        "Features/preset": features.get("preset", "basic"),
        "Features/numeric_impute_strategy": features.get("numeric_impute_strategy", "median"),
        "Features/categorical_impute_strategy": features.get("categorical_impute_strategy", "missing_token"),
        "Features/categorical_encoder": features.get("categorical_encoder", "onehot"),
        "Features/scaling": features.get("scaling", "standard"),
        "Features/drop_columns": _json(features.get("drop_columns", []) or []),
        "Features/passthrough_columns": _json(features.get("passthrough_columns", []) or []),
        "Features/max_dense_cells": int(features.get("max_dense_cells", 25_000_000)),
    }


def _model_defaults(model: dict[str, Any], metrics: dict[str, Any], ensemble: dict[str, Any]) -> dict[str, Any]:
    return {
        "Model/candidates": _json(model.get("candidates") or SUPPORTED_MODELS),
        "Model/model_params_by_name": _json(model.get("params", {}) or {}),
        "Model/evaluation_metrics": _json(metrics.get("names", []) or []),
        "Model/selection_metric": model.get("selection_metric", "rmse"),
        "Model/ensemble_enabled": "",
        "Model/ensemble_methods": _json(ensemble.get("methods", [ensemble.get("method", "mean_topk")]) or []),
        "Model/ensemble_top_k": int(ensemble.get("top_k") or 3),
    }


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True)
