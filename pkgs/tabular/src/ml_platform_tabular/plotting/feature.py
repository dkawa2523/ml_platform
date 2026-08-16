from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from ml_platform_core.io import write_table

from .common import write_metrics_bar_plot


def transformed_columns_from_transformer(transformer: Any) -> list[str]:
    columns = list(getattr(transformer, "numeric_cols", []))
    for col in getattr(transformer, "categorical_cols", []):
        for level in getattr(transformer, "category_levels", {}).get(col, []):
            columns.append(f"{col}={level}")
    columns.extend(list(getattr(transformer, "passthrough_cols", [])))
    return columns


def feature_role(column: str, transformer: Any, feature_config: dict[str, Any]) -> str:
    if column in set(feature_config.get("drop_columns") or []):
        return "dropped"
    if column in set(getattr(transformer, "passthrough_cols", [])):
        return "passthrough"
    if column in set(getattr(transformer, "numeric_cols", [])):
        return "numeric"
    if column in set(getattr(transformer, "categorical_cols", [])):
        return "categorical"
    return "categorical_dropped" if feature_config.get("categorical_encoder") == "drop" else "selected"


def write_feature_diagnostics(
    *,
    df: pd.DataFrame,
    X: pd.DataFrame,
    feature_columns: list[str],
    transformer: Any,
    feature_config: dict[str, Any],
    output_dir: Path,
) -> tuple[dict[str, Path], dict[str, Path]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    missing_rows: list[dict[str, Any]] = []
    visible_columns = list(feature_columns)
    for column in feature_config["drop_columns"]:
        if column in df.columns and column not in visible_columns:
            visible_columns.append(column)
    for column in visible_columns:
        source = df[column] if column in df.columns else X[column]
        missing_count = int(source.isna().sum())
        missing_rows.append(
            {
                "column": column,
                "role": feature_role(column, transformer, feature_config),
                "dtype": str(source.dtype),
                "missing_count": missing_count,
                "missing_rate": float(missing_count / len(source)) if len(source) else 0.0,
            }
        )
    missing_path = write_table(pd.DataFrame(missing_rows), output_dir / "missing_rate_by_column.csv")
    missingness_plot = write_metrics_bar_plot(
        [(row["column"], row["missing_rate"]) for row in missing_rows],
        output_dir / "missing_rate_by_column_bar.png",
        title="Feature missing rate",
        value_label="missing_rate",
    )
    return {"missing_rate_by_column": missing_path}, {"missing_rate_by_column_bar": missingness_plot}


def _feature_importance_frame(estimator: Any) -> pd.DataFrame | None:
    transformer = getattr(estimator, "transformer", None)
    model = getattr(estimator, "model", None)
    if transformer is None or model is None:
        return None
    columns = transformed_columns_from_transformer(transformer)
    raw_values = None
    source = None
    if hasattr(model, "feature_importances_"):
        raw_values = np.asarray(model.feature_importances_, dtype=float).reshape(-1)
        source = "feature_importances_"
    elif hasattr(model, "coef_"):
        raw_values = np.asarray(model.coef_, dtype=float).reshape(-1)
        if raw_values.shape[0] == len(columns) + 1:
            raw_values = raw_values[1:]
        source = "coef_"
    if raw_values is None or raw_values.shape[0] != len(columns):
        return None
    frame = pd.DataFrame(
        {
            "feature": columns,
            "importance": np.abs(raw_values),
            "raw_value": raw_values,
            "source": source,
        }
    )
    frame = frame.sort_values("importance", ascending=False).reset_index(drop=True)
    frame.insert(0, "rank", range(1, len(frame) + 1))
    return frame


def write_feature_importance_plot_if_available(estimator: Any, output_dir: Path) -> tuple[Path | None, Path | None]:
    frame = _feature_importance_frame(estimator)
    if frame is None or frame.empty:
        return None, None
    table_path = write_table(frame, output_dir / "feature_importance.csv")
    plot_path = write_metrics_bar_plot(
        [(str(row.feature), _as_float(row.importance)) for row in frame.itertuples(index=False)],
        output_dir / "feature_importance.png",
        title="Feature importance",
        value_label="importance",
    )
    return table_path, plot_path


def _as_float(value: Any) -> float:
    return float(value)
