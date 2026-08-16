"""Read and combine predictions made on the shared selection holdout."""

from __future__ import annotations

import numpy as np
import pandas as pd
from ml_platform_core.io import read_table

from ..metrics import regression_prediction_frame
from .artifacts import CandidateResult

DERIVED_COLUMNS = {"actual", "prediction", "residual", "abs_error", "model_name"}


def ensemble_selection_predictions(selected: list[CandidateResult], method: str, weights: list[float]) -> pd.DataFrame:
    frames = [read_table(item.tables["selection_predictions"]) for item in selected]
    reference = frames[0]
    _validate_shared_holdout(reference, frames[1:])
    matrix = np.column_stack([frame["prediction"].to_numpy(dtype=float) for frame in frames])
    if method == "median":
        prediction = np.median(matrix, axis=1)
    else:
        prediction = np.average(matrix, axis=1, weights=np.asarray(weights, dtype=float))
    base = reference.drop(columns=list(DERIVED_COLUMNS), errors="ignore")
    return regression_prediction_frame(base, reference["actual"], prediction, model_name=method)


def _validate_shared_holdout(reference: pd.DataFrame, others: list[pd.DataFrame]) -> None:
    context = [column for column in ("source_row", "target", "actual") if column in reference]
    if "actual" not in context:
        raise ValueError("Selection predictions must include actual values.")
    for frame in others:
        if context != [column for column in context if column in frame] or not reference[context].equals(
            frame[context]
        ):
            raise ValueError("Candidate selection predictions must describe the same rows in the same order.")
