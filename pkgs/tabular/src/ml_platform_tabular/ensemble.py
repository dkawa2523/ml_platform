from __future__ import annotations

import math
from typing import Any

WEIGHT_EPSILON = 1e-12
SUPPORTED_ENSEMBLE_METHODS = ("mean_topk", "weighted", "median")


def as_bool(value: Any, *, default: bool = False) -> bool:
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


def ensemble_config(model_cfg: dict[str, Any]) -> dict[str, Any]:
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
        invalid = [name for name in methods if name not in SUPPORTED_ENSEMBLE_METHODS]
        if invalid:
            raise ValueError(
                "model.ensemble.methods must contain only: "
                f"{', '.join(SUPPORTED_ENSEMBLE_METHODS)}. Invalid: {invalid}"
            )
    return {"enabled": enabled, "method": method, "methods": methods, "top_k": top_k}


def _ensemble_methods(raw: dict[str, Any]) -> list[str]:
    methods = raw.get("methods")
    if methods is None or methods == "":
        methods = [raw.get("method") or "mean_topk"]
    elif isinstance(methods, str):
        text = methods.strip()
        if not text:
            methods = [raw.get("method") or "mean_topk"]
        elif text.startswith("["):
            import json

            methods = json.loads(text)
        else:
            methods = [item.strip() for item in text.split(",") if item.strip()]
    if not isinstance(methods, list):
        raise ValueError("model.ensemble.methods must be a list of method names.")
    normalized = []
    seen = set()
    for item in methods:
        name = str(item).strip()
        if not name:
            continue
        if name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    if not normalized:
        raise ValueError("model.ensemble.methods must contain at least one method.")
    return normalized


def metric_value(metrics: dict[str, float], selection_metric: str) -> float:
    if selection_metric not in metrics:
        raise ValueError(f"selection_metric is missing from metrics: {selection_metric}")
    value = float(metrics[selection_metric])
    if not math.isfinite(value):
        raise ValueError(f"selection_metric must be finite: {selection_metric}")
    return value


def ensemble_weights(selected_results: list[dict[str, Any]], method: str, selection_metric: str) -> list[float]:
    if not selected_results:
        raise ValueError("At least one selected model is required for ensemble.")
    if method == "mean_topk":
        return [1.0 / len(selected_results)] * len(selected_results)
    if method == "median":
        return [1.0 / len(selected_results)] * len(selected_results)
    if method != "weighted":
        raise ValueError("model.ensemble.method must be one of: mean_topk, weighted, median.")

    if selection_metric in {"rmse", "mae"}:
        raw_weights = [1.0 / max(metric_value(item["metrics"], selection_metric), WEIGHT_EPSILON) for item in selected_results]
    elif selection_metric == "r2":
        raw_weights = [max(metric_value(item["metrics"], selection_metric), 0.0) for item in selected_results]
        if sum(raw_weights) <= WEIGHT_EPSILON:
            return [1.0 / len(selected_results)] * len(selected_results)
    else:
        raise ValueError("model.selection_metric must be one of: mae, rmse, r2.")

    total = sum(raw_weights)
    if not math.isfinite(total) or total <= WEIGHT_EPSILON:
        return [1.0 / len(selected_results)] * len(selected_results)
    return [float(weight) / total for weight in raw_weights]
