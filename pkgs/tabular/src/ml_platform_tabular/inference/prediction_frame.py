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


def _model_artifact_id(model_path: Path) -> str:
    return file_hash(model_path)[:16]


def _prediction_frame(
    df,
    y_pred,
    *,
    id_columns: list[str],
    coordinate_columns: list[str],
):
    conflicts = [column for column in RESERVED_PREDICTION_COLUMNS if column in df.columns]
    if conflicts:
        raise ValueError(f"Input table contains reserved prediction output columns: {conflicts}")
    out = pd.DataFrame({"row_index": df.index.to_list()})
    if TARGET_COLUMN in df.columns:
        out["target"] = df[TARGET_COLUMN].to_list()
        for column in coordinate_columns:
            if column in df.columns and column not in out.columns:
                out[column] = df[column].to_list()
        if SOURCE_ROW_COLUMN in df.columns:
            out["source_row"] = df[SOURCE_ROW_COLUMN].to_list()
    for column in id_columns:
        if column in df.columns and column not in out.columns:
            out[column] = df[column].to_list()
    out["prediction"] = y_pred
    return out
