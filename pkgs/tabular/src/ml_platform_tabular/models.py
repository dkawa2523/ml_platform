from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

AVAILABLE_MODELS = ["linear", "ridge", "random_forest", "gradient_boosting"]


@dataclass
class LinearRegressor:
    coef_: np.ndarray | None = None

    def fit(self, X: np.ndarray, y) -> "LinearRegressor":
        y_arr = np.asarray(y, dtype=float)
        design = np.c_[np.ones(X.shape[0]), X]
        self.coef_ = np.linalg.pinv(design) @ y_arr
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.coef_ is None:
            raise ValueError("Model is not fitted.")
        design = np.c_[np.ones(X.shape[0]), X]
        return design @ self.coef_


@dataclass
class RidgeRegressor:
    alpha: float = 1.0
    coef_: np.ndarray | None = None

    def fit(self, X: np.ndarray, y) -> "RidgeRegressor":
        y_arr = np.asarray(y, dtype=float)
        design = np.c_[np.ones(X.shape[0]), X]
        penalty = np.eye(design.shape[1]) * float(self.alpha)
        penalty[0, 0] = 0.0
        self.coef_ = np.linalg.pinv(design.T @ design + penalty) @ design.T @ y_arr
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.coef_ is None:
            raise ValueError("Model is not fitted.")
        design = np.c_[np.ones(X.shape[0]), X]
        return design @ self.coef_


@dataclass
class TabularEstimator:
    transformer: Any
    model: Any
    feature_columns: list[str]

    def fit(self, X: pd.DataFrame, y) -> "TabularEstimator":
        self.model.fit(self.transformer.transform(X), y)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict(self.transformer.transform(X))


def build_model(name: str, params: dict[str, Any] | None = None):
    params = dict(params or {})
    if name == "linear":
        return LinearRegressor()
    if name == "ridge":
        return RidgeRegressor(**params)
    if name == "random_forest":
        try:
            from sklearn.ensemble import RandomForestRegressor  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("random_forest requires optional dependency: pip install scikit-learn") from exc
        params.setdefault("n_jobs", 1)
        return RandomForestRegressor(**params)
    if name == "gradient_boosting":
        try:
            from sklearn.ensemble import GradientBoostingRegressor  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("gradient_boosting requires optional dependency: pip install scikit-learn") from exc
        return GradientBoostingRegressor(**params)
    raise ValueError(f"Unknown model name: {name}. Available: {', '.join(AVAILABLE_MODELS)}")
