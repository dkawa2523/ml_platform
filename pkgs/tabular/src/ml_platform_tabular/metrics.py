from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

DEFAULT_REGRESSION_METRICS = ("mae", "rmse", "r2")


def _normalize_metric_name(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _normalize_metric_names(metrics: Iterable[str] | str | None) -> tuple[str, ...]:
    if metrics is None:
        return DEFAULT_REGRESSION_METRICS
    if isinstance(metrics, str):
        names = tuple(name.strip() for name in metrics.split(",") if name.strip())
    else:
        names = tuple(metrics)
    if not names:
        raise ValueError("At least one regression metric is required.")
    return names


def regression_metrics(y_true, y_pred, metrics: Iterable[str] | str | None = None) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=float).reshape(-1)
    y_pred = np.asarray(y_pred, dtype=float).reshape(-1)
    if y_true.shape[0] != y_pred.shape[0]:
        raise ValueError("y_true and y_pred must have the same length.")
    if y_true.shape[0] == 0:
        raise ValueError("y_true and y_pred must not be empty.")

    residual = y_true - y_pred
    mae = float(np.mean(np.abs(residual)))
    mse = float(np.mean(residual**2))
    rmse = float(np.sqrt(mse))
    denom = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = 1.0 - float(np.sum(residual**2)) / denom if denom else 0.0

    values = {"mae": mae, "rmse": rmse, "r2": float(r2), "mse": mse}
    selected = _normalize_metric_names(metrics)
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
    from .plots import write_regression_plot_artifacts as _write_regression_plot_artifacts

    return _write_regression_plot_artifacts(y_true, y_pred, output_dir, prefix=prefix)
