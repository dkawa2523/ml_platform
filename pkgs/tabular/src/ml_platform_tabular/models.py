from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np
import pandas as pd

DEPENDENCY_FREE_MODELS = [
    "linear",
    "ridge",
    "lasso",
    "elasticnet",
    "random_forest",
    "extra_trees",
    "gradient_boosting",
]
OPTIONAL_DEPENDENCY_MODELS = [
    "lightgbm",
    "xgboost",
    "catboost",
]
SUPPORTED_MODELS = [*DEPENDENCY_FREE_MODELS, *OPTIONAL_DEPENDENCY_MODELS]
AVAILABLE_MODELS = list(SUPPORTED_MODELS)
OUT_OF_SCOPE_MODELS = {
    "knn",
    "svr",
    "mlp",
    "gaussian_process",
    "tabpfn",
}
SKLEARN_MODEL_SPECS: dict[str, tuple[str, str, dict[str, Any]]] = {
    "random_forest": ("sklearn.ensemble", "RandomForestRegressor", {"n_jobs": 1}),
    "gradient_boosting": ("sklearn.ensemble", "GradientBoostingRegressor", {}),
    "lasso": ("sklearn.linear_model", "Lasso", {"alpha": 0.01, "max_iter": 5000}),
    "elasticnet": (
        "sklearn.linear_model",
        "ElasticNet",
        {"alpha": 0.01, "l1_ratio": 0.5, "max_iter": 5000},
    ),
    "extra_trees": ("sklearn.ensemble", "ExtraTreesRegressor", {"n_estimators": 50, "n_jobs": 1}),
}
OPTIONAL_MODEL_SPECS: dict[str, tuple[str, str, dict[str, Any]]] = {
    "lightgbm": ("lightgbm", "LGBMRegressor", {"n_estimators": 100, "n_jobs": 1}),
    "xgboost": (
        "xgboost",
        "XGBRegressor",
        {"n_estimators": 100, "n_jobs": 1, "objective": "reg:squarederror", "verbosity": 0},
    ),
    "catboost": ("catboost", "CatBoostRegressor", {"iterations": 100, "verbose": False}),
}
MODEL_SEED_PARAMETERS = {
    "elasticnet": "random_state",
    "random_forest": "random_state",
    "extra_trees": "random_state",
    "gradient_boosting": "random_state",
    "lightgbm": "random_state",
    "xgboost": "random_state",
    "catboost": "random_seed",
}


class OptionalDependencyError(RuntimeError):
    """Raised when an optional model dependency is missing or unusable."""


class FrameTransformer(Protocol):
    def transform(self, X: pd.DataFrame, /) -> np.ndarray: ...


class Regressor(Protocol):
    def fit(self, X: np.ndarray, y: object, /) -> object: ...

    def predict(self, X: np.ndarray, /) -> np.ndarray: ...


class Predictor(Protocol):
    def predict(self, X: pd.DataFrame, /) -> np.ndarray: ...


@dataclass(frozen=True)
class ModelCandidate:
    name: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "params": dict(self.params)}


def validate_model_name(name: str) -> str:
    if name in OUT_OF_SCOPE_MODELS:
        raise ValueError(
            f"Model {name!r} is out of current product scope. "
            "Use supported models only; LightGBM/XGBoost/CatBoost require optional dependencies."
        )
    if name not in AVAILABLE_MODELS:
        raise ValueError(f"Unknown model name: {name}. Available: {', '.join(AVAILABLE_MODELS)}")
    return name


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


def model_candidates(model_cfg: dict[str, Any]) -> list[ModelCandidate]:
    raw_candidates = model_cfg.get("candidates") or []
    model_params = model_cfg.get("params") or {}
    if not raw_candidates:
        return [_single_model_candidate(model_cfg, model_params)]
    if not isinstance(raw_candidates, list):
        raise ValueError("model.candidates must be a list of model names or model definitions.")
    return _model_candidate_list(raw_candidates, model_params)


def _single_model_candidate(model_cfg: dict[str, Any], model_params: Any) -> ModelCandidate:
    if not isinstance(model_params, dict):
        raise ValueError("model.params must be a mapping.")
    name = str(model_cfg.get("name", "ridge"))
    validate_model_name(name)
    return ModelCandidate(name=name, params=dict(model_params))


def _model_candidate_list(raw_candidates: list[Any], model_params: Any) -> list[ModelCandidate]:
    candidates: list[ModelCandidate] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_candidates):
        candidate = _model_candidate(item, index, model_params)
        _add_unique_candidate(candidates, seen, candidate)
    return candidates


def _model_candidate(item: Any, index: int, model_params: Any) -> ModelCandidate:
    if isinstance(item, str):
        name = item.strip()
        if not name:
            raise ValueError(f"model.candidates[{index}] must not be empty.")
        return ModelCandidate(name=name, params=candidate_params(model_params, name))
    if isinstance(item, dict):
        return _model_candidate_from_mapping(item, index, model_params)
    raise ValueError(f"model.candidates[{index}] must be a model name or mapping.")


def _model_candidate_from_mapping(item: dict[str, Any], index: int, model_params: Any) -> ModelCandidate:
    name = item.get("name")
    if not name:
        raise ValueError(f"model.candidates[{index}].name is required.")
    name = str(name)
    params = item.get("params")
    if params is None:
        params = candidate_params(model_params, name)
    if not isinstance(params, dict):
        raise ValueError(f"model.candidates[{index}].params must be a mapping.")
    return ModelCandidate(name=name, params=dict(params))


def _add_unique_candidate(candidates: list[ModelCandidate], seen: set[str], candidate: ModelCandidate) -> None:
    name = candidate.name
    if name in seen:
        raise ValueError(f"model.candidates contains duplicate model name: {name}")
    validate_model_name(name)
    seen.add(name)
    candidates.append(ModelCandidate(name=str(name), params=dict(candidate.params)))


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


def model_params_for_seed(name: str, params: dict[str, Any] | None, seed: int) -> dict[str, Any]:
    """Return effective model params with run.seed as the only random seed."""
    resolved = dict(params or {})
    seed_parameter = MODEL_SEED_PARAMETERS.get(name)
    if seed_parameter:
        resolved[seed_parameter] = int(seed)
    return resolved


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
