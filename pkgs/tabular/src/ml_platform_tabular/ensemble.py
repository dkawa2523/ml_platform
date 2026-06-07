from __future__ import annotations

import math
from typing import Any

WEIGHT_EPSILON = 1e-12


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
    method = str(raw.get("method") or "mean_topk")
    top_k = int(raw.get("top_k") or 3)
    if top_k < 1:
        raise ValueError("model.ensemble.top_k must be >= 1.")
    if enabled and method not in {"mean_topk", "weighted"}:
        raise ValueError("model.ensemble.method must be one of: mean_topk, weighted.")
    return {"enabled": enabled, "method": method, "top_k": top_k}


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
    if method != "weighted":
        raise ValueError("model.ensemble.method must be one of: mean_topk, weighted.")

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
