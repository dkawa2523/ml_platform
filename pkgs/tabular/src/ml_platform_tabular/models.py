from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np
import pandas as pd

from .model_candidates import ModelCandidate, model_candidates
from .model_catalog import (
    AVAILABLE_MODELS,
    DEPENDENCY_FREE_MODELS,
    OPTIONAL_DEPENDENCY_MODELS,
    OPTIONAL_MODEL_SPECS,
    SKLEARN_MODEL_SPECS,
    SUPPORTED_MODELS,
    model_params_for_seed,
    validate_model_name,
)

__all__ = [
    "AVAILABLE_MODELS",
    "DEPENDENCY_FREE_MODELS",
    "OPTIONAL_DEPENDENCY_MODELS",
    "SUPPORTED_MODELS",
    "FrameTransformer",
    "MeanTopKEnsemble",
    "MedianEnsemble",
    "ModelCandidate",
    "OptionalDependencyError",
    "Predictor",
    "Regressor",
    "build_model",
    "model_candidates",
    "model_params_for_seed",
    "validate_model_name",
]


class OptionalDependencyError(RuntimeError):
    """Raised when an optional model dependency is missing or unusable."""


class FrameTransformer(Protocol):
    def transform(self, X: pd.DataFrame, /) -> np.ndarray: ...


class Regressor(Protocol):
    def fit(self, X: np.ndarray, y: object, /) -> object: ...

    def predict(self, X: np.ndarray, /) -> np.ndarray: ...


class Predictor(Protocol):
    def predict(self, X: pd.DataFrame, /) -> np.ndarray: ...


@dataclass
class LinearRegressor:
    coef_: np.ndarray | None = None

    def fit(self, X: np.ndarray, y: object) -> LinearRegressor:
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

    def fit(self, X: np.ndarray, y: object) -> RidgeRegressor:
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
class MeanTopKEnsemble:
    estimators: list[Predictor]
    weights: list[float]

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self.estimators:
            raise ValueError("Ensemble has no base estimators.")
        predictions = np.column_stack([estimator.predict(X) for estimator in self.estimators])
        weights = np.asarray(self.weights, dtype=float)
        if len(weights) != predictions.shape[1]:
            raise ValueError("Ensemble weights do not match base estimators.")
        return predictions @ (weights / weights.sum())


@dataclass
class MedianEnsemble:
    estimators: list[Predictor]

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self.estimators:
            raise ValueError("Ensemble has no base estimators.")
        predictions = np.column_stack([estimator.predict(X) for estimator in self.estimators])
        return np.median(predictions, axis=1)


def build_model(name: str, params: dict[str, Any] | None = None, *, seed: int = 42) -> Regressor:
    validate_model_name(name)
    params = model_params_for_seed(name, params, seed)
    if name == "linear":
        if params:
            raise ValueError(f"linear does not accept model parameters: {sorted(params)}")
        return LinearRegressor()
    if name == "ridge":
        return RidgeRegressor(**params)
    if name in SKLEARN_MODEL_SPECS:
        return _build_sklearn_model(name, params)
    if name in OPTIONAL_MODEL_SPECS:
        return _build_optional_model(name, params)
    raise ValueError(f"Unknown model name: {name}. Available: {', '.join(AVAILABLE_MODELS)}")


def _build_sklearn_model(name: str, params: dict[str, Any]) -> Regressor:
    module_name, class_name, defaults = SKLEARN_MODEL_SPECS[name]
    model_cls = _required_model_class(module_name, class_name, name)
    _apply_defaults(params, defaults)
    return model_cls(**params)


def _build_optional_model(name: str, params: dict[str, Any]) -> Regressor:
    module_name, class_name, defaults = OPTIONAL_MODEL_SPECS[name]
    model_cls = _optional_dependency_model_class(module_name, class_name, name)
    _apply_defaults(params, defaults)
    return model_cls(**params)


def _apply_defaults(params: dict[str, Any], defaults: dict[str, Any]) -> None:
    for key, value in defaults.items():
        params.setdefault(key, value)


def _required_model_class(module_name: str, class_name: str, model_name: str):
    try:
        module = importlib.import_module(module_name)
    except (ModuleNotFoundError, ImportError) as exc:  # pragma: no cover - dependency install failure
        raise RuntimeError(f"{model_name} requires scikit-learn. Install project runtime dependencies.") from exc
    return getattr(module, class_name)


def _optional_install_hint() -> str:
    return (
        'Install with `uv sync --extra gbm`, `uv pip install -e "pkgs/tabular[gbm]"`, '
        "or use a ClearML Agent image that includes the GBM packages."
    )


def _optional_dependency_model_class(module_name: str, class_name: str, model_name: str):
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional environment
        if exc.name != module_name:
            raise
        raise OptionalDependencyError(
            f"{model_name} requires optional dependency {module_name}, but it is not installed. "
            f"{_optional_install_hint()}"
        ) from exc
    except ImportError as exc:  # pragma: no cover - depends on optional environment
        raise OptionalDependencyError(
            f"{model_name} requires optional dependency {module_name}, but {module_name} could not be imported. "
            f"{_optional_install_hint()} Original import error: {exc}"
        ) from exc
    try:
        return getattr(module, class_name)
    except AttributeError as exc:  # pragma: no cover - depends on optional package version
        raise OptionalDependencyError(
            f"{model_name} requires {module_name}.{class_name}, but the installed package does not expose it. "
            f"Check the installed {module_name} version or reinstall the `gbm` extra."
        ) from exc
