from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

from .models import DEPENDENCY_FREE_MODELS, OPTIONAL_DEPENDENCY_MODELS, SUPPORTED_MODELS, model_candidates

TABULAR_MODEL_SUITES: dict[str, tuple[str, ...]] = {
    "default": tuple(SUPPORTED_MODELS),
    "fast": tuple(DEPENDENCY_FREE_MODELS),
    "interpretable": ("linear", "ridge", "lasso", "elasticnet"),
    "tree": ("random_forest", "extra_trees", "gradient_boosting"),
    "gbm": tuple(OPTIONAL_DEPENDENCY_MODELS),
}
TABULAR_CUSTOM_MODEL_SUITE = "custom"
TABULAR_QUALITY_MODES = ("fast", "standard", "quality")
TABULAR_QUALITY_MODEL_PARAMS: dict[str, dict[str, dict[str, object]]] = {
    "fast": {
        "linear": {},
        "ridge": {"alpha": 1.0},
        "lasso": {"alpha": 0.01, "max_iter": 3000},
        "elasticnet": {"alpha": 0.01, "l1_ratio": 0.5, "max_iter": 3000, "random_state": 42},
        "random_forest": {"n_estimators": 10, "random_state": 42, "n_jobs": 1},
        "extra_trees": {"n_estimators": 10, "random_state": 42, "n_jobs": 1},
        "gradient_boosting": {"n_estimators": 10, "random_state": 42},
        "lightgbm": {"n_estimators": 30, "random_state": 42, "n_jobs": 1},
        "xgboost": {
            "n_estimators": 30,
            "random_state": 42,
            "n_jobs": 1,
            "objective": "reg:squarederror",
            "verbosity": 0,
        },
        "catboost": {"iterations": 30, "random_seed": 42, "verbose": False},
    },
    "standard": {
        "linear": {},
        "ridge": {"alpha": 1.0},
        "lasso": {"alpha": 0.01, "max_iter": 5000},
        "elasticnet": {"alpha": 0.01, "l1_ratio": 0.5, "max_iter": 5000, "random_state": 42},
        "random_forest": {"n_estimators": 20, "random_state": 42, "n_jobs": 1},
        "extra_trees": {"n_estimators": 20, "random_state": 42, "n_jobs": 1},
        "gradient_boosting": {"n_estimators": 20, "random_state": 42},
        "lightgbm": {"n_estimators": 100, "random_state": 42, "n_jobs": 1},
        "xgboost": {
            "n_estimators": 100,
            "random_state": 42,
            "n_jobs": 1,
            "objective": "reg:squarederror",
            "verbosity": 0,
        },
        "catboost": {"iterations": 100, "random_seed": 42, "verbose": False},
    },
    "quality": {
        "linear": {},
        "ridge": {"alpha": 1.0},
        "lasso": {"alpha": 0.01, "max_iter": 8000},
        "elasticnet": {"alpha": 0.01, "l1_ratio": 0.5, "max_iter": 8000, "random_state": 42},
        "random_forest": {"n_estimators": 60, "random_state": 42, "n_jobs": 1},
        "extra_trees": {"n_estimators": 60, "random_state": 42, "n_jobs": 1},
        "gradient_boosting": {"n_estimators": 60, "random_state": 42},
        "lightgbm": {"n_estimators": 200, "random_state": 42, "n_jobs": 1},
        "xgboost": {
            "n_estimators": 200,
            "random_state": 42,
            "n_jobs": 1,
            "objective": "reg:squarederror",
            "verbosity": 0,
        },
        "catboost": {"iterations": 200, "random_seed": 42, "verbose": False},
    },
}


def model_suite_names(*, include_custom: bool = True) -> tuple[str, ...]:
    names = tuple(TABULAR_MODEL_SUITES)
    if include_custom:
        return (*names, TABULAR_CUSTOM_MODEL_SUITE)
    return names


def model_suite_candidates(suite: str) -> tuple[str, ...]:
    normalized = suite.strip().lower()
    if normalized == TABULAR_CUSTOM_MODEL_SUITE:
        return ()
    try:
        return TABULAR_MODEL_SUITES[normalized]
    except KeyError as exc:
        choices = ", ".join(model_suite_names())
        raise ValueError(f"model suite must be one of: {choices}.") from exc


def quality_mode_names() -> tuple[str, ...]:
    return TABULAR_QUALITY_MODES


def quality_model_params(mode: str) -> dict[str, dict[str, object]]:
    normalized = mode.strip().lower()
    try:
        return deepcopy(TABULAR_QUALITY_MODEL_PARAMS[normalized])
    except KeyError as exc:
        choices = ", ".join(TABULAR_QUALITY_MODES)
        raise ValueError(f"quality mode must be one of: {choices}.") from exc


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True)


def _as_bool(value: object, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"", "none", "null"}:
            return default
        return text in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _as_str_list(value: object) -> list[str] | None:
    if value is None or value == "":
        return None
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = None
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
        return [item.strip() for item in text.split(",") if item.strip()]
    raise ValueError(f"Cannot convert value to list: {value!r}")


def _as_dict(value: object) -> dict[str, Any]:
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError(f"Expected JSON object, got: {value!r}")
        return parsed
    raise ValueError(f"Cannot convert value to dict: {value!r}")


def _as_candidates(value: object) -> list[object]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        value = json.loads(text)
    if not isinstance(value, list):
        raise ValueError(f"Expected JSON array for candidates, got: {value!r}")
    candidates: list[object] = []
    for index, item in enumerate(value):
        if isinstance(item, str):
            text = item.strip()
            if not text:
                raise ValueError(f"Model/candidates[{index}] must not be empty.")
            candidates.append(text)
        elif isinstance(item, dict):
            candidates.append(dict(item))
        else:
            raise ValueError(f"Model/candidates[{index}] must be a model name or object.")
    return candidates


def _has_runtime_value(value: object) -> bool:
    return value is not None and not (isinstance(value, str) and value.strip() == "")


def basic_config(pipeline_cfg: dict[str, Any]) -> dict[str, Any]:
    raw = pipeline_cfg.get("basic") or pipeline_cfg.get("Basic") or {}
    return raw if isinstance(raw, dict) else {}


def _runtime_text(runtime_params: dict[str, Any], key: str, default: str) -> str:
    value = runtime_params.get(key)
    if not _has_runtime_value(value):
        return default
    return str(value).strip().lower()


def runtime_model_suite(runtime_params: dict[str, Any]) -> str:
    suite = _runtime_text(runtime_params, "Basic/model_suite", "default")
    if suite not in model_suite_names():
        choices = ", ".join(model_suite_names())
        raise ValueError(f"Basic/model_suite must be one of: {choices}.")
    return suite


def runtime_quality_mode(runtime_params: dict[str, Any]) -> str:
    mode = _runtime_text(runtime_params, "Basic/quality_mode", "standard")
    if mode not in quality_mode_names():
        choices = ", ".join(quality_mode_names())
        raise ValueError(f"Basic/quality_mode must be one of: {choices}.")
    return mode


def apply_runtime_model_suite(model_cfg: dict[str, Any], runtime_params: dict[str, Any]) -> None:
    suite = runtime_model_suite(runtime_params)
    if suite in {"default", TABULAR_CUSTOM_MODEL_SUITE}:
        return
    model_cfg["candidates"] = list(model_suite_candidates(suite))


def apply_runtime_quality_mode(
    model_cfg: dict[str, Any],
    runtime_params: dict[str, Any],
    explicit_runtime_params: dict[str, Any],
) -> None:
    if "Model/model_params_by_name" in explicit_runtime_params or "Model/params" in explicit_runtime_params:
        return
    if runtime_model_suite(runtime_params) == TABULAR_CUSTOM_MODEL_SUITE:
        return
    model_cfg["params"] = quality_model_params(runtime_quality_mode(runtime_params))


def model_cfg_for_runtime(
    pipeline_cfg: dict[str, Any],
    runtime_params: dict[str, Any] | None = None,
    explicit_runtime_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model_cfg = deepcopy(pipeline_cfg.get("model", {}) or {})
    runtime_params = runtime_params or {}
    explicit_runtime_params = explicit_runtime_params or {}
    if "Model/candidates" in runtime_params:
        model_cfg["candidates"] = _as_candidates(runtime_params.get("Model/candidates"))
    if "Model/model_params_by_name" in explicit_runtime_params:
        model_cfg["params"] = _as_dict(runtime_params.get("Model/model_params_by_name"))
    elif "Model/params" in explicit_runtime_params:
        model_cfg["params"] = _as_dict(runtime_params.get("Model/params"))
    if "Model/selection_metric" in runtime_params and runtime_params.get("Model/selection_metric"):
        model_cfg["selection_metric"] = runtime_params["Model/selection_metric"]
    apply_runtime_model_suite(model_cfg, runtime_params)
    apply_runtime_quality_mode(model_cfg, runtime_params, explicit_runtime_params)
    if _has_runtime_value(runtime_params.get("Basic/use_ensemble")):
        model_cfg.setdefault("ensemble", {})["enabled"] = _as_bool(runtime_params.get("Basic/use_ensemble"))
    if _has_runtime_value(runtime_params.get("Model/ensemble_enabled")):
        model_cfg.setdefault("ensemble", {})["enabled"] = _as_bool(runtime_params.get("Model/ensemble_enabled"))
    if "Model/ensemble_methods" in runtime_params:
        model_cfg.setdefault("ensemble", {})["methods"] = (
            _as_str_list(runtime_params.get("Model/ensemble_methods")) or []
        )
    if "Model/ensemble_method" in runtime_params and runtime_params.get("Model/ensemble_method"):
        model_cfg.setdefault("ensemble", {})["method"] = runtime_params["Model/ensemble_method"]
    if "Model/ensemble_top_k" in runtime_params and runtime_params.get("Model/ensemble_top_k") not in {None, ""}:
        model_cfg.setdefault("ensemble", {})["top_k"] = int(runtime_params["Model/ensemble_top_k"])
    return model_cfg


def validate_primary_training_graph(model_cfg: dict[str, Any]) -> None:
    search_cfg = model_cfg.get("search", {}) or {}
    if not isinstance(search_cfg, dict):
        search_cfg = {}
    if _as_bool(search_cfg.get("enabled")):
        raise ValueError(
            "model.search.enabled=true is future/experimental and is not part of the "
            "primary ClearML training pipeline graph. Remove model.search or set enabled=false for "
            "preprocess_features -> train_<model>* -> build_ensemble_<method>* -> evaluate_models."
        )


def training_model_candidates(model_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = model_candidates(model_cfg)
    if not candidates:
        raise ValueError("Training pipeline requires at least one model candidate.")
    return candidates


def ensemble_methods_from_config(ensemble_cfg: dict[str, Any]) -> list[str]:
    raw = ensemble_cfg.get("methods")
    if raw is None or raw == "":
        raw = [ensemble_cfg.get("method") or "mean_topk"]
    methods = _as_str_list(raw) or []
    return methods or ["mean_topk"]


def ensemble_enabled_from_config(ensemble_cfg: dict[str, Any]) -> bool:
    return _as_bool(ensemble_cfg.get("enabled"))


def pipeline_runtime_defaults(
    pipeline_cfg: dict[str, Any],
    *,
    remote_default_dataset_id: object | None = None,
    remote_default_dataset_file: object | None = None,
    use_clearml: bool = False,
) -> dict[str, Any]:
    run = pipeline_cfg.get("run", {})
    basic = basic_config(pipeline_cfg)
    data = pipeline_cfg.get("data", {})
    split = pipeline_cfg.get("split", {}) or {}
    features = pipeline_cfg.get("features", {}) or {}
    model = pipeline_cfg.get("model", {})
    metrics = pipeline_cfg.get("metrics", {}) or {}
    output = pipeline_cfg.get("output", {}) or {}
    ensemble = model.get("ensemble", {}) or {}
    if not isinstance(ensemble, dict):
        ensemble = {}
    clearml_dataset_id = data.get("clearml_dataset_id")
    dataset_file = data.get("dataset_file")
    local_path = data.get("local_path")
    if use_clearml and remote_default_dataset_id and not clearml_dataset_id:
        clearml_dataset_id = remote_default_dataset_id
        dataset_file = dataset_file or remote_default_dataset_file
        local_path = ""
    return {
        "Basic/model_suite": basic.get("model_suite", "default"),
        "Basic/quality_mode": basic.get("quality_mode", "standard"),
        "Basic/use_ensemble": basic.get("use_ensemble", _as_bool(ensemble.get("enabled"), default=True)),
        "Basic/notes": basic.get("notes") or run.get("description", ""),
        "Run/name": run.get("name"),
        "Run/seed": run.get("seed"),
        "Split/method": split.get("method", "random"),
        "Split/valid_size": split.get("valid_size", 0.2),
        "Split/group_column": split.get("group_column"),
        "Split/time_column": split.get("time_column"),
        "Split/valid_filter_column": split.get("valid_filter_column"),
        "Split/valid_filter_value": split.get("valid_filter_value"),
        "Input/local_path": local_path,
        "Input/clearml_dataset_id": clearml_dataset_id,
        "Input/dataset_file": dataset_file,
        "Input/target_column": data.get("target_column"),
        "Input/feature_columns": data.get("feature_columns") or [],
        "Input/id_columns": data.get("id_columns", []),
        "Features/preset": features.get("preset", "basic"),
        "Features/numeric_impute_strategy": features.get("numeric_impute_strategy", "median"),
        "Features/categorical_impute_strategy": features.get("categorical_impute_strategy", "missing_token"),
        "Features/categorical_encoder": features.get("categorical_encoder", "onehot"),
        "Features/scaling": features.get("scaling", "standard"),
        "Features/drop_columns": _json(features.get("drop_columns", []) or []),
        "Features/passthrough_columns": _json(features.get("passthrough_columns", []) or []),
        "Model/candidates": _json(SUPPORTED_MODELS),
        "Model/model_params_by_name": _json(model.get("params", {}) or {}),
        "Model/evaluation_metrics": _json(metrics.get("names", []) or []),
        "Model/selection_metric": model.get("selection_metric", "rmse"),
        "Model/ensemble_enabled": "",
        "Model/ensemble_methods": _json(ensemble.get("methods", [ensemble.get("method", "mean_topk")]) or []),
        "Model/ensemble_top_k": int(ensemble.get("top_k") or 3),
        "Output/report_plots": _as_bool(output.get("report_plots"), default=True),
    }
