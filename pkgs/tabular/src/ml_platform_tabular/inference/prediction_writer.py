from __future__ import annotations

from pathlib import Path
from typing import Any

from ml_platform_core.io import write_table

from .prediction_frame import _prediction_frame


def _chunk_size(cfg: dict[str, Any]) -> int | None:
    value = cfg.get("output", {}).get("chunk_size")
    if value in {None, ""}:
        return None
    chunk_size = int(value)
    if chunk_size < 1:
        raise ValueError("output.chunk_size must be >= 1 when set.")
    return chunk_size


def _write_chunked_predictions(
    path: Path,
    df,
    estimator,
    features: list[str],
    chunk_size: int,
    *,
    id_columns: list[str],
    model_info: dict[str, Any],
    run_id: str,
    model_artifact_id: str,
) -> Path:
    if path.suffix.lower() != ".csv":
        raise ValueError("output.chunk_size currently supports CSV prediction output only.")
    path.parent.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(df), chunk_size):
        chunk = df.iloc[start : start + chunk_size]
        y_pred = estimator.predict(chunk[features])
        frame = _prediction_frame(
            chunk,
            y_pred,
            id_columns=id_columns,
            model_info=model_info,
            run_id=run_id,
            model_artifact_id=model_artifact_id,
        )
        frame.to_csv(path, index=False, mode="w" if start == 0 else "a", header=start == 0)
    if len(df) == 0:
        frame = _prediction_frame(
            df,
            [],
            id_columns=id_columns,
            model_info=model_info,
            run_id=run_id,
            model_artifact_id=model_artifact_id,
        )
        frame.to_csv(path, index=False)
    return path


def write_predictions(
    path: Path,
    df,
    estimator,
    features: list[str],
    chunk_size: int | None,
    *,
    id_columns: list[str],
    model_info: dict[str, Any],
    run_id: str,
    model_artifact_id: str,
) -> Path:
    if chunk_size:
        return _write_chunked_predictions(
            path,
            df,
            estimator,
            features,
            chunk_size,
            id_columns=id_columns,
            model_info=model_info,
            run_id=run_id,
            model_artifact_id=model_artifact_id,
        )
    y_pred = estimator.predict(df[features])
    prediction_frame = _prediction_frame(
        df,
        y_pred,
        id_columns=id_columns,
        model_info=model_info,
        run_id=run_id,
        model_artifact_id=model_artifact_id,
    )
    return write_table(prediction_frame, path)
