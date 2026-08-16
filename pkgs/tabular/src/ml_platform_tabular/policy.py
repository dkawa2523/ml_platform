from __future__ import annotations

from copy import deepcopy
from typing import Any

from ml_platform_core.value_coercion import (
    as_bool as _as_bool,
)
from ml_platform_core.value_coercion import (
    as_candidates as _as_candidates,
)
from ml_platform_core.value_coercion import (
    as_dict as _as_dict,
)
from ml_platform_core.value_coercion import (
    as_str_list as _as_str_list,
)

from .model_candidates import model_candidates
from .model_catalog import model_params_for_seed
from .model_presets import (
    CUSTOM_MODEL_SUITE,
    model_suite_candidates,
    model_suite_names,
    quality_mode_names,
    quality_model_params,
)
from .runtime_defaults import basic_config as basic_config
from .runtime_defaults import pipeline_runtime_defaults as pipeline_runtime_defaults


def _has_runtime_value(value: object) -> bool:
    return value is not None and not (isinstance(value, str) and value.strip() == "")


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
    if suite in {"default", CUSTOM_MODEL_SUITE}:
        return
    model_cfg["candidates"] = list(model_suite_candidates(suite))


def apply_runtime_quality_mode(
    model_cfg: dict[str, Any],
    runtime_params: dict[str, Any],
    explicit_runtime_params: dict[str, Any],
) -> None:
    if "Model/model_params_by_name" in explicit_runtime_params or "Model/params" in explicit_runtime_params:
        return
    if runtime_model_suite(runtime_params) == CUSTOM_MODEL_SUITE:
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
    _apply_runtime_model_overrides(model_cfg, runtime_params, explicit_runtime_params)
    apply_runtime_model_suite(model_cfg, runtime_params)
    apply_runtime_quality_mode(model_cfg, runtime_params, explicit_runtime_params)
    _apply_runtime_ensemble_overrides(model_cfg, runtime_params)
    return model_cfg


def _apply_runtime_model_overrides(
    model_cfg: dict[str, Any],
    runtime_params: dict[str, Any],
    explicit_runtime_params: dict[str, Any],
) -> None:
    if "Model/candidates" in runtime_params:
        model_cfg["candidates"] = _as_candidates(runtime_params.get("Model/candidates"))
    if "Model/model_params_by_name" in explicit_runtime_params:
        model_cfg["params"] = _as_dict(runtime_params.get("Model/model_params_by_name"))
    elif "Model/params" in explicit_runtime_params:
        model_cfg["params"] = _as_dict(runtime_params.get("Model/params"))
    if "Model/selection_metric" in runtime_params and runtime_params.get("Model/selection_metric"):
        model_cfg["selection_metric"] = runtime_params["Model/selection_metric"]


def _apply_runtime_ensemble_overrides(model_cfg: dict[str, Any], runtime_params: dict[str, Any]) -> None:
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


def validate_primary_training_graph(model_cfg: dict[str, Any]) -> None:
    search_cfg = model_cfg.get("search", {}) or {}
    if not isinstance(search_cfg, dict):
        search_cfg = {}
    if _as_bool(search_cfg.get("enabled")):
        raise ValueError(
            "model.search.enabled=true is future/experimental and is not part of the "
            "primary training graph. Remove model.search or set enabled=false. Package stage "
            "names are preprocess_features -> train_model* -> build_ensemble -> evaluate_models; "
            "ClearML step labels may include model or ensemble method suffixes."
        )


def training_model_candidates(model_cfg: dict[str, Any], *, seed: int = 42) -> list[dict[str, Any]]:
    candidates = model_candidates(model_cfg)
    if not candidates:
        raise ValueError("Training pipeline requires at least one model candidate.")
    return [
        {"name": candidate.name, "params": model_params_for_seed(candidate.name, candidate.params, seed)}
        for candidate in candidates
    ]


def ensemble_methods_from_config(ensemble_cfg: dict[str, Any]) -> list[str]:
    raw = ensemble_cfg.get("methods")
    if raw is None or raw == "":
        raw = [ensemble_cfg.get("method") or "mean_topk"]
    methods = _as_str_list(raw) or []
    return methods or ["mean_topk"]


def ensemble_enabled_from_config(ensemble_cfg: dict[str, Any]) -> bool:
    return _as_bool(ensemble_cfg.get("enabled"))
