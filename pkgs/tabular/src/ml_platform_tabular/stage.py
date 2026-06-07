"""ClearML-free stage runner for tabular training pipelines.

This module executes one stage at a time. ClearML resolves artifact URLs before
calling this code; package code only receives local paths or plain JSON refs.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from ml_platform_core.artifacts import prepare_run_dir, update_latest, write_config_snapshot, write_manifest
from ml_platform_core.io import load_joblib, read_json, read_table
from ml_platform_core.result import RunResult

from .pipeline import (
    _build_ensemble,
    _evaluate_models,
    _metric_name,
    _metric_names,
    _preprocess_features,
    _ranked_results,
    _retrain_best,
    _run_search_trials,
    _safe_name,
    _train_model,
    _evaluate_best,
)


def _run_dir(cfg: dict[str, Any], stage: str) -> Path:
    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    run_name = cfg.get("run", {}).get("name") or stage
    return prepare_run_dir(output_dir, run_name)


def _finish_stage(
    cfg: dict[str, Any],
    run_dir: Path,
    *,
    metrics: dict[str, Any] | None,
    artifacts: dict[str, Path],
    tables: dict[str, Path] | None = None,
    extra: dict[str, Any] | None = None,
) -> RunResult:
    tables = tables or {}
    extra = extra or {}
    config_path = write_config_snapshot(cfg, run_dir)
    artifacts = {**artifacts, "config": config_path}
    manifest_path = write_manifest(
        run_dir,
        config=cfg,
        metrics=metrics or {},
        artifacts=artifacts,
        tables=tables,
        extra=extra,
    )
    artifacts["manifest"] = manifest_path
    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    update_latest(run_dir, output_dir / "latest_tabular_stage")
    update_latest(run_dir, output_dir / "latest")
    return RunResult(run_dir=run_dir, metrics=metrics or {}, artifacts=artifacts, tables=tables, extra=extra)


def _json_value(value: Any, *, default: Any) -> Any:
    if value is None or value == "":
        return default
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return default
        return json.loads(text)
    return value


def _stage_inputs(cfg: dict[str, Any]) -> dict[str, Any]:
    inputs = cfg.get("stage_inputs") or {}
    if not isinstance(inputs, dict):
        raise ValueError("stage_inputs must be a mapping.")
    return inputs


def _required_path(inputs: dict[str, Any], key: str) -> Path:
    value = inputs.get(key)
    if not value:
        raise ValueError(f"stage_inputs.{key} is required for this stage.")
    path = Path(str(value))
    if "${" in str(value):
        raise ValueError(f"stage_inputs.{key} still contains an unresolved ClearML placeholder: {value}")
    if not path.exists():
        raise FileNotFoundError(f"stage_inputs.{key} does not exist: {path}")
    return path


def _load_preprocess(cfg: dict[str, Any]) -> dict[str, Any]:
    inputs = _stage_inputs(cfg)
    bundle_path = _required_path(inputs, "preprocess_bundle")
    feature_spec_path = _required_path(inputs, "feature_spec")
    processed_train_path = _required_path(inputs, "processed_train")
    processed_valid_path = _required_path(inputs, "processed_valid")

    bundle = load_joblib(bundle_path)
    spec = read_json(feature_spec_path)
    train_df = read_table(processed_train_path)
    valid_df = read_table(processed_valid_path)
    target_column = spec.get("target_column") or bundle.get("target_column")
    if not target_column:
        raise ValueError("feature_spec.target_column is required.")
    feature_columns = spec.get("feature_columns") or bundle.get("feature_columns")
    if not feature_columns:
        feature_columns = [col for col in train_df.columns if col != target_column]

    return {
        "stage": "preprocess_features",
        "stage_dir": bundle_path.parent,
        "transformer": bundle["transformer"],
        "feature_columns": list(feature_columns),
        "target_column": target_column,
        "feature_preset": bundle.get("feature_preset") or spec.get("feature_preset", "basic"),
        "X_train": train_df[list(feature_columns)],
        "X_valid": valid_df[list(feature_columns)],
        "y_train": train_df[target_column],
        "y_valid": valid_df[target_column],
        "artifacts": {
            "preprocess_bundle": bundle_path,
            "feature_spec": feature_spec_path,
        },
        "tables": {
            "processed_train": processed_train_path,
            "processed_valid": processed_valid_path,
        },
    }


def _model_ref(item: dict[str, Any]) -> dict[str, Any]:
    model_value = str(item.get("model") or "")
    if "${" in model_value:
        raise ValueError(f"Model ref still contains an unresolved ClearML placeholder: {model_value}")
    model_path = Path(model_value)
    if not model_path.exists():
        raise FileNotFoundError(f"Model ref artifact does not exist: {model_path}")
    metrics_value = str(item.get("metrics") or "")
    if "${" in metrics_value:
        raise ValueError(f"Metrics ref still contains an unresolved ClearML placeholder: {metrics_value}")
    metrics_path = Path(metrics_value)
    metrics = read_json(metrics_path) if metrics_path.exists() else {}
    model_info_path = Path(str(item.get("model_info") or "")) if item.get("model_info") else None
    model_info = read_json(model_info_path) if model_info_path and model_info_path.exists() else {}
    model_name = str(item.get("model_name") or model_info.get("model_name") or model_path.parent.name.replace("train_", ""))
    model_params = item.get("model_params")
    if model_params is None:
        model_params = model_info.get("model_params") or {}
    if not isinstance(model_params, dict):
        raise ValueError(f"model_params for {model_name} must be a mapping.")
    return {
        "stage": str(item.get("stage") or f"train_{_safe_name(model_name)}"),
        "stage_dir": model_path.parent,
        "model_name": model_name,
        "model_params": dict(model_params),
        "artifact_kind": str(item.get("artifact_kind") or model_info.get("artifact_kind") or "model"),
        "estimator": load_joblib(model_path),
        "metrics": metrics,
        "artifacts": {
            "model": model_path,
            "metrics": metrics_path,
            **({"model_info": model_info_path} if model_info_path is not None else {}),
        },
        "tables": (
            {"validation_predictions": Path(str(item["validation_predictions"]))}
            if item.get("validation_predictions")
            else {}
        ),
    }


def _model_refs(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    raw = _json_value(inputs.get("model_refs"), default=[])
    if not isinstance(raw, list):
        raise ValueError("stage_inputs.model_refs must be a JSON array.")
    refs = [_model_ref(dict(item)) for item in raw]
    if not refs:
        raise ValueError("stage_inputs.model_refs must contain at least one model ref.")
    return refs


def _ensemble_ref(inputs: dict[str, Any]) -> dict[str, Any] | None:
    raw = _json_value(inputs.get("ensemble_ref"), default=None)
    if not raw:
        return None
    if not isinstance(raw, dict):
        raise ValueError("stage_inputs.ensemble_ref must be a JSON object.")
    ref = _model_ref(dict(raw))
    ref["artifact_kind"] = "ensemble"
    if raw.get("ensemble_info"):
        ref["artifacts"]["ensemble_info"] = Path(str(raw["ensemble_info"]))
    if raw.get("ensemble_predictions"):
        ref["tables"]["ensemble_predictions"] = Path(str(raw["ensemble_predictions"]))
    return ref


def _metric_settings(cfg: dict[str, Any]) -> tuple[str, list[str] | str | None]:
    selection_metric = _metric_name(cfg.get("model", {}).get("selection_metric") or "rmse")
    metric_names = _metric_names(cfg.get("metrics", {}).get("names"), selection_metric)
    return selection_metric, metric_names


def _run_preprocess(cfg: dict[str, Any]) -> RunResult:
    run_dir = _run_dir(cfg, "preprocess_features")
    stage = _preprocess_features(cfg, run_dir)
    return _finish_stage(
        cfg,
        run_dir,
        metrics={},
        artifacts=stage["artifacts"],
        tables=stage["tables"],
        extra={
            "pipeline_stage": "preprocess_features",
            "artifacts": {key: str(value) for key, value in stage["artifacts"].items()},
            "tables": {key: str(value) for key, value in stage["tables"].items()},
        },
    )


def _run_train_model(cfg: dict[str, Any]) -> RunResult:
    preprocess = _load_preprocess(cfg)
    _, metric_names = _metric_settings(cfg)
    model_cfg = cfg.get("model", {})
    model_name = str(model_cfg.get("name") or "ridge")
    model_params = model_cfg.get("params") or {}
    if not isinstance(model_params, dict):
        raise ValueError("model.params must be a mapping for train_model stage.")

    run_dir = _run_dir(cfg, f"train_{_safe_name(model_name)}")
    result = _train_model(cfg, preprocess, {"name": model_name, "params": model_params}, run_dir, metric_names)
    return _finish_stage(
        cfg,
        run_dir,
        metrics=result["metrics"],
        artifacts=result["artifacts"],
        tables=result["tables"],
        extra={
            "pipeline_stage": "train_model",
            "stage_name": result["stage"],
            "model_name": result["model_name"],
            "model_params": result["model_params"],
        },
    )


def _run_build_ensemble(cfg: dict[str, Any]) -> RunResult:
    preprocess = _load_preprocess(cfg)
    inputs = _stage_inputs(cfg)
    selection_metric, metric_names = _metric_settings(cfg)
    refs = _model_refs(inputs)
    ranked = _ranked_results(refs, selection_metric)

    run_dir = _run_dir(cfg, "build_ensemble")
    result = _build_ensemble(cfg, preprocess, ranked, run_dir, metric_names, selection_metric)
    if result is None:
        raise ValueError("build_ensemble stage requires model.ensemble.enabled=true.")
    return _finish_stage(
        cfg,
        run_dir,
        metrics=result["metrics"],
        artifacts=result["artifacts"],
        tables=result["tables"],
        extra={
            "pipeline_stage": "build_ensemble",
            "stage_name": "build_ensemble",
            "model_name": result["model_name"],
            "selected_base_models": result.get("selected_base_models", []),
        },
    )


def _run_evaluate_models(cfg: dict[str, Any]) -> RunResult:
    inputs = _stage_inputs(cfg)
    selection_metric, _ = _metric_settings(cfg)
    model_refs = _model_refs(inputs)
    ensemble = _ensemble_ref(inputs)

    run_dir = _run_dir(cfg, "evaluate_models")
    result = _evaluate_models(cfg, model_refs, ensemble, run_dir, selection_metric)
    artifacts = dict(result["artifacts"])
    tables = dict(result["tables"])
    metrics = dict(result["metrics"])
    metrics_path = artifacts.get("metrics")
    if metrics_path is None:
        metrics_path = run_dir / "metrics.json"
    best_model_path = artifacts.get("best_model")
    if best_model_path and best_model_path.exists():
        copied = run_dir / "best_model.joblib"
        if best_model_path != copied:
            shutil.copy2(best_model_path, copied)
            artifacts["best_model"] = copied
    return _finish_stage(
        cfg,
        run_dir,
        metrics=metrics,
        artifacts=artifacts,
        tables=tables,
        extra={
            "pipeline_stage": "evaluate_models",
            "stage_name": "evaluate_models",
            "best_model": result["report"]["best_model"],
            "candidate_count": result["report"]["candidate_count"],
            "ensemble_enabled": result["report"]["ensemble_enabled"],
        },
    )


def _run_search_trials_stage(cfg: dict[str, Any]) -> RunResult:
    preprocess = _load_preprocess(cfg)
    selection_metric, metric_names = _metric_settings(cfg)
    run_dir = _run_dir(cfg, "search_trials")
    result = _run_search_trials(cfg, preprocess, run_dir, metric_names, selection_metric)
    return _finish_stage(
        cfg,
        run_dir,
        metrics=result["metrics"],
        artifacts=result["artifacts"],
        tables=result["tables"],
        extra={
            "pipeline_stage": "search_trials",
            "stage_name": "search_trials",
            "search": result["search"],
        },
    )


def _run_retrain_best_stage(cfg: dict[str, Any]) -> RunResult:
    preprocess = _load_preprocess(cfg)
    inputs = _stage_inputs(cfg)
    best_params_path = _required_path(inputs, "best_params")
    run_dir = _run_dir(cfg, "retrain_best")
    result = _retrain_best(cfg, preprocess, best_params_path, run_dir)
    return _finish_stage(
        cfg,
        run_dir,
        metrics=result["metrics"],
        artifacts=result["artifacts"],
        extra={
            "pipeline_stage": "retrain_best",
            "stage_name": "retrain_best",
            "model_name": result["model_name"],
            "model_params": result["model_params"],
        },
    )


def _run_evaluate_best_stage(cfg: dict[str, Any]) -> RunResult:
    inputs = _stage_inputs(cfg)
    selection_metric, _ = _metric_settings(cfg)
    best_params_path = _required_path(inputs, "best_params")
    optimization_summary_path = _required_path(inputs, "optimization_summary")
    model_path = _required_path(inputs, "model")
    model_info_path = _required_path(inputs, "model_info")

    run_dir = _run_dir(cfg, "evaluate_best")
    result = _evaluate_best(
        cfg,
        best_params_path,
        optimization_summary_path,
        model_path,
        model_info_path,
        run_dir,
        selection_metric,
    )
    return _finish_stage(
        cfg,
        run_dir,
        metrics=result["metrics"],
        artifacts=result["artifacts"],
        extra={
            "pipeline_stage": "evaluate_best",
            "stage_name": "evaluate_best",
            "best_model": result["report"]["best_model"],
        },
    )


def run_stage(cfg: dict[str, Any]) -> RunResult:
    stage = str(cfg.get("run", {}).get("stage") or "").strip()
    if not stage:
        raise ValueError("run.stage is required for tabular_stage.")
    if stage == "preprocess_features":
        return _run_preprocess(cfg)
    if stage == "train_model":
        return _run_train_model(cfg)
    if stage == "build_ensemble":
        return _run_build_ensemble(cfg)
    if stage == "evaluate_models":
        return _run_evaluate_models(cfg)
    if stage == "search_trials":
        return _run_search_trials_stage(cfg)
    if stage == "retrain_best":
        return _run_retrain_best_stage(cfg)
    if stage == "evaluate_best":
        return _run_evaluate_best_stage(cfg)
    raise ValueError(
        "Unsupported tabular stage: "
        f"{stage}. Available: preprocess_features, train_model, build_ensemble, "
        "evaluate_models, search_trials, retrain_best, evaluate_best."
    )
