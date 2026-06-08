from __future__ import annotations

import json
from numbers import Real
from pathlib import Path
from typing import Any

from ml_platform_core.result import RunResult

MODEL_METRICS = ("rmse", "mae", "r2")
TABLE_REPORTS = {"leaderboard", "evaluation_predictions", "predictions"}


def _read_json(path: str | Path) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _numeric_metrics(payload: dict[str, Any]) -> dict[str, float]:
    metrics = payload.get("metrics", payload)
    if not isinstance(metrics, dict):
        return {}
    return {
        name: float(metrics[name])
        for name in MODEL_METRICS
        if isinstance(metrics.get(name), Real)
    }


def _report_metrics_by_model(adapter, path: str | Path) -> None:
    payload = _read_json(path)
    by_model = payload.get("metrics_by_model", {})
    if not isinstance(by_model, dict):
        return
    for model_name, model_payload in by_model.items():
        if not isinstance(model_payload, dict):
            continue
        metrics = _numeric_metrics(model_payload)
        for metric_name, value in metrics.items():
            adapter.report_scalar(f"metrics_by_model/{metric_name}", str(model_name), value, iteration=0)
        if model_payload.get("artifact_kind") == "ensemble":
            for metric_name, value in metrics.items():
                adapter.report_scalar("ensemble", metric_name, value, iteration=0)


def _report_best_model_metrics(adapter, metrics_payload: dict[str, Any]) -> None:
    best_model = metrics_payload.get("best_model")
    if not isinstance(best_model, dict):
        return
    for metric_name, value in _numeric_metrics(best_model).items():
        adapter.report_scalar("best_model", metric_name, value, iteration=0)


def report_result(adapter, result: RunResult, *, report_plots: bool = True) -> None:
    """Report RunResult to ClearML.

    Keep this generic and avoid tabular-specific assumptions.
    """
    for name, value in result.metrics.items():
        if isinstance(value, Real):
            adapter.report_scalar("metrics", name, float(value), iteration=0)
    _report_best_model_metrics(adapter, result.metrics)

    for name, path in result.artifacts.items():
        adapter.upload_artifact(name, path)
        if name == "metrics_by_model":
            _report_metrics_by_model(adapter, path)

    for name, path in result.tables.items():
        adapter.upload_artifact(name, path)
        if name in TABLE_REPORTS:
            adapter.report_table("tables", name, path, iteration=0)

    for name, path in result.plots.items():
        adapter.upload_artifact(name, path)
        if report_plots:
            adapter.report_media("plots", name, path, iteration=0)
