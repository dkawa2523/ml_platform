from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import json
import math
from typing import Any, Protocol

from ml_platform_core.value_coercion import as_bool

from .selection import metric_value as _metric_value, metric_weight_value

WEIGHT_EPSILON = 1e-12
SUPPORTED_ENSEMBLE_METHODS = ("mean_topk", "weighted", "median")


@dataclass(frozen=True)
class EnsembleConfig:
    enabled: bool
    method: str
    methods: list[str]
    top_k: int


class MetricsCarrier(Protocol):
    metrics: dict[str, float]


def ensemble_config(model_cfg: dict[str, Any]) -> EnsembleConfig:
    raw = model_cfg.get("ensemble") or {}
    if not isinstance(raw, dict):
        raise ValueError("model.ensemble must be a mapping.")
    enabled = as_bool(raw.get("enabled"))
    methods = _ensemble_methods(raw)
    method = methods[0]
    top_k = int(raw.get("top_k") or 3)
    if top_k < 1:
        raise ValueError("model.ensemble.top_k must be >= 1.")
    if enabled:
        _validate_ensemble_methods(methods)
    return EnsembleConfig(enabled=enabled, method=method, methods=methods, top_k=top_k)


def _ensemble_methods(raw: dict[str, Any]) -> list[str]:
    normalized = _unique_methods(_raw_ensemble_methods(raw))
    if not normalized:
        raise ValueError("model.ensemble.methods must contain at least one method.")
    return normalized


def _raw_ensemble_methods(raw: dict[str, Any]) -> list[Any]:
    methods = raw.get("methods")
    if methods is None or methods == "":
        return [raw.get("method") or "mean_topk"]
    if isinstance(methods, str):
        return _methods_from_text(methods, default=raw.get("method") or "mean_topk")
    if not isinstance(methods, list):
        raise ValueError("model.ensemble.methods must be a list of method names.")
    return methods


def _methods_from_text(value: str, *, default: str) -> list[Any]:
    text = value.strip()
    if not text:
        return [default]
    if text.startswith("["):
        return json.loads(text)
    return [item.strip() for item in text.split(",") if item.strip()]


def _unique_methods(methods: list[Any]) -> list[str]:
    normalized: list[str] = []
    seen = set()
    for item in methods:
        name = str(item).strip()
        if not name:
            continue
        if name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return normalized


def _validate_ensemble_methods(methods: list[str]) -> None:
    invalid = [name for name in methods if name not in SUPPORTED_ENSEMBLE_METHODS]
    if invalid:
        raise ValueError(
            f"model.ensemble.methods must contain only: {', '.join(SUPPORTED_ENSEMBLE_METHODS)}. Invalid: {invalid}"
        )


def metric_value(metrics: dict[str, float], selection_metric: str) -> float:
    """Compatibility wrapper; selection owns metric semantics."""
    return _metric_value(metrics, selection_metric)


def ensemble_weights(selected_results: Sequence[MetricsCarrier], method: str, selection_metric: str) -> list[float]:
    if not selected_results:
        raise ValueError("At least one selected model is required for ensemble.")
    if method in {"mean_topk", "median"}:
        return _uniform_weights(selected_results)
    if method != "weighted":
        raise ValueError("model.ensemble.method must be one of: mean_topk, weighted, median.")
    return _normalized_weights(_raw_weight_values(selected_results, selection_metric), selected_results)


def _uniform_weights(selected_results: Sequence[MetricsCarrier]) -> list[float]:
    return [1.0 / len(selected_results)] * len(selected_results)


def _raw_weight_values(selected_results: Sequence[MetricsCarrier], selection_metric: str) -> list[float]:
    return [metric_weight_value(item.metrics, selection_metric, epsilon=WEIGHT_EPSILON) for item in selected_results]


def _normalized_weights(raw_weights: list[float], selected_results: Sequence[MetricsCarrier]) -> list[float]:
    total = sum(raw_weights)
    if not math.isfinite(total) or total <= WEIGHT_EPSILON:
        return _uniform_weights(selected_results)
    return [float(weight) / total for weight in raw_weights]
