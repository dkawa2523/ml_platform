from __future__ import annotations

import json
from numbers import Real
from pathlib import Path
from typing import Any

MODEL_METRICS = ("rmse", "mae", "r2")
FEATURE_SUMMARY_SCALARS = (
    "input_rows",
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
        if isinstance(value, Real):
            adapter.report_scalar("metrics", name, float(value), iteration=0)
    _report_best_model_metrics(adapter, metrics_payload)


def report_artifact_scalars(adapter, name: str, path: str | Path) -> None:
    reporters = {
        "metrics": _report_metrics_artifact,
        "feature_summary": _report_feature_summary_metrics,
        "metrics_by_candidate": _report_metrics_by_candidate_artifact,
    }
    reporter = reporters.get(name)
    if reporter is not None:
        reporter(adapter, path)


def report_table_scalars(adapter, name: str, path: str | Path) -> None:
    if _is_metrics_table(name):
        _report_metrics_table(adapter, path)
    elif name == "ensemble_metrics_table":
        _report_ensemble_metrics_table(adapter, path)


def _report_metrics_artifact(adapter, path: str | Path) -> None:
    _report_plain_metrics(adapter, _read_json(path))


def _report_metrics_by_candidate_artifact(adapter, path: str | Path) -> None:
    _report_candidate_metrics(adapter, path, title_prefix="metrics_by_candidate")


def _is_metrics_table(name: str) -> bool:
    return name == "metrics_table" or name.startswith("metrics_table_")


def _read_json(path: str | Path) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def _read_csv_or_none(path: str | Path):
    try:
        import pandas as pd

        return pd.read_csv(path)
    except (OSError, UnicodeDecodeError, ValueError):
        return None


def _numeric_metrics(payload: dict[str, Any]) -> dict[str, float]:
    metrics = payload.get("metrics", payload)
    if not isinstance(metrics, dict):
        return {}
    return {name: float(metrics[name]) for name in MODEL_METRICS if isinstance(metrics.get(name), Real)}


def _report_candidate_metrics(adapter, path: str | Path, *, title_prefix: str) -> None:
    payload = _read_json(path)
    by_candidate = payload.get("metrics_by_candidate") or {}
    if not isinstance(by_candidate, dict):
        return
    for model_name, model_payload in by_candidate.items():
        _report_candidate_payload(adapter, str(model_name), model_payload, title_prefix=title_prefix)


def _report_candidate_payload(adapter, model_name: str, payload: Any, *, title_prefix: str) -> None:
    if not isinstance(payload, dict):
        return
    metrics = _numeric_metrics(payload)
    for metric_name, value in metrics.items():
        adapter.report_scalar(f"{title_prefix}/{metric_name}", model_name, value, iteration=0)
    if payload.get("artifact_kind") != "ensemble":
        return
    series = str(payload.get("ensemble_method") or model_name)
    for metric_name, value in metrics.items():
        adapter.report_scalar(f"ensemble/{metric_name}", series, value, iteration=0)


def _report_best_model_metrics(adapter, metrics_payload: dict[str, Any]) -> None:
    best_model = metrics_payload.get("best_model")
    if not isinstance(best_model, dict):
        return
    series = str(best_model.get("model_name") or best_model.get("ensemble_method") or "best")
    for metric_name, value in _numeric_metrics(best_model).items():
        adapter.report_scalar(f"best_model/{metric_name}", series, value, iteration=0)


def _report_feature_summary_metrics(adapter, path: str | Path) -> None:
    payload = _read_json(path)
    for key in FEATURE_SUMMARY_SCALARS:
        value = payload.get(key)
        if isinstance(value, Real):
            adapter.report_scalar("features", key, float(value), iteration=0)


def _report_plain_metrics(adapter, payload: dict[str, Any], *, title: str = "metrics") -> None:
    for metric_name, value in _numeric_metrics(payload).items():
        adapter.report_scalar(title, metric_name, value, iteration=0)
    _report_best_model_metrics(adapter, payload)


def _report_metrics_table(adapter, path: str | Path, *, title: str = "metrics") -> None:
    frame = _read_csv_or_none(path)
    if frame is None or not {"metric", "value"} <= set(frame.columns):
        return
    for row in frame.itertuples(index=False):
        _report_metric_row(adapter, row, title=title)


def _report_metric_row(adapter, row: Any, *, title: str) -> None:
    try:
        value = float(row.value)
    except (TypeError, ValueError):
        return
    adapter.report_scalar(title, str(row.metric), value, iteration=0)


def _report_ensemble_metrics_table(adapter, path: str | Path) -> None:
    frame = _read_csv_or_none(path)
    if frame is None or "ensemble_method" not in frame.columns:
        return
    for row in frame.to_dict(orient="records"):
        _report_ensemble_metric_row(adapter, row)


def _report_ensemble_metric_row(adapter, row: dict[str, Any]) -> None:
    series = str(row.get("ensemble_method") or row.get("model_name") or "ensemble")
    for metric_name in MODEL_METRICS:
        value = row.get(metric_name)
        if isinstance(value, Real):
            adapter.report_scalar(f"ensemble/{metric_name}", series, float(value), iteration=0)
