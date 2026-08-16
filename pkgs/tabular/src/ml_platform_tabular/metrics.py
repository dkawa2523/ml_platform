from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path

import numpy as np
import pandas as pd

from .target_sources import SOURCE_ROW_COLUMN, TARGET_COLUMN

DEFAULT_REGRESSION_METRICS = ("mae", "rmse", "r2")


def _normalize_metric_name(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _normalize_metric_names(metrics: Iterable[str] | str | None) -> tuple[str, ...]:
    if metrics is None:
        return DEFAULT_REGRESSION_METRICS
    names = _metric_names_from_text(metrics) if isinstance(metrics, str) else tuple(metrics)
    if not names:
        raise ValueError("At least one regression metric is required.")
    return names


def _metric_names_from_text(metrics: str) -> tuple[str, ...]:
    return tuple(name.strip() for name in metrics.split(",") if name.strip())


def regression_metrics(y_true, y_pred, metrics: Iterable[str] | str | None = None) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=float).reshape(-1)
    y_pred = np.asarray(y_pred, dtype=float).reshape(-1)
    if y_true.shape[0] != y_pred.shape[0]:
        raise ValueError("y_true and y_pred must have the same length.")
    if y_true.shape[0] == 0:
        raise ValueError("y_true and y_pred must not be empty.")
    if not np.isfinite(y_true).all() or not np.isfinite(y_pred).all():
        raise ValueError("y_true and y_pred must contain only finite values.")

    selected = _normalize_metric_names(metrics)
    if y_true.shape[0] < 2 and any(_normalize_metric_name(name) == "r2" for name in selected):
        raise ValueError("r2 requires at least two samples.")
    values = _regression_metric_values(y_true, y_pred)
    return _selected_metric_values(values, selected)


def target_regression_metrics(
    y_true,
    y_pred,
    targets,
    *,
    metrics: Iterable[str] | str | None = None,
    baseline_means: Mapping[str, float] | None = None,
) -> tuple[dict[str, float], pd.DataFrame]:
    """Calculate target-level diagnostics and equal-target macro metrics."""
    actual, prediction, target_series = _target_metric_inputs(y_true, y_pred, targets)
    selected, raw_metrics = _target_metric_plan(metrics)
    rows, values_by_metric = _target_metric_rows(
        actual,
        prediction,
        target_series,
        raw_metrics,
        baseline_means,
    )
    all_aggregates = _append_macro_metric_rows(rows, values_by_metric, len(actual))
    requested = [_normalize_metric_name(name) for name in selected]
    aggregate = {name: all_aggregates[name] for name in requested if name in all_aggregates}
    return aggregate, pd.DataFrame(rows)


def _target_metric_inputs(y_true, y_pred, targets) -> tuple[pd.Series, np.ndarray, pd.Series]:
    actual = pd.Series(np.asarray(y_true, dtype=float).reshape(-1))
    prediction = np.asarray(y_pred, dtype=float).reshape(-1)
    target_series = pd.Series(targets).reset_index(drop=True)
    if len(actual) != len(prediction) or len(actual) != len(target_series):
        raise ValueError("y_true, y_pred, and targets must have the same length.")
    if target_series.isna().any():
        raise ValueError("targets must not contain missing values.")
    return actual, prediction, target_series.astype(str)


def _target_metric_plan(metrics: Iterable[str] | str | None) -> tuple[tuple[str, ...], tuple[str, ...]]:
    selected = _normalize_metric_names(metrics)
    derived = {"relative_rmse", "skill"}
    unknown = [
        name for name in selected if _normalize_metric_name(name) not in {*DEFAULT_REGRESSION_METRICS, "mse", *derived}
    ]
    if unknown:
        raise ValueError(f"Unsupported regression metric: {unknown[0]}")
    raw_metrics = tuple(name for name in selected if _normalize_metric_name(name) not in derived)
    return selected, raw_metrics


def _target_metric_rows(
    actual: pd.Series,
    prediction: np.ndarray,
    target_series: pd.Series,
    raw_metrics: tuple[str, ...],
    baseline_means: Mapping[str, float] | None,
) -> tuple[list[dict[str, object]], dict[str, list[float]]]:
    rows: list[dict[str, object]] = []
    values_by_metric: dict[str, list[float]] = {}
    for target in target_series.drop_duplicates():
        target = str(target)
        mask = target_series.eq(target).to_numpy()
        values = regression_metrics(actual[mask], prediction[mask], metrics=raw_metrics)
        _append_target_metric_rows(rows, values_by_metric, target, values, int(mask.sum()))
        if baseline_means is not None:
            baseline_values = _relative_target_metrics(
                actual[mask].to_numpy(),
                prediction[mask],
                baseline_means,
                target,
            )
            _append_target_metric_rows(rows, values_by_metric, target, baseline_values, int(mask.sum()))
    return rows, values_by_metric


def _append_macro_metric_rows(
    rows: list[dict[str, object]], values_by_metric: Mapping[str, list[float]], observation_count: int
) -> dict[str, float]:
    all_aggregates = {name: float(np.mean(values)) for name, values in values_by_metric.items() if values}
    for name, value in all_aggregates.items():
        rows.append(
            {
                "target": "__macro__",
                "metric": name,
                "value": value,
                "observation_count": observation_count,
            }
        )
    return all_aggregates


def target_means(y, targets) -> dict[str, float]:
    frame = pd.DataFrame(
        {
            "target": pd.Series(targets).reset_index(drop=True).astype(str),
            "value": np.asarray(y, dtype=float).reshape(-1),
        }
    )
    return {str(target): float(value) for target, value in frame.groupby("target", sort=False)["value"].mean().items()}


def target_labels(frame: pd.DataFrame, target_names: list[str]) -> pd.Series:
    if TARGET_COLUMN in frame.columns:
        return frame[TARGET_COLUMN].astype(str)
    if len(target_names) == 1:
        return pd.Series(target_names[0], index=frame.index)
    raise ValueError(f"Data is missing required target routing column: {TARGET_COLUMN}")


def _append_target_metric_rows(
    rows: list[dict[str, object]],
    values_by_metric: dict[str, list[float]],
    target: str,
    values: Mapping[str, float],
    observation_count: int,
) -> None:
    for name, value in values.items():
        value = float(value)
        rows.append(
            {
                "target": target,
                "metric": name,
                "value": value,
                "observation_count": observation_count,
            }
        )
        if np.isfinite(value):
            values_by_metric.setdefault(name, []).append(value)


def _relative_target_metrics(
    actual: np.ndarray,
    prediction: np.ndarray,
    baseline_means: Mapping[str, float],
    target: str,
) -> dict[str, float]:
    if target not in baseline_means:
        raise ValueError(f"Missing training baseline for target: {target}")
    model_rmse = float(np.sqrt(np.mean((actual - prediction) ** 2)))
    baseline_rmse = float(np.sqrt(np.mean((actual - float(baseline_means[target])) ** 2)))
    if baseline_rmse == 0.0:
        return {"baseline_rmse": 0.0}
    relative_rmse = model_rmse / baseline_rmse
    return {
        "baseline_rmse": baseline_rmse,
        "relative_rmse": relative_rmse,
        "skill": 1.0 - relative_rmse,
    }


def _regression_metric_values(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    residual = y_true - y_pred
    mae = float(np.mean(np.abs(residual)))
    mse = float(np.mean(residual**2))
    rmse = float(np.sqrt(mse))
    residual_sum = float(np.sum(residual**2))
    denom = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = float(residual_sum == 0.0) if denom < np.finfo(float).tiny else 1.0 - residual_sum / denom
    return {"mae": mae, "rmse": rmse, "r2": float(r2), "mse": mse}


def _selected_metric_values(values: dict[str, float], selected: tuple[str, ...]) -> dict[str, float]:
    result: dict[str, float] = {}
    for name in selected:
        key = _normalize_metric_name(name)
        if not key:
            continue
        if key not in values:
            raise ValueError(f"Unsupported regression metric: {name}")
        result[key] = values[key]
    return result


def regression_prediction_frame(base_frame, y_true, y_pred, *, model_name: str | None = None) -> pd.DataFrame:
    """Return a compact prediction table with residual columns."""
    frame = pd.DataFrame(base_frame).reset_index(drop=True).copy()
    frame = frame.rename(columns={TARGET_COLUMN: "target", SOURCE_ROW_COLUMN: "source_row"})
    actual = np.asarray(y_true, dtype=float).reshape(-1)
    prediction = np.asarray(y_pred, dtype=float).reshape(-1)
    if len(frame) != actual.shape[0] or actual.shape[0] != prediction.shape[0]:
        raise ValueError("Prediction frame, y_true, and y_pred must have the same length.")
    residual = actual - prediction
    frame["actual"] = actual
    frame["prediction"] = prediction
    frame["residual"] = residual
    frame["abs_error"] = np.abs(residual)
    if model_name:
        frame["model_name"] = model_name
    return frame


def write_regression_plot_artifacts(y_true, y_pred, output_dir: Path, *, prefix: str = "validation") -> dict[str, Path]:
    from .plotting import write_regression_plot_artifacts as _write_regression_plot_artifacts

    return _write_regression_plot_artifacts(y_true, y_pred, output_dir, prefix=prefix)
