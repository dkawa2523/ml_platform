"""Prediction bundle for independently observed tabular targets."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .models import FrameTransformer, Regressor


@dataclass
class TargetModelBundle:
    """Apply one fitted scalar model per target to a logical long frame."""

    transformer: FrameTransformer
    models: Mapping[str, Regressor]
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

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Return one scalar prediction per input row, preserving row order."""
        return _predict_bundle(self, X)


def _predict_bundle(bundle: TargetModelBundle, frame: pd.DataFrame) -> np.ndarray:
    _validate_required_columns(bundle, frame)
    targets = _target_values(bundle, frame)
    _validate_target_values(bundle, targets)
    if frame.empty:
        return np.empty(0, dtype=float)
    predictions = np.empty(len(frame), dtype=float)
    for target, model in bundle.models.items():
        _predict_target(bundle, frame, targets, target, model, predictions)
    return predictions


def _validate_required_columns(bundle: TargetModelBundle, frame: pd.DataFrame) -> None:
    required = list(bundle.feature_columns)
    if len(bundle.models) > 1:
        required.insert(0, bundle.target_column)
    missing = [name for name in required if name not in frame.columns]
    if missing:
        raise ValueError(f"Prediction data is missing required columns: {missing}")


def _target_values(bundle: TargetModelBundle, frame: pd.DataFrame) -> pd.Series:
    return (
        frame[bundle.target_column]
        if bundle.target_column in frame.columns
        else pd.Series(next(iter(bundle.models)), index=frame.index)
    )


def _validate_target_values(bundle: TargetModelBundle, targets: pd.Series) -> None:
    if targets.isna().any():
        raise ValueError(f"Prediction data contains missing values in target column {bundle.target_column!r}.")
    unknown = set(targets.unique()) - bundle.models.keys()
    if unknown:
        unknown_names = ", ".join(sorted(repr(value) for value in unknown))
        available = ", ".join(sorted(bundle.models))
        raise ValueError(f"Unknown target values: {unknown_names}. Available targets: {available}")


def _predict_target(
    bundle: TargetModelBundle,
    frame: pd.DataFrame,
    targets: pd.Series,
    target: str,
    model: Regressor,
    predictions: np.ndarray,
) -> None:
    positions = np.flatnonzero(targets.eq(target).to_numpy())
    if not positions.size:
        return
    features = frame.iloc[positions][bundle.feature_columns]
    target_predictions = np.asarray(model.predict(bundle.transformer.transform(features)))
    expected_shape = (len(positions),)
    if target_predictions.shape != expected_shape:
        raise ValueError(
            f"Model for target {target!r} returned predictions with shape "
            f"{target_predictions.shape}; expected {expected_shape}."
        )
    predictions[positions] = target_predictions
