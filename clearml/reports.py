from __future__ import annotations

import json
from numbers import Real
from pathlib import Path
from typing import Any

from ml_platform_core.result import RunResult

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
TABLE_REPORTS = {
    "leaderboard",
    "validation_predictions",
    "evaluation_predictions",
    "evaluation_summary",
    "predictions",
    "prediction_summary",
    "prediction_preview",
    "feature_summary_table",
    "feature_summary",
    "missing_rate_by_column",
    "feature_missingness",
    "feature_type_counts",
    "metrics_table",
    "metrics_by_candidate",
    "ensemble_metrics_table",
}
TABLE_SERIES_ALIASES = {
    "leaderboard": "leaderboard_table",
    "predictions": "predictions_table",
    "prediction_summary": "prediction_summary_table",
    "prediction_preview": "prediction_preview_table",
}
TABLE_REPORT_PREFIXES = (
    "ensemble_predictions",
    "feature_importance",
    "ensemble_members",
    "ensemble_weights",
    "metrics_table",
)
PREDICTION_PLOT_TABLES = {"validation_predictions", "evaluation_predictions", "ensemble_predictions", "predictions"}


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


def _report_candidate_metrics(adapter, path: str | Path, *, title_prefix: str) -> None:
    payload = _read_json(path)
    by_candidate = payload.get("metrics_by_candidate") or payload.get("metrics_by_model") or {}
    if not isinstance(by_candidate, dict):
        return
    for model_name, model_payload in by_candidate.items():
        if not isinstance(model_payload, dict):
            continue
        metrics = _numeric_metrics(model_payload)
        for metric_name, value in metrics.items():
            adapter.report_scalar(f"{title_prefix}/{metric_name}", str(model_name), value, iteration=0)
        if model_payload.get("artifact_kind") == "ensemble":
            series = str(model_payload.get("ensemble_method") or model_name)
            for metric_name, value in metrics.items():
                adapter.report_scalar(f"ensemble/{metric_name}", series, value, iteration=0)


def _report_best_model_metrics(adapter, metrics_payload: dict[str, Any]) -> None:
    best_model = metrics_payload.get("best_model")
    if not isinstance(best_model, dict):
        return
    series = str(best_model.get("model_name") or best_model.get("ensemble_method") or "best")
    for metric_name, value in _numeric_metrics(best_model).items():
        adapter.report_scalar(f"best_model/{metric_name}", series, value, iteration=0)
        # Compatibility for older ClearML views/tests that grouped best metrics
        # under one title with metric names as series.
        adapter.report_scalar("best_model", metric_name, value, iteration=0)


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
    try:
        import pandas as pd

        frame = pd.read_csv(path)
    except Exception:
        return
    if not {"metric", "value"} <= set(frame.columns):
        return
    for row in frame.itertuples(index=False):
        try:
            value = float(row.value)
        except (TypeError, ValueError):
            continue
        adapter.report_scalar(title, str(row.metric), value, iteration=0)


def _report_ensemble_metrics_table(adapter, path: str | Path) -> None:
    try:
        import pandas as pd

        frame = pd.read_csv(path)
    except Exception:
        return
    if "ensemble_method" not in frame.columns:
        return
    for row in frame.to_dict(orient="records"):
        series = str(row.get("ensemble_method") or row.get("model_name") or "ensemble")
        for metric_name in MODEL_METRICS:
            value = row.get(metric_name)
            if isinstance(value, Real):
                adapter.report_scalar(f"ensemble/{metric_name}", series, float(value), iteration=0)


def _report_prediction_plots(adapter, table_name: str, path: str | Path) -> None:
    report_scatter = getattr(adapter, "report_scatter", None)
    report_histogram = getattr(adapter, "report_histogram", None)
    if not callable(report_scatter) and not callable(report_histogram):
        return
    try:
        import pandas as pd

        frame = pd.read_csv(path)
    except Exception:
        return
    if "prediction" not in frame:
        return
    prediction = pd.to_numeric(frame["prediction"], errors="coerce")
    if "actual" not in frame:
        values = prediction.dropna()
        if table_name == "predictions" and callable(report_histogram) and not values.empty:
            report_histogram("prediction_distribution", table_name, [float(value) for value in values], iteration=0)
        return
    actual = pd.to_numeric(frame["actual"], errors="coerce")
    valid = actual.notna() & prediction.notna()
    if not valid.any():
        return
    actual = actual[valid]
    prediction = prediction[valid]
    if callable(report_scatter):
        points = [(float(a), float(p)) for a, p in zip(actual, prediction)]
        report_scatter("prediction_vs_actual", table_name, points, iteration=0)
    if callable(report_histogram):
        if "residual" in frame:
            residual = pd.to_numeric(frame.loc[valid, "residual"], errors="coerce").dropna()
        else:
            residual = actual - prediction
        report_histogram("residual_histogram", table_name, [float(value) for value in residual], iteration=0)


def _is_report_table(name: str) -> bool:
    return name in TABLE_REPORTS or any(name.startswith(prefix) for prefix in TABLE_REPORT_PREFIXES)


def _is_prediction_plot_table(name: str) -> bool:
    return name in PREDICTION_PLOT_TABLES or name.startswith("ensemble_predictions")


def _report_table(adapter, name: str, path: str | Path) -> None:
    adapter.report_table("tables", TABLE_SERIES_ALIASES.get(name, name), path, iteration=0)


def _report_plot_image(adapter, name: str, path: str | Path) -> None:
    report_image = getattr(adapter, "report_image", None)
    if callable(report_image):
        report_image("plots", name, path, iteration=0)
        return
    report_media = getattr(adapter, "report_media", None)
    if callable(report_media):
        report_media("plots", name, path, iteration=0)


def report_result(adapter, result: RunResult, *, report_plots: bool = True) -> None:
    """Report RunResult to ClearML.

    Keep this small: upload artifacts/tables, publish scalar metrics, and turn
    standard prediction tables into ClearML-native plots when requested.
    """
    for name, value in result.metrics.items():
        if isinstance(value, Real):
            adapter.report_scalar("metrics", name, float(value), iteration=0)
    _report_best_model_metrics(adapter, result.metrics)

    for name, path in result.artifacts.items():
        adapter.upload_artifact(name, path)
        if name == "metrics":
            _report_plain_metrics(adapter, _read_json(path))
        if name == "feature_summary":
            _report_feature_summary_metrics(adapter, path)
        if name == "metrics_by_model":
            _report_candidate_metrics(adapter, path, title_prefix="metrics_by_model")
        if name == "metrics_by_candidate":
            _report_candidate_metrics(adapter, path, title_prefix="metrics_by_candidate")

    for name, path in result.tables.items():
        adapter.upload_artifact(name, path)
        if _is_report_table(name):
            _report_table(adapter, name, path)
        if name == "metrics_table" or name.startswith("metrics_table_"):
            _report_metrics_table(adapter, path)
        if name == "ensemble_metrics_table":
            _report_ensemble_metrics_table(adapter, path)
        if report_plots and _is_prediction_plot_table(name):
            _report_prediction_plots(adapter, name, path)

    for name, path in result.plots.items():
        adapter.upload_artifact(name, path)
        if report_plots:
            _report_plot_image(adapter, name, path)
