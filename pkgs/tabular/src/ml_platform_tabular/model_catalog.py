from __future__ import annotations

from typing import Any

DEPENDENCY_FREE_MODELS = [
    "linear",
    "ridge",
    "lasso",
    "elasticnet",
    "random_forest",
    "extra_trees",
    "gradient_boosting",
]
OPTIONAL_DEPENDENCY_MODELS = ["lightgbm", "xgboost", "catboost"]
SUPPORTED_MODELS = [*DEPENDENCY_FREE_MODELS, *OPTIONAL_DEPENDENCY_MODELS]
AVAILABLE_MODELS = list(SUPPORTED_MODELS)
OUT_OF_SCOPE_MODELS = {"knn", "svr", "mlp", "gaussian_process", "tabpfn"}

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


def validate_model_name(name: str) -> str:
    if name in OUT_OF_SCOPE_MODELS:
        raise ValueError(
            f"Model {name!r} is out of current product scope. "
            "Use supported models only; LightGBM/XGBoost/CatBoost require optional dependencies."
        )
    if name not in AVAILABLE_MODELS:
        raise ValueError(f"Unknown model name: {name}. Available: {', '.join(AVAILABLE_MODELS)}")
    return name


def model_params_for_seed(name: str, params: dict[str, Any] | None, seed: int) -> dict[str, Any]:
    """Return effective model params with run.seed as the only random seed."""
    resolved = dict(params or {})
    seed_parameter = MODEL_SEED_PARAMETERS.get(name)
    if seed_parameter:
        resolved[seed_parameter] = int(seed)
    return resolved
