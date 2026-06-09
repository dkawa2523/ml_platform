from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

PRESET_DEFAULTS: dict[str, dict[str, Any]] = {
    "basic": {
        "numeric_impute_strategy": "median",
        "categorical_impute_strategy": "missing_token",
        "categorical_encoder": "onehot",
        "scaling": "standard",
    },
    "numeric_only": {
        "numeric_impute_strategy": "median",
        "categorical_impute_strategy": "missing_token",
        "categorical_encoder": "drop",
        "scaling": "standard",
    },
}
FEATURE_CONFIG_KEYS = {
    "numeric_impute_strategy",
    "categorical_impute_strategy",
    "categorical_encoder",
    "scaling",
    "drop_columns",
    "passthrough_columns",
}
NUMERIC_IMPUTE_STRATEGIES = {"median", "mean", "zero"}
CATEGORICAL_IMPUTE_STRATEGIES = {"missing_token", "mode"}
CATEGORICAL_ENCODERS = {"onehot", "drop"}
SCALING_OPTIONS = {"standard", "none"}


def _normalize_columns(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value]
    raise ValueError(f"Column list must be null, string, or list: {value!r}")


def _validate_choice(name: str, value: str, choices: set[str]) -> str:
    text = str(value or "").strip()
    if text not in choices:
        raise ValueError(f"features.{name} must be one of {sorted(choices)}, got: {value!r}")
    return text


def normalize_feature_config(feature_cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve preset defaults and explicit feature settings into one small config."""
    raw = dict(feature_cfg or {})
    params = raw.get("params") or {}
    if not isinstance(params, dict):
        raise ValueError("features.params must be a mapping when provided.")

    preset = str(raw.get("preset") or params.get("preset") or "basic").strip()
    if preset not in PRESET_DEFAULTS:
        raise ValueError(f"Unknown feature preset: {preset}. Available: {', '.join(PRESET_DEFAULTS)}")

    resolved: dict[str, Any] = {
        "preset": preset,
        **PRESET_DEFAULTS[preset],
        "drop_columns": [],
        "passthrough_columns": [],
        "params": dict(params),
    }
    for key in FEATURE_CONFIG_KEYS:
        if key in params:
            resolved[key] = params[key]
    for key in FEATURE_CONFIG_KEYS:
        if key in raw and raw[key] is not None:
            resolved[key] = raw[key]

    resolved["numeric_impute_strategy"] = _validate_choice(
        "numeric_impute_strategy", resolved["numeric_impute_strategy"], NUMERIC_IMPUTE_STRATEGIES
    )
    resolved["categorical_impute_strategy"] = _validate_choice(
        "categorical_impute_strategy", resolved["categorical_impute_strategy"], CATEGORICAL_IMPUTE_STRATEGIES
    )
    resolved["categorical_encoder"] = _validate_choice("categorical_encoder", resolved["categorical_encoder"], CATEGORICAL_ENCODERS)
    resolved["scaling"] = _validate_choice("scaling", resolved["scaling"], SCALING_OPTIONS)
    resolved["drop_columns"] = _normalize_columns(resolved.get("drop_columns"))
    resolved["passthrough_columns"] = _normalize_columns(resolved.get("passthrough_columns"))
    return resolved


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

    def fit(self, X: pd.DataFrame) -> "FeatureTransformer":
        config = normalize_feature_config(
            {
                "preset": self.preset,
                "numeric_impute_strategy": self.numeric_impute_strategy,
                "categorical_impute_strategy": self.categorical_impute_strategy,
                "categorical_encoder": self.categorical_encoder,
                "scaling": self.scaling,
                "drop_columns": self.drop_columns,
                "passthrough_columns": self.passthrough_columns,
                "params": self.feature_config.get("params", {}),
            }
        )
        self.preset = config["preset"]
        self.numeric_impute_strategy = config["numeric_impute_strategy"]
        self.categorical_impute_strategy = config["categorical_impute_strategy"]
        self.categorical_encoder = config["categorical_encoder"]
        self.scaling = config["scaling"]
        self.drop_columns = list(config["drop_columns"])
        self.passthrough_columns = list(config["passthrough_columns"])
        self.feature_config = dict(config)

        missing_passthrough = [col for col in self.passthrough_columns if col not in X.columns]
        if missing_passthrough:
            raise ValueError(f"features.passthrough_columns not found: {missing_passthrough}")
        overlap = sorted(set(self.drop_columns) & set(self.passthrough_columns))
        if overlap:
            raise ValueError(f"features.drop_columns cannot overlap passthrough_columns: {overlap}")

        X_work = X.drop(columns=self.drop_columns, errors="ignore")
        passthrough = list(self.passthrough_columns)
        non_numeric_passthrough = [col for col in passthrough if not pd.api.types.is_numeric_dtype(X_work[col])]
        if non_numeric_passthrough:
            raise ValueError(f"features.passthrough_columns must be numeric raw columns: {non_numeric_passthrough}")

        passthrough_set = set(passthrough)
        self.passthrough_cols = passthrough
        self.numeric_cols = [c for c in X_work.columns if c not in passthrough_set and pd.api.types.is_numeric_dtype(X_work[c])]
        categorical_candidates = [c for c in X_work.columns if c not in passthrough_set and c not in self.numeric_cols]
        self.categorical_cols = [] if self.categorical_encoder == "drop" else categorical_candidates
        if not self.numeric_cols and not self.categorical_cols and not self.passthrough_cols:
            raise ValueError("No usable feature columns were found.")

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

        for col in self.categorical_cols:
            values = X_work[col]
            fill_value = self._categorical_fill_value(values)
            filled = values.fillna(fill_value).astype(str)
            self.categorical_fill_values[col] = fill_value
            self.category_levels[col] = sorted(filled.unique().tolist())
        return self

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
        arrays: list[np.ndarray] = []
        for col in self.numeric_cols:
            if col not in X.columns:
                raise ValueError(f"Required numeric feature is missing: {col}")
            fill_value = self.numeric_fill_values.get(col, self.numeric_medians[col])
            values = pd.to_numeric(X[col], errors="coerce").fillna(fill_value).astype(float)
            array = values.to_numpy()
            if self.scaling == "standard":
                array = (array - self.numeric_means[col]) / self.numeric_stds[col]
            arrays.append(array.reshape(-1, 1))

        for col in self.categorical_cols:
            if col not in X.columns:
                raise ValueError(f"Required categorical feature is missing: {col}")
            values = X[col].fillna(self.categorical_fill_values[col]).astype(str)
            levels = self.category_levels[col]
            encoded = np.zeros((len(X), len(levels)), dtype=float)
            index = {level: i for i, level in enumerate(levels)}
            for row_i, value in enumerate(values):
                level_i = index.get(value)
                if level_i is not None:
                    encoded[row_i, level_i] = 1.0
            arrays.append(encoded)

        for col in self.passthrough_cols:
            if col not in X.columns:
                raise ValueError(f"Required passthrough feature is missing: {col}")
            values = pd.to_numeric(X[col], errors="coerce")
            if values.isna().any():
                raise ValueError(f"Passthrough feature contains missing or non-numeric values: {col}")
            arrays.append(values.astype(float).to_numpy().reshape(-1, 1))

        if not arrays:
            raise ValueError("No feature arrays were produced.")
        return np.hstack(arrays)


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
        feature_config=config,
    )
    return transformer.fit(X)
