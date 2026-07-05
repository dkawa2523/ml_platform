from __future__ import annotations

import math
from typing import Any

from .metrics import DEFAULT_REGRESSION_METRICS


REPORT_METRICS = ("rmse", "mae", "r2")
HIGHER_IS_BETTER_METRICS = {"r2"}
SELECTION_METRICS = set(REPORT_METRICS)


def metric_value(metrics: dict[str, float], selection_metric: str) -> float:
    if selection_metric not in metrics:
        raise ValueError(f"selection_metric is missing from metrics: {selection_metric}")
    value = float(metrics[selection_metric])
    if not math.isfinite(value):
        raise ValueError(f"selection_metric must be finite: {selection_metric}")
    return value


def higher_is_better(metric_name: str) -> bool:
    return metric_name in HIGHER_IS_BETTER_METRICS


def selection_sort_value(metrics: dict[str, float], selection_metric: str) -> float:
    value = metric_value(metrics, selection_metric)
    return -value if higher_is_better(selection_metric) else value


def metric_improved(metric_name: str, baseline_value: float | None, candidate_value: float | None) -> bool | None:
    if baseline_value is None or candidate_value is None:
        return None
    if higher_is_better(metric_name):
        return candidate_value > baseline_value
    return candidate_value < baseline_value


def metric_plot_sort(metric_name: str) -> str:
    return "value_desc" if higher_is_better(metric_name) else "value_asc"


def metric_weight_value(metrics: dict[str, float], selection_metric: str, *, epsilon: float) -> float:
    if selection_metric not in SELECTION_METRICS:
        raise ValueError("model.selection_metric must be one of: mae, rmse, r2.")
    value = metric_value(metrics, selection_metric)
    if higher_is_better(selection_metric):
        return max(value, 0.0)
    return 1.0 / max(value, epsilon)


def metric_settings(cfg: dict[str, Any], model_cfg: dict[str, Any]) -> tuple[str, list[str]]:
    selection_metric = _metric_name(model_cfg.get("selection_metric") or "rmse")
    if selection_metric not in SELECTION_METRICS:
        raise ValueError("model.selection_metric must be one of: mae, rmse, r2.")
    return selection_metric, _required_metric_names(cfg.get("metrics", {}).get("names"), selection_metric)


def _required_metric_names(metric_names: Any, selection_metric: str) -> list[str]:
    names = _configured_metric_names(metric_names)
    return _with_required_metrics(names, selection_metric)


def _configured_metric_names(metric_names: Any) -> list[str]:
    if metric_names is None:
        return list(DEFAULT_REGRESSION_METRICS)
    if isinstance(metric_names, str):
        return _metric_names_from_string(metric_names)
    return _metric_names_from_iterable(metric_names)


def _metric_names_from_string(metric_names: str) -> list[str]:
    names: list[str] = []
    for name in metric_names.split(","):
        if name.strip():
            names.append(_metric_name(name))
    return names


def _metric_names_from_iterable(metric_names: Any) -> list[str]:
    return [_metric_name(name) for name in metric_names]


def _with_required_metrics(names: list[str], selection_metric: str) -> list[str]:
    for name in [*REPORT_METRICS, selection_metric]:
        if name not in names:
            names.append(name)
    return names


def _metric_name(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")
