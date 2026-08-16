from __future__ import annotations

from pathlib import Path

import pandas as pd
from ml_platform_core.artifacts import file_hash

from ..target_sources import SOURCE_ROW_COLUMN, TARGET_COLUMN

PREDICTION_SCHEMA_VERSION = "v3"
RESERVED_PREDICTION_COLUMNS = {
    "row_index",
    "target",
    "source_row",
    "prediction",
}


def model_artifact_id(model_path: Path) -> str:
    return file_hash(model_path)[:16]


def build_prediction_frame(
    df: pd.DataFrame,
    y_pred,
    *,
    id_columns: list[str],
    coordinate_columns: list[str],
) -> pd.DataFrame:
    conflicts = [column for column in RESERVED_PREDICTION_COLUMNS if column in df.columns]
    if conflicts:
        raise ValueError(f"Input table contains reserved prediction output columns: {conflicts}")

    out = pd.DataFrame({"row_index": df.index.to_list()})
    _add_target_context(out, df, coordinate_columns)
    _copy_columns(out, df, id_columns)
    out["prediction"] = y_pred
    return out


def _add_target_context(out: pd.DataFrame, source: pd.DataFrame, coordinate_columns: list[str]) -> None:
    if TARGET_COLUMN not in source.columns:
        return
    out["target"] = source[TARGET_COLUMN].to_list()
    _copy_columns(out, source, coordinate_columns)
    if SOURCE_ROW_COLUMN in source.columns:
        out["source_row"] = source[SOURCE_ROW_COLUMN].to_list()


def _copy_columns(out: pd.DataFrame, source: pd.DataFrame, columns: list[str]) -> None:
    for column in columns:
        if column in source.columns and column not in out.columns:
            out[column] = source[column].to_list()
