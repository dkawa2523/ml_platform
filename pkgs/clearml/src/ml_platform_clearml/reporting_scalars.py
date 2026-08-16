from __future__ import annotations

import json
from numbers import Integral, Real
from pathlib import Path
from typing import Any

from .support import read_csv_for_reporting

MODEL_METRICS = ("rmse", "mae", "r2")
DATA_QUALITY_SCALARS = (
    "row_count",
    "train_rows",
    "valid_rows",
    "feature_count",
    "numeric_feature_count",
    "categorical_feature_count",
    "passthrough_feature_count",
    "dropped_feature_count",
    "transformed_feature_count",
)


def report_result_metrics(adapter, metrics_payload: dict[str, Any]) -> None:
    for name, value in metrics_payload.items():
        if isinstance(value, Real) and not isinstance(value, Integral):
            adapter.report_scalar("metrics", name, float(value), iteration=0)
    _report_best_model_metrics(adapter, metrics_payload)


def report_artifact_scalars(adapter, name: str, path: str | Path) -> None:
    reporters = {
        "metrics": _report_metrics_artifact,
        "data_quality_summary": _report_data_quality_metrics,
    }
    reporter = reporters.get(name)
    if reporter is not None:
        reporter(adapter, path)


def report_table_scalars(adapter, name: str, path: str | Path) -> None:
    if name == "ensemble_metrics_table":
        _report_ensemble_metrics_table(adapter, path)


def _report_metrics_artifact(adapter, path: str | Path) -> None:
    _report_best_model_metrics(adapter, _read_json(path))


def _read_json(path: str | Path) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def _numeric_metrics(payload: dict[str, Any]) -> dict[str, float]:
    metrics = payload.get("metrics", payload)
    if not isinstance(metrics, dict):
        return {}
    return {name: float(metrics[name]) for name in MODEL_METRICS if isinstance(metrics.get(name), Real)}


def _report_best_model_metrics(adapter, metrics_payload: dict[str, Any]) -> None:
    best_model = metrics_payload.get("best_model")
    if not isinstance(best_model, dict):
        return
    series = str(best_model.get("model_name") or best_model.get("ensemble_method") or "best")
    for metric_name, value in _numeric_metrics(best_model).items():
        adapter.report_scalar(f"best_model/{metric_name}", series, value, iteration=0)


def _report_data_quality_metrics(adapter, path: str | Path) -> None:
    payload = _read_json(path)
    for key in DATA_QUALITY_SCALARS:
        value = payload.get(key)
        if isinstance(value, Real):
            adapter.report_scalar("features", key, float(value), iteration=0)


def _report_ensemble_metrics_table(adapter, path: str | Path) -> None:
    frame = read_csv_for_reporting(path)
    if frame is None or "ensemble_method" not in frame.columns:
        return
    for row in frame.to_dict(orient="records"):
        _report_ensemble_metric_row(adapter, {str(key): value for key, value in row.items()})


def _report_ensemble_metric_row(adapter, row: dict[str, Any]) -> None:
    series = str(row.get("ensemble_method") or row.get("model_name") or "ensemble")
    for metric_name in MODEL_METRICS:
        value = row.get(metric_name)
        if isinstance(value, Real):
            adapter.report_scalar(f"ensemble/{metric_name}", series, float(value), iteration=0)
