from __future__ import annotations

from pathlib import Path

import pandas as pd

from ml_platform_core.io import write_table

from .common import write_histogram_plot
from .prediction import (
    write_prediction_vs_actual_plot,
    write_residual_histogram,
    write_residual_vs_predicted_plot,
)


def write_prediction_summary_tables(
    predictions_path: Path,
    output_dir: Path,
    *,
    target_column: str | None = None,
    preview_rows: int = 20,
) -> tuple[dict[str, Path], dict[str, Path]]:
    frame = pd.read_csv(predictions_path)
    if "prediction" not in frame.columns:
        raise ValueError("predictions.csv must contain a prediction column.")
    numeric = _prediction_values(frame)
    summary_path = _write_prediction_summary(numeric, row_count=len(frame), output_dir=output_dir)
    preview_path = _write_prediction_preview(frame, output_dir=output_dir, preview_rows=preview_rows)
    distribution_path = write_histogram_plot(
        numeric,
        output_dir / "prediction_distribution_histogram.png",
        title="Prediction distribution",
        x_label="prediction",
    )

    plots = {"prediction_distribution_histogram": distribution_path}
    plots.update(_actual_prediction_plots(frame, output_dir=output_dir, target_column=target_column))
    return {"prediction_summary": summary_path, "prediction_preview": preview_path}, plots


def _prediction_values(frame: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(frame["prediction"], errors="coerce").dropna()


def _write_prediction_summary(numeric: pd.Series, *, row_count: int, output_dir: Path) -> Path:
    return write_table(
        pd.DataFrame([{"metric": key, "value": value} for key, value in _summary_rows(numeric, row_count)]),
        output_dir / "prediction_summary.csv",
    )


def _summary_rows(numeric: pd.Series, row_count: int) -> list[tuple[str, float | int]]:
    quantiles = numeric.quantile([0.25, 0.5, 0.75])
    has_values = len(numeric) > 0
    return [
        ("prediction_rows", int(row_count)),
        ("prediction_mean", float(numeric.mean()) if has_values else 0.0),
        ("prediction_std", float(numeric.std(ddof=0)) if has_values else 0.0),
        ("prediction_min", float(numeric.min()) if has_values else 0.0),
        ("prediction_p25", float(quantiles.loc[0.25]) if has_values else 0.0),
        ("prediction_median", float(quantiles.loc[0.5]) if has_values else 0.0),
        ("prediction_p75", float(quantiles.loc[0.75]) if has_values else 0.0),
        ("prediction_max", float(numeric.max()) if has_values else 0.0),
    ]


def _write_prediction_preview(frame: pd.DataFrame, *, output_dir: Path, preview_rows: int) -> Path:
    return write_table(frame.head(max(int(preview_rows), 1)), output_dir / "prediction_preview.csv")


def _actual_prediction_plots(
    frame: pd.DataFrame,
    *,
    output_dir: Path,
    target_column: str | None,
) -> dict[str, Path]:
    actual_column = _actual_column(frame, target_column)
    if not actual_column:
        return {}
    actual = pd.to_numeric(frame[actual_column], errors="coerce")
    prediction = pd.to_numeric(frame["prediction"], errors="coerce")
    valid = actual.notna() & prediction.notna()
    if not valid.any():
        return {}
    return {
        "prediction_vs_actual": write_prediction_vs_actual_plot(
            actual[valid],
            prediction[valid],
            output_dir / "prediction_vs_actual.png",
        ),
        "residual_histogram": write_residual_histogram(
            actual[valid],
            prediction[valid],
            output_dir / "residual_histogram.png",
        ),
        "residual_vs_predicted": write_residual_vs_predicted_plot(
            actual[valid],
            prediction[valid],
            output_dir / "residual_vs_predicted.png",
        ),
    }


def _actual_column(frame: pd.DataFrame, target_column: str | None) -> str | None:
    for candidate in ("actual", target_column):
        if candidate and candidate in frame.columns:
            return candidate
    return None
