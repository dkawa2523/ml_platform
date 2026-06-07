from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

AVAILABLE_MODELS = [
    "linear",
    "ridge",
    "random_forest",
    "gradient_boosting",
    "lasso",
    "elasticnet",
    "extra_trees",
    "knn",
    "svr",
    "mlp",
]


def candidate_params(model_params: Any, name: str) -> dict[str, Any]:
    if not model_params:
        return {}
    if not isinstance(model_params, dict):
        raise ValueError("model.params must be a mapping.")
    value = model_params.get(name)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"model.params.{name} must be a mapping.")
    return dict(value)


def model_candidates(model_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    raw_candidates = model_cfg.get("candidates") or []
    model_params = model_cfg.get("params") or {}
    if not raw_candidates:
        if not isinstance(model_params, dict):
            raise ValueError("model.params must be a mapping.")
        return [
            {
                "name": model_cfg.get("name", "ridge"),
                "params": dict(model_params),
            }
        ]
    if not isinstance(raw_candidates, list):
        raise ValueError("model.candidates must be a list of model names or model definitions.")

    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_candidates):
        if isinstance(item, str):
            name = item.strip()
            if not name:
                raise ValueError(f"model.candidates[{index}] must not be empty.")
            params = candidate_params(model_params, name)
        elif isinstance(item, dict):
            name = item.get("name")
            if not name:
                raise ValueError(f"model.candidates[{index}].name is required.")
            name = str(name)
            params = item.get("params")
            if params is None:
                params = candidate_params(model_params, name)
            if not isinstance(params, dict):
                raise ValueError(f"model.candidates[{index}].params must be a mapping.")
            params = dict(params)
        else:
            raise ValueError(f"model.candidates[{index}] must be a model name or mapping.")
        if name in seen:
            raise ValueError(f"model.candidates contains duplicate model name: {name}")
        seen.add(name)
        candidates.append({"name": str(name), "params": dict(params)})
    return candidates


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


@dataclass
class MeanTopKEnsemble:
    estimators: list[TabularEstimator]
    weights: list[float]

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self.estimators:
            raise ValueError("Ensemble has no base estimators.")
        predictions = np.column_stack([estimator.predict(X) for estimator in self.estimators])
        weights = np.asarray(self.weights, dtype=float)
        if len(weights) != predictions.shape[1]:
            raise ValueError("Ensemble weights do not match base estimators.")
        return predictions @ (weights / weights.sum())


def build_model(name: str, params: dict[str, Any] | None = None):
    params = dict(params or {})
    if name == "linear":
        return LinearRegressor()
    if name == "ridge":
        return RidgeRegressor(**params)
    if name == "random_forest":
        try:
            from sklearn.ensemble import RandomForestRegressor  # type: ignore
        except Exception as exc:  # pragma: no cover - dependency install failure
            raise RuntimeError("random_forest requires scikit-learn. Install project runtime dependencies.") from exc
        params.setdefault("n_jobs", 1)
        return RandomForestRegressor(**params)
    if name == "gradient_boosting":
        try:
            from sklearn.ensemble import GradientBoostingRegressor  # type: ignore
        except Exception as exc:  # pragma: no cover - dependency install failure
            raise RuntimeError("gradient_boosting requires scikit-learn. Install project runtime dependencies.") from exc
        return GradientBoostingRegressor(**params)
    if name == "lasso":
        try:
            from sklearn.linear_model import Lasso  # type: ignore
        except Exception as exc:  # pragma: no cover - dependency install failure
            raise RuntimeError("lasso requires scikit-learn. Install project runtime dependencies.") from exc
        params.setdefault("alpha", 0.01)
        params.setdefault("max_iter", 5000)
        return Lasso(**params)
    if name == "elasticnet":
        try:
            from sklearn.linear_model import ElasticNet  # type: ignore
        except Exception as exc:  # pragma: no cover - dependency install failure
            raise RuntimeError("elasticnet requires scikit-learn. Install project runtime dependencies.") from exc
        params.setdefault("alpha", 0.01)
        params.setdefault("l1_ratio", 0.5)
        params.setdefault("max_iter", 5000)
        params.setdefault("random_state", 42)
        return ElasticNet(**params)
    if name == "extra_trees":
        try:
            from sklearn.ensemble import ExtraTreesRegressor  # type: ignore
        except Exception as exc:  # pragma: no cover - dependency install failure
            raise RuntimeError("extra_trees requires scikit-learn. Install project runtime dependencies.") from exc
        params.setdefault("n_estimators", 50)
        params.setdefault("random_state", 42)
        params.setdefault("n_jobs", 1)
        return ExtraTreesRegressor(**params)
    if name == "knn":
        try:
            from sklearn.neighbors import KNeighborsRegressor  # type: ignore
        except Exception as exc:  # pragma: no cover - dependency install failure
            raise RuntimeError("knn requires scikit-learn. Install project runtime dependencies.") from exc
        params.setdefault("n_neighbors", 5)
        params.setdefault("weights", "distance")
        return KNeighborsRegressor(**params)
    if name == "svr":
        try:
            from sklearn.svm import SVR  # type: ignore
        except Exception as exc:  # pragma: no cover - dependency install failure
            raise RuntimeError("svr requires scikit-learn. Install project runtime dependencies.") from exc
        params.setdefault("kernel", "rbf")
        params.setdefault("C", 1.0)
        params.setdefault("epsilon", 0.1)
        params.setdefault("gamma", "scale")
        return SVR(**params)
    if name == "mlp":
        try:
            from sklearn.neural_network import MLPRegressor  # type: ignore
        except Exception as exc:  # pragma: no cover - dependency install failure
            raise RuntimeError("mlp requires scikit-learn. Install project runtime dependencies.") from exc
        params.setdefault("hidden_layer_sizes", [32])
        params.setdefault("solver", "lbfgs")
        params.setdefault("max_iter", 500)
        params.setdefault("random_state", 42)
        return MLPRegressor(**params)
    raise ValueError(f"Unknown model name: {name}. Available: {', '.join(AVAILABLE_MODELS)}")
