from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class FeatureTransformer:
    """Small tabular feature transformer for the MVP.

    The default MVP path avoids scikit-learn so local smoke runs stay light. Optional
    sklearn-based models can still be added in models.py without changing ClearML boundaries.
    """

    preset: str = "basic"
    numeric_cols: list[str] = field(default_factory=list)
    categorical_cols: list[str] = field(default_factory=list)
    numeric_medians: dict[str, float] = field(default_factory=dict)
    numeric_means: dict[str, float] = field(default_factory=dict)
    numeric_stds: dict[str, float] = field(default_factory=dict)
    category_levels: dict[str, list[str]] = field(default_factory=dict)

    def fit(self, X: pd.DataFrame) -> "FeatureTransformer":
        if self.preset not in {"basic", "numeric_only"}:
            raise ValueError(f"Unknown feature preset: {self.preset}. Available: basic, numeric_only")

        self.numeric_cols = [c for c in X.columns if pd.api.types.is_numeric_dtype(X[c])]
        self.categorical_cols = [] if self.preset == "numeric_only" else [c for c in X.columns if c not in self.numeric_cols]
        if not self.numeric_cols and not self.categorical_cols:
            raise ValueError("No usable feature columns were found.")

        for col in self.numeric_cols:
            values = pd.to_numeric(X[col], errors="coerce")
            median = float(values.median()) if not values.dropna().empty else 0.0
            filled = values.fillna(median).astype(float)
            mean = float(filled.mean())
            std = float(filled.std(ddof=0)) or 1.0
            self.numeric_medians[col] = median
            self.numeric_means[col] = mean
            self.numeric_stds[col] = std

        for col in self.categorical_cols:
            values = X[col].fillna("__missing__").astype(str)
            self.category_levels[col] = sorted(values.unique().tolist())
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        arrays: list[np.ndarray] = []
        for col in self.numeric_cols:
            if col not in X.columns:
                raise ValueError(f"Required numeric feature is missing: {col}")
            values = pd.to_numeric(X[col], errors="coerce").fillna(self.numeric_medians[col]).astype(float)
            scaled = (values.to_numpy() - self.numeric_means[col]) / self.numeric_stds[col]
            arrays.append(scaled.reshape(-1, 1))

        for col in self.categorical_cols:
            if col not in X.columns:
                raise ValueError(f"Required categorical feature is missing: {col}")
            values = X[col].fillna("__missing__").astype(str)
            levels = self.category_levels[col]
            encoded = np.zeros((len(X), len(levels)), dtype=float)
            index = {level: i for i, level in enumerate(levels)}
            for row_i, value in enumerate(values):
                level_i = index.get(value)
                if level_i is not None:
                    encoded[row_i, level_i] = 1.0
            arrays.append(encoded)

        if not arrays:
            raise ValueError("No feature arrays were produced.")
        return np.hstack(arrays)


def build_feature_pipeline(name: str, X: pd.DataFrame, params: dict[str, Any] | None = None) -> FeatureTransformer:
    params = params or {}
    transformer = FeatureTransformer(preset=name, **params)
    return transformer.fit(X)
