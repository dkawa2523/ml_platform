from __future__ import annotations

from pathlib import Path

import pandas as pd
from ml_platform_core.io import write_table

from ..plotting import (
    write_feature_importance_plot_if_available,
    write_prediction_vs_actual_plot,
    write_residual_histogram,
    write_residual_vs_predicted_plot,
)
from .artifacts import CandidateResult

PREDICTION_COLUMNS = {"actual", "prediction"}


def write_evaluation_diagnostics(
    best: CandidateResult,
    frame: pd.DataFrame,
    stage_dir: Path,
) -> tuple[Path | None, dict[str, Path], dict[str, Path]]:
    destination = stage_dir / "evaluation_predictions.csv"
    if not set(frame.columns) >= PREDICTION_COLUMNS:
        raise ValueError("Evaluation predictions must contain actual and prediction columns.")
    write_table(frame, destination)
    tables: dict[str, Path] = {}
    plots = _best_prediction_plots(frame, stage_dir)
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
