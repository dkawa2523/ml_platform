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
    numeric = pd.to_numeric(frame["prediction"], errors="coerce").dropna()
    quantiles = numeric.quantile([0.25, 0.5, 0.75])
    summary_rows = [
        ("prediction_rows", int(len(frame))),
        ("prediction_mean", float(numeric.mean()) if len(numeric) else 0.0),
        ("prediction_std", float(numeric.std(ddof=0)) if len(numeric) else 0.0),
        ("prediction_min", float(numeric.min()) if len(numeric) else 0.0),
        ("prediction_p25", float(quantiles.loc[0.25]) if len(numeric) else 0.0),
        ("prediction_median", float(quantiles.loc[0.5]) if len(numeric) else 0.0),
        ("prediction_p75", float(quantiles.loc[0.75]) if len(numeric) else 0.0),
        ("prediction_max", float(numeric.max()) if len(numeric) else 0.0),
    ]
    summary_path = write_table(
        pd.DataFrame([{"metric": key, "value": value} for key, value in summary_rows]),
        output_dir / "prediction_summary.csv",
    )
    preview_path = write_table(frame.head(max(int(preview_rows), 1)), output_dir / "prediction_preview.csv")
    distribution_path = write_histogram_plot(
        numeric,
        output_dir / "prediction_distribution_histogram.png",
        title="Prediction distribution",
        x_label="prediction",
    )

    plots = {"prediction_distribution_histogram": distribution_path}
    actual_column = None
    for candidate in ("actual", target_column):
        if candidate and candidate in frame.columns:
            actual_column = candidate
            break
    if actual_column:
        actual = pd.to_numeric(frame[actual_column], errors="coerce")
        prediction = pd.to_numeric(frame["prediction"], errors="coerce")
        valid = actual.notna() & prediction.notna()
        if valid.any():
            plots.update(
                {
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
            )
    return {"prediction_summary": summary_path, "prediction_preview": preview_path}, plots
