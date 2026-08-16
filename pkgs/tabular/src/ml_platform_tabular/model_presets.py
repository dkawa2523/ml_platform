from __future__ import annotations

from copy import deepcopy

from .model_catalog import DEPENDENCY_FREE_MODELS, OPTIONAL_DEPENDENCY_MODELS, SUPPORTED_MODELS

MODEL_SUITES: dict[str, tuple[str, ...]] = {
    "default": tuple(SUPPORTED_MODELS),
    "fast": tuple(DEPENDENCY_FREE_MODELS),
    "interpretable": ("linear", "ridge", "lasso", "elasticnet"),
    "tree": ("random_forest", "extra_trees", "gradient_boosting"),
    "gbm": tuple(OPTIONAL_DEPENDENCY_MODELS),
}
CUSTOM_MODEL_SUITE = "custom"
QUALITY_MODES = ("fast", "standard", "quality")
QUALITY_MODEL_PARAMS: dict[str, dict[str, dict[str, object]]] = {
    "fast": {
        "linear": {},
        "ridge": {"alpha": 1.0},
        "lasso": {"alpha": 0.01, "max_iter": 3000},
        "elasticnet": {"alpha": 0.01, "l1_ratio": 0.5, "max_iter": 3000},
        "random_forest": {"n_estimators": 10, "n_jobs": 1},
        "extra_trees": {"n_estimators": 10, "n_jobs": 1},
        "gradient_boosting": {"n_estimators": 10},
        "lightgbm": {"n_estimators": 30, "n_jobs": 1},
        "xgboost": {
            "n_estimators": 30,
            "n_jobs": 1,
            "objective": "reg:squarederror",
            "verbosity": 0,
        },
        "catboost": {"iterations": 30, "verbose": False},
    },
    "standard": {
        "linear": {},
        "ridge": {"alpha": 1.0},
        "lasso": {"alpha": 0.01, "max_iter": 5000},
        "elasticnet": {"alpha": 0.01, "l1_ratio": 0.5, "max_iter": 5000},
        "random_forest": {"n_estimators": 20, "n_jobs": 1},
        "extra_trees": {"n_estimators": 20, "n_jobs": 1},
        "gradient_boosting": {"n_estimators": 20},
        "lightgbm": {"n_estimators": 100, "n_jobs": 1},
        "xgboost": {
            "n_estimators": 100,
            "n_jobs": 1,
            "objective": "reg:squarederror",
            "verbosity": 0,
        },
        "catboost": {"iterations": 100, "verbose": False},
    },
    "quality": {
        "linear": {},
        "ridge": {"alpha": 1.0},
        "lasso": {"alpha": 0.01, "max_iter": 8000},
        "elasticnet": {"alpha": 0.01, "l1_ratio": 0.5, "max_iter": 8000},
        "random_forest": {"n_estimators": 60, "n_jobs": 1},
        "extra_trees": {"n_estimators": 60, "n_jobs": 1},
        "gradient_boosting": {"n_estimators": 60},
        "lightgbm": {"n_estimators": 200, "n_jobs": 1},
        "xgboost": {
            "n_estimators": 200,
            "n_jobs": 1,
            "objective": "reg:squarederror",
            "verbosity": 0,
        },
        "catboost": {"iterations": 200, "verbose": False},
    },
}


def model_suite_names(*, include_custom: bool = True) -> tuple[str, ...]:
    names = tuple(MODEL_SUITES)
    return (*names, CUSTOM_MODEL_SUITE) if include_custom else names


def model_suite_candidates(suite: str) -> tuple[str, ...]:
    normalized = suite.strip().lower()
    if normalized == CUSTOM_MODEL_SUITE:
        return ()
    try:
        return MODEL_SUITES[normalized]
    except KeyError as exc:
        choices = ", ".join(model_suite_names())
        raise ValueError(f"model suite must be one of: {choices}.") from exc


def quality_mode_names() -> tuple[str, ...]:
    return QUALITY_MODES


def quality_model_params(mode: str) -> dict[str, dict[str, object]]:
    normalized = mode.strip().lower()
    try:
        return deepcopy(QUALITY_MODEL_PARAMS[normalized])
    except KeyError as exc:
        choices = ", ".join(QUALITY_MODES)
        raise ValueError(f"quality mode must be one of: {choices}.") from exc
