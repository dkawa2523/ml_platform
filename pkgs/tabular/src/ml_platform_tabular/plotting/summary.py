from __future__ import annotations

from pathlib import Path

import pandas as pd

from ml_platform_core.io import write_table

from .common import write_histogram_plot


def write_prediction_summary_tables(
    predictions_path: Path,
    output_dir: Path,
    *,
    preview_rows: int = 20,
) -> tuple[dict[str, Path], dict[str, Path]]:
    frame = pd.read_csv(predictions_path)
    if "prediction" not in frame.columns:
        raise ValueError("predictions.csv must contain a prediction column.")
    if "target" in frame.columns and frame["target"].nunique() > 1:
        summary_path = _write_target_prediction_summary(frame, output_dir)
        preview_path = _write_prediction_preview(frame, output_dir=output_dir, preview_rows=preview_rows)
        return {"prediction_summary": summary_path, "prediction_preview": preview_path}, {}
    numeric = _prediction_values(frame)
    summary_path = _write_prediction_summary(numeric, row_count=len(frame), output_dir=output_dir)
    preview_path = _write_prediction_preview(frame, output_dir=output_dir, preview_rows=preview_rows)
    distribution_path = write_histogram_plot(
        numeric,
        output_dir / "prediction_distribution.png",
        title="Prediction distribution",
        x_label="prediction",
    )

    return {
        "prediction_summary": summary_path,
        "prediction_preview": preview_path,
    }, {"prediction_distribution": distribution_path}


def _write_target_prediction_summary(frame: pd.DataFrame, output_dir: Path) -> Path:
    rows = []
    for target, target_frame in frame.groupby("target", sort=False):
        numeric = _prediction_values(target_frame)
        rows.extend(
            {"target": target, "metric": metric, "value": value}
            for metric, value in _summary_rows(numeric, len(target_frame))
        )
    return write_table(pd.DataFrame(rows), output_dir / "prediction_summary.csv")


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
