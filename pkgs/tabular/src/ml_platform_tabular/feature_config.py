from __future__ import annotations

from typing import Any

from ml_platform_core.value_coercion import as_str_list

PRESET_DEFAULTS: dict[str, dict[str, Any]] = {
    "basic": {
        "numeric_impute_strategy": "median",
        "categorical_impute_strategy": "missing_token",
        "categorical_encoder": "onehot",
        "scaling": "standard",
        "max_dense_cells": 25_000_000,
    },
    "numeric_only": {
        "numeric_impute_strategy": "median",
        "categorical_impute_strategy": "missing_token",
        "categorical_encoder": "drop",
        "scaling": "standard",
        "max_dense_cells": 25_000_000,
    },
}
FEATURE_CONFIG_KEYS = {
    "numeric_impute_strategy",
    "categorical_impute_strategy",
    "categorical_encoder",
    "scaling",
    "drop_columns",
    "passthrough_columns",
    "max_dense_cells",
}
NUMERIC_IMPUTE_STRATEGIES = {"median", "mean", "zero"}
CATEGORICAL_IMPUTE_STRATEGIES = {"missing_token", "mode"}
CATEGORICAL_ENCODERS = {"onehot", "drop"}
SCALING_OPTIONS = {"standard", "none"}


def normalize_feature_config(feature_cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve a feature preset and its explicit overrides."""
    raw = dict(feature_cfg or {})
    params = _feature_params(raw)
    preset = _feature_preset(raw, params)
    resolved = _feature_defaults(preset, params)
    _apply_overrides(resolved, params)
    _apply_overrides(resolved, raw)
    return _validate(resolved)


def _feature_params(raw: dict[str, Any]) -> dict[str, Any]:
    params = raw.get("params") or {}
    if not isinstance(params, dict):
        raise ValueError("features.params must be a mapping when provided.")
    return dict(params)


def _feature_preset(raw: dict[str, Any], params: dict[str, Any]) -> str:
    preset = str(raw.get("preset") or params.get("preset") or "basic").strip()
    if preset not in PRESET_DEFAULTS:
        raise ValueError(f"Unknown feature preset: {preset}. Available: {', '.join(PRESET_DEFAULTS)}")
    return preset


def _feature_defaults(preset: str, params: dict[str, Any]) -> dict[str, Any]:
    return {
        "preset": preset,
        **PRESET_DEFAULTS[preset],
        "drop_columns": [],
        "passthrough_columns": [],
        "params": dict(params),
    }


def _apply_overrides(resolved: dict[str, Any], values: dict[str, Any]) -> None:
    for key in FEATURE_CONFIG_KEYS:
        if key in values and values[key] is not None:
            resolved[key] = values[key]


def _choice(name: str, value: object, choices: set[str]) -> str:
    text = str(value or "").strip()
    if text not in choices:
        raise ValueError(f"features.{name} must be one of {sorted(choices)}, got: {value!r}")
    return text


def _validate(resolved: dict[str, Any]) -> dict[str, Any]:
    resolved["numeric_impute_strategy"] = _choice(
        "numeric_impute_strategy", resolved["numeric_impute_strategy"], NUMERIC_IMPUTE_STRATEGIES
    )
    resolved["categorical_impute_strategy"] = _choice(
        "categorical_impute_strategy", resolved["categorical_impute_strategy"], CATEGORICAL_IMPUTE_STRATEGIES
    )
    resolved["categorical_encoder"] = _choice(
        "categorical_encoder", resolved["categorical_encoder"], CATEGORICAL_ENCODERS
    )
    resolved["scaling"] = _choice("scaling", resolved["scaling"], SCALING_OPTIONS)
    resolved["drop_columns"] = as_str_list(resolved.get("drop_columns")) or []
    resolved["passthrough_columns"] = as_str_list(resolved.get("passthrough_columns")) or []
    max_dense_cells = resolved.get("max_dense_cells")
    if isinstance(max_dense_cells, bool) or not isinstance(max_dense_cells, int) or max_dense_cells < 1:
        raise ValueError("features.max_dense_cells must be a positive integer.")
    return resolved
