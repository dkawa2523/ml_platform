from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .feature_config import normalize_feature_config


def _numeric_feature_columns(X: pd.DataFrame, excluded: set[str]) -> list[str]:
    return [col for col in X.columns if col not in excluded and pd.api.types.is_numeric_dtype(X[col])]


@dataclass
class FeatureTransformer:
    """Small tabular feature transformer for the MVP.

    Feature handling stays intentionally small so model additions in models.py do not
    change the ClearML boundary.
    """

    preset: str = "basic"
    numeric_impute_strategy: str = "median"
    categorical_impute_strategy: str = "missing_token"
    categorical_encoder: str = "onehot"
    scaling: str = "standard"
    drop_columns: list[str] = field(default_factory=list)
    passthrough_columns: list[str] = field(default_factory=list)
    max_dense_cells: int = 25_000_000
    feature_config: dict[str, Any] = field(default_factory=dict)
    numeric_cols: list[str] = field(default_factory=list)
    categorical_cols: list[str] = field(default_factory=list)
    passthrough_cols: list[str] = field(default_factory=list)
    numeric_fill_values: dict[str, float] = field(default_factory=dict)
    numeric_medians: dict[str, float] = field(default_factory=dict)
    numeric_means: dict[str, float] = field(default_factory=dict)
    numeric_stds: dict[str, float] = field(default_factory=dict)
    categorical_fill_values: dict[str, str] = field(default_factory=dict)
    category_levels: dict[str, list[str]] = field(default_factory=dict)

    def fit(self, X: pd.DataFrame) -> FeatureTransformer:
        config = normalize_feature_config(self._raw_config())
        self._apply_config(config)
        X_work = self._fit_input_frame(X)
        self._fit_column_roles(X_work)
        self._fit_numeric_features(X_work)
        self._fit_categorical_features(X_work)
        return self

    def _raw_config(self) -> dict[str, Any]:
        return {
            "preset": self.preset,
            "numeric_impute_strategy": self.numeric_impute_strategy,
            "categorical_impute_strategy": self.categorical_impute_strategy,
            "categorical_encoder": self.categorical_encoder,
            "scaling": self.scaling,
            "drop_columns": self.drop_columns,
            "passthrough_columns": self.passthrough_columns,
            "max_dense_cells": self.max_dense_cells,
            "params": self.feature_config.get("params", {}),
        }

    def _apply_config(self, config: dict[str, Any]) -> None:
        self.preset = config["preset"]
        self.numeric_impute_strategy = config["numeric_impute_strategy"]
        self.categorical_impute_strategy = config["categorical_impute_strategy"]
        self.categorical_encoder = config["categorical_encoder"]
        self.scaling = config["scaling"]
        self.drop_columns = list(config["drop_columns"])
        self.passthrough_columns = list(config["passthrough_columns"])
        self.max_dense_cells = int(config["max_dense_cells"])
        self.feature_config = dict(config)

    def _fit_input_frame(self, X: pd.DataFrame) -> pd.DataFrame:
        self._validate_passthrough_columns(X)
        X_work = X.drop(columns=self.drop_columns, errors="ignore")
        self._validate_numeric_passthrough(X_work)
        return X_work

    def _validate_passthrough_columns(self, X: pd.DataFrame) -> None:
        missing_passthrough = [col for col in self.passthrough_columns if col not in X.columns]
        if missing_passthrough:
            raise ValueError(f"features.passthrough_columns not found: {missing_passthrough}")
        overlap = sorted(set(self.drop_columns) & set(self.passthrough_columns))
        if overlap:
            raise ValueError(f"features.drop_columns cannot overlap passthrough_columns: {overlap}")

    def _validate_numeric_passthrough(self, X_work: pd.DataFrame) -> None:
        non_numeric_passthrough = [
            col for col in self.passthrough_columns if not pd.api.types.is_numeric_dtype(X_work[col])
        ]
        if non_numeric_passthrough:
            raise ValueError(f"features.passthrough_columns must be numeric raw columns: {non_numeric_passthrough}")

    def _fit_column_roles(self, X_work: pd.DataFrame) -> None:
        passthrough_set = set(self.passthrough_columns)
        self.passthrough_cols = list(self.passthrough_columns)
        self.numeric_cols = _numeric_feature_columns(X_work, passthrough_set)
        self.categorical_cols = self._categorical_feature_columns(X_work, passthrough_set)
        self._require_usable_features()

    def _categorical_feature_columns(self, X_work: pd.DataFrame, passthrough_set: set[str]) -> list[str]:
        if self.categorical_encoder == "drop":
            return []
        return [c for c in X_work.columns if c not in passthrough_set and c not in self.numeric_cols]

    def _require_usable_features(self) -> None:
        if not self.numeric_cols and not self.categorical_cols and not self.passthrough_cols:
            raise ValueError("No usable feature columns were found.")

    def _fit_numeric_features(self, X_work: pd.DataFrame) -> None:
        for col in self.numeric_cols:
            values = pd.to_numeric(X_work[col], errors="coerce")
            fill_value = self._numeric_fill_value(values)
            filled = values.fillna(fill_value).astype(float)
            mean = float(filled.mean())
            std = float(filled.std(ddof=0)) or 1.0
            self.numeric_fill_values[col] = fill_value
            self.numeric_medians[col] = fill_value
            self.numeric_means[col] = mean
            self.numeric_stds[col] = std

    def _fit_categorical_features(self, X_work: pd.DataFrame) -> None:
        for col in self.categorical_cols:
            values = X_work[col]
            fill_value = self._categorical_fill_value(values)
            filled = values.fillna(fill_value).astype(str)
            self.categorical_fill_values[col] = fill_value
            self.category_levels[col] = sorted(filled.unique().tolist())

    def _numeric_fill_value(self, values: pd.Series) -> float:
        non_null = values.dropna()
        if non_null.empty or self.numeric_impute_strategy == "zero":
            return 0.0
        if self.numeric_impute_strategy == "mean":
            return float(non_null.mean())
        return float(non_null.median())

    def _categorical_fill_value(self, values: pd.Series) -> str:
        non_null = values.dropna().astype(str)
        if self.categorical_impute_strategy == "mode" and not non_null.empty:
            modes = non_null.mode()
            if not modes.empty:
                return str(modes.iloc[0])
        return "__missing__"

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        self._validate_dense_size(len(X))
        arrays = [
            *self._numeric_arrays(X),
            *self._categorical_arrays(X),
            *self._passthrough_arrays(X),
        ]
        if not arrays:
            raise ValueError("No feature arrays were produced.")
        return np.hstack(arrays)

    def _validate_dense_size(self, row_count: int) -> None:
        width = (
            len(self.numeric_cols)
            + len(self.passthrough_cols)
            + sum(len(levels) for levels in self.category_levels.values())
        )
        cells = row_count * width
        if cells > self.max_dense_cells:
            raise ValueError(
                "Dense feature matrix exceeds features.max_dense_cells "
                f"(rows={row_count}, columns={width}, cells={cells}, limit={self.max_dense_cells}). "
                "Use the numeric_only preset, drop high-cardinality columns, or raise the limit deliberately."
            )

    def _numeric_arrays(self, X: pd.DataFrame) -> list[np.ndarray]:
        arrays: list[np.ndarray] = []
        for col in self.numeric_cols:
            if col not in X.columns:
                raise ValueError(f"Required numeric feature is missing: {col}")
            fill_value = self.numeric_fill_values.get(col, self.numeric_medians[col])
            values = pd.to_numeric(X[col], errors="coerce").fillna(fill_value)
            array = values.to_numpy(dtype=np.float32)
            if self.scaling == "standard":
                array = (array - self.numeric_means[col]) / self.numeric_stds[col]
            arrays.append(array.astype(np.float32, copy=False).reshape(-1, 1))
        return arrays

    def _categorical_arrays(self, X: pd.DataFrame) -> list[np.ndarray]:
        arrays: list[np.ndarray] = []
        for col in self.categorical_cols:
            if col not in X.columns:
                raise ValueError(f"Required categorical feature is missing: {col}")
            values = X[col].fillna(self.categorical_fill_values[col]).astype(str)
            levels = self.category_levels[col]
            encoded = np.zeros((len(X), len(levels)), dtype=np.float32)
            index = {level: i for i, level in enumerate(levels)}
            for row_i, value in enumerate(values):
                level_i = index.get(value)
                if level_i is not None:
                    encoded[row_i, level_i] = 1.0
            arrays.append(encoded)
        return arrays

    def _passthrough_arrays(self, X: pd.DataFrame) -> list[np.ndarray]:
        arrays: list[np.ndarray] = []
        for col in self.passthrough_cols:
            if col not in X.columns:
                raise ValueError(f"Required passthrough feature is missing: {col}")
            values = pd.to_numeric(X[col], errors="coerce")
            if values.isna().any():
                raise ValueError(f"Passthrough feature contains missing or non-numeric values: {col}")
            arrays.append(values.to_numpy(dtype=np.float32).reshape(-1, 1))
        return arrays


def build_feature_pipeline(name: str, X: pd.DataFrame, params: dict[str, Any] | None = None) -> FeatureTransformer:
    config = normalize_feature_config({"preset": name, **(params or {})})
    transformer = FeatureTransformer(
        preset=config["preset"],
        numeric_impute_strategy=config["numeric_impute_strategy"],
        categorical_impute_strategy=config["categorical_impute_strategy"],
        categorical_encoder=config["categorical_encoder"],
        scaling=config["scaling"],
        drop_columns=list(config["drop_columns"]),
        passthrough_columns=list(config["passthrough_columns"]),
        max_dense_cells=int(config["max_dense_cells"]),
        feature_config=config,
    )
    return transformer.fit(X)
