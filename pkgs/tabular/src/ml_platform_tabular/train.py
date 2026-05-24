from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ml_platform_core.artifacts import (
    prepare_run_dir,
    update_latest,
    write_config_snapshot,
    write_manifest,
)
from ml_platform_core.io import dump_joblib, write_json, write_table
from ml_platform_core.result import RunResult

from .data import load_dataset, split_xy, train_valid_split
from .features import build_feature_pipeline
from .metrics import DEFAULT_REGRESSION_METRICS, regression_metrics
from .model_artifact import write_model_info
from .models import TabularEstimator, build_model


def _model_candidates(model_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    raw_candidates = model_cfg.get("candidates") or []
    if not raw_candidates:
        return [
            {
                "name": model_cfg.get("name", "ridge"),
                "params": model_cfg.get("params") or {},
            }
        ]
    if not isinstance(raw_candidates, list):
        raise ValueError("model.candidates must be a list of model definitions.")

    candidates: list[dict[str, Any]] = []
    for index, item in enumerate(raw_candidates):
        if not isinstance(item, dict):
            raise ValueError(f"model.candidates[{index}] must be a mapping.")
        name = item.get("name")
        if not name:
            raise ValueError(f"model.candidates[{index}].name is required.")
        params = item.get("params") or {}
        if not isinstance(params, dict):
            raise ValueError(f"model.candidates[{index}].params must be a mapping.")
        candidates.append({"name": str(name), "params": dict(params)})
    return candidates


def _metric_name(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _metric_names_for_training(metric_names: Any, selection_metric: str) -> list[str] | str | None:
    if metric_names is None:
        names = list(DEFAULT_REGRESSION_METRICS)
        if selection_metric not in names:
            names.append(selection_metric)
        return names
    if isinstance(metric_names, str):
        names = [_metric_name(name) for name in metric_names.split(",") if name.strip()]
    else:
        names = [_metric_name(name) for name in metric_names]
    if selection_metric not in names:
        names.append(selection_metric)
    return names


def _metric_columns(metric_names: Any, metrics: dict[str, float]) -> list[str]:
    if metric_names is None:
        return list(metrics)
    if isinstance(metric_names, str):
        return [_metric_name(name) for name in metric_names.split(",") if name.strip()]
    return [_metric_name(name) for name in metric_names]


def _selection_sort_value(metrics: dict[str, float], selection_metric: str) -> float:
    if selection_metric not in metrics:
        raise ValueError(f"selection_metric is missing from metrics: {selection_metric}")
    value = float(metrics[selection_metric])
    return -value if selection_metric == "r2" else value


def _leaderboard_rows(
    candidate_results: list[dict[str, Any]],
    *,
    metric_names: list[str],
    selection_metric: str,
) -> list[dict[str, Any]]:
    ranked = sorted(candidate_results, key=lambda item: _selection_sort_value(item["metrics"], selection_metric))
    rows = []
    for rank, item in enumerate(ranked, start=1):
        metrics = item["metrics"]
        row = {
            "rank": rank,
            "model_name": item["model_name"],
            "model_params": json.dumps(item["model_params"], sort_keys=True, default=str),
        }
        for name in metric_names:
            row[name] = metrics.get(name)
        row["selection_metric"] = selection_metric
        row["selection_value"] = metrics.get(selection_metric)
        row["selected"] = rank == 1
        rows.append(row)
    return rows


def run_train(cfg: dict[str, Any]) -> RunResult:
    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    run_name = cfg.get("run", {}).get("name", "tabular_train")
    run_dir = prepare_run_dir(output_dir, run_name)

    df = load_dataset(cfg)
    X, y, feature_names = split_xy(df, cfg)
    X_train, X_valid, y_train, y_valid = train_valid_split(X, y, cfg)

    feature_cfg = cfg.get("features", {})
    feature_preset = feature_cfg.get("preset", "basic")
    transformer = build_feature_pipeline(feature_preset, X_train, feature_cfg.get("params") or {})

    model_cfg = cfg.get("model", {})
    metric_names = cfg.get("metrics", {}).get("names")
    selection_metric = _metric_name(model_cfg.get("selection_metric") or "rmse")
    train_metric_names = _metric_names_for_training(metric_names, selection_metric)
    candidates = _model_candidates(model_cfg)

    candidate_results = []
    for candidate in candidates:
        model = build_model(candidate["name"], candidate["params"])
        estimator = TabularEstimator(transformer=transformer, model=model, feature_columns=feature_names)
        estimator.fit(X_train, y_train)
        y_pred = estimator.predict(X_valid)
        metrics = regression_metrics(y_valid, y_pred, metrics=train_metric_names)
        candidate_results.append(
            {
                "model_name": candidate["name"],
                "model_params": candidate["params"],
                "estimator": estimator,
                "predictions": y_pred,
                "metrics": metrics,
            }
        )

    best = min(candidate_results, key=lambda item: _selection_sort_value(item["metrics"], selection_metric))
    model_name = best["model_name"]
    model_params = best["model_params"]
    estimator = best["estimator"]
    y_pred = best["predictions"]
    metrics = best["metrics"]
    predictions_path = write_table(
        X_valid.assign(_target=y_valid.values, _prediction=y_pred),
        run_dir / "validation_predictions.csv",
    )
    model_path = dump_joblib(estimator, run_dir / "model.joblib")
    model_info_path = write_model_info(
        run_dir / "model_info.json",
        feature_columns=feature_names,
        target_column=cfg.get("data", {}).get("target_column"),
        feature_preset=feature_preset,
        model_name=model_name,
        model_params=model_params,
    )
    metrics_path = write_json(metrics, run_dir / "metrics.json")
    config_path = write_config_snapshot(cfg, run_dir)

    artifacts = {
        "model": model_path,
        "model_info": model_info_path,
        "metrics": metrics_path,
        "config": config_path,
    }
    tables = {"validation_predictions": predictions_path}
    if model_cfg.get("candidates"):
        metric_columns = _metric_columns(metric_names, metrics)
        leaderboard_path = write_table(
            pd.DataFrame(_leaderboard_rows(candidate_results, metric_names=metric_columns, selection_metric=selection_metric)),
            run_dir / "leaderboard.csv",
        )
        tables["leaderboard"] = leaderboard_path
    manifest_path = write_manifest(run_dir, config=cfg, metrics=metrics, artifacts=artifacts, tables=tables)
    artifacts["manifest"] = manifest_path

    update_latest(run_dir, output_dir / "latest_train")
    update_latest(run_dir, output_dir / "latest")

    return RunResult(
        run_dir=run_dir,
        metrics=metrics,
        artifacts=artifacts,
        tables=tables,
        extra={"feature_columns": feature_names},
    )
