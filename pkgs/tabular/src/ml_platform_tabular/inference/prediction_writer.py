from __future__ import annotations

from pathlib import Path
from ml_platform_core.io import write_table

from .prediction_frame import _prediction_frame


def _prediction_input(df, features: list[str], estimator):
    columns = list(features)
    target_column = getattr(estimator, "target_column", None)
    if target_column is None:
        estimators = getattr(estimator, "estimators", None)
        if estimators:
            target_column = getattr(estimators[0], "target_column", None)
    if isinstance(target_column, str) and target_column in df.columns and target_column not in columns:
        columns.append(target_column)
    return df[columns]


def write_predictions(
    path: Path,
    df,
    estimator,
    features: list[str],
    *,
    id_columns: list[str],
    coordinate_columns: list[str],
) -> Path:
    y_pred = estimator.predict(_prediction_input(df, features, estimator))
    prediction_frame = _prediction_frame(
        df,
        y_pred,
        id_columns=id_columns,
        coordinate_columns=coordinate_columns,
    )
    return write_table(prediction_frame, path)
