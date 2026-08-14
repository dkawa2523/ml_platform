from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from ..plotting import (
    write_feature_importance_plot_if_available,
    write_prediction_vs_actual_plot,
    write_residual_histogram,
    write_residual_vs_predicted_plot,
)
from .artifacts import CandidateResult


PREDICTION_COLUMNS = {"actual", "prediction"}


def prediction_table_path(item: CandidateResult) -> Path | None:
    path = item.tables.get("validation_predictions") or item.tables.get("ensemble_predictions")
    return Path(path) if path else None


def _prediction_frame(item: CandidateResult) -> pd.DataFrame | None:
    source = prediction_table_path(item)
    if source is None or not source.exists():
        return None
    frame = pd.read_csv(source)
    if not PREDICTION_COLUMNS <= set(frame.columns):
        return None
    return frame


def write_evaluation_diagnostics(
    best: CandidateResult,
    stage_dir: Path,
) -> tuple[Path | None, dict[str, Path], dict[str, Path]]:
    source = prediction_table_path(best)
    if source is None or not source.exists():
        return None, {}, {}
    frame = _prediction_frame(best)
    destination = stage_dir / "evaluation_predictions.csv"
    if source != destination:
        shutil.copy2(source, destination)
    tables: dict[str, Path] = {}
    plots = _best_prediction_plots(frame, stage_dir) if frame is not None else {}
    importance_table, importance_plot = write_feature_importance_plot_if_available(best.estimator, stage_dir)
    if importance_table is not None:
        tables["feature_importance"] = importance_table
    if importance_plot is not None:
        plots["best_feature_importance"] = importance_plot
    return destination, tables, plots


def _best_prediction_plots(frame: pd.DataFrame, stage_dir: Path) -> dict[str, Path]:
    if "target" in frame.columns and frame["target"].nunique() > 1:
        return {}
    scatter = write_prediction_vs_actual_plot(
        frame["actual"],
        frame["prediction"],
        stage_dir / "best_prediction_vs_actual.png",
        title="Best prediction vs actual",
    )
    residual = write_residual_histogram(
        frame["actual"],
        frame["prediction"],
        stage_dir / "best_residual_histogram.png",
        title="Best residual histogram",
    )
    residual_vs_predicted = write_residual_vs_predicted_plot(
        frame["actual"],
        frame["prediction"],
        stage_dir / "best_residual_vs_predicted.png",
        title="Best residuals vs predicted",
    )
    return {
        "best_prediction_vs_actual": scatter,
        "best_residual_histogram": residual,
        "best_residual_vs_predicted": residual_vs_predicted,
    }
