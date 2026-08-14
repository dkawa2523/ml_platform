"""Prediction bundle for independently observed tabular targets."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .models import FrameTransformer, Regressor


@dataclass
class TargetModelBundle:
    """Apply one fitted scalar model per target to a logical long frame."""

    transformer: FrameTransformer
    models: dict[str, Regressor]
    feature_columns: list[str]
    target_column: str = "__target__"

    def __post_init__(self) -> None:
        if not self.models:
            raise ValueError("Target model bundle requires at least one model.")
        if not self.target_column:
            raise ValueError("target_column must not be empty.")
        if len(self.feature_columns) != len(set(self.feature_columns)):
            raise ValueError("feature_columns must not contain duplicates.")
        if self.target_column in self.feature_columns:
            raise ValueError("target_column must not also be a feature column.")

    @property
    def model(self) -> Regressor | None:
        """Expose the scalar model for legacy feature-importance consumers."""
        if len(self.models) == 1:
            return next(iter(self.models.values()))
        return None

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        """Return one scalar prediction per input row, preserving row order."""
        required = list(self.feature_columns)
        if len(self.models) > 1:
            required.insert(0, self.target_column)
        missing = [name for name in required if name not in frame.columns]
        if missing:
            raise ValueError(f"Prediction data is missing required columns: {missing}")
        targets = (
            frame[self.target_column]
            if self.target_column in frame.columns
            else pd.Series(next(iter(self.models)), index=frame.index)
        )
        if targets.isna().any():
            raise ValueError(f"Prediction data contains missing values in target column {self.target_column!r}.")
        if frame.empty:
            return np.empty(0, dtype=float)

        unknown = set(targets.unique()) - self.models.keys()
        if unknown:
            unknown_names = ", ".join(sorted(repr(value) for value in unknown))
            available = ", ".join(sorted(self.models))
            raise ValueError(f"Unknown target values: {unknown_names}. Available targets: {available}")

        predictions = np.empty(len(frame), dtype=float)
        for target, model in self.models.items():
            positions = np.flatnonzero(targets.eq(target).to_numpy())
            if not positions.size:
                continue
            features = frame.iloc[positions][self.feature_columns]
            target_predictions = np.asarray(model.predict(self.transformer.transform(features)))
            expected_shape = (len(positions),)
            if target_predictions.shape != expected_shape:
                raise ValueError(
                    f"Model for target {target!r} returned predictions with shape "
                    f"{target_predictions.shape}; expected {expected_shape}."
                )
            predictions[positions] = target_predictions
        return predictions
