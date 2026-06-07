from __future__ import annotations

import itertools
import json
import random
from typing import Any

from .ensemble import as_bool, metric_value

SEARCH_METHODS = {"grid", "random"}


def search_config(model_cfg: dict[str, Any]) -> dict[str, Any]:
    raw = model_cfg.get("search") or {}
    if not isinstance(raw, dict):
        raise ValueError("model.search must be a mapping.")
    enabled = as_bool(raw.get("enabled"))
    method = str(raw.get("method") or "grid").strip().lower()
    max_trials = int(raw.get("max_trials") or 20)
    search_space = raw.get("search_space") or {}
    if not isinstance(search_space, dict):
        raise ValueError("model.search.search_space must be a mapping.")
    if max_trials < 1:
        raise ValueError("model.search.max_trials must be >= 1.")
    if enabled and method not in SEARCH_METHODS:
        raise ValueError("model.search.method must be one of: grid, random.")
    return {
        "enabled": enabled,
        "method": method,
        "max_trials": max_trials,
        "search_space": search_space,
        "retrain_best": as_bool(raw.get("retrain_best"), default=True),
    }


def parameter_grid(search_space: dict[str, Any]) -> list[dict[str, Any]]:
    if not search_space:
        return [{}]
    keys = list(search_space)
    values = []
    for key in keys:
        raw_value = search_space[key]
        if not isinstance(raw_value, list) or not raw_value:
            raise ValueError(f"model.search.search_space.{key} must be a non-empty list.")
        values.append(raw_value)
    return [dict(zip(keys, combination)) for combination in itertools.product(*values)]


def search_space_for_candidate(
    search_space: dict[str, Any],
    model_name: str,
    *,
    comparison: bool,
) -> dict[str, Any]:
    if comparison:
        raw = search_space.get(model_name, {})
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise ValueError(f"model.search.search_space.{model_name} must be a mapping.")
        return raw
    return search_space


def search_trials(
    candidates: list[dict[str, Any]],
    search_cfg: dict[str, Any],
    *,
    comparison: bool,
    seed: int,
) -> list[dict[str, Any]]:
    if not search_cfg["enabled"]:
        return [
            {
                "trial": index,
                "model_name": candidate["name"],
                "model_params": candidate["params"],
            }
            for index, candidate in enumerate(candidates, start=1)
        ]

    trials: list[dict[str, Any]] = []
    for candidate in candidates:
        space = search_space_for_candidate(search_cfg["search_space"], candidate["name"], comparison=comparison)
        for params in parameter_grid(space):
            trial_params = {**candidate["params"], **params}
            trials.append(
                {
                    "trial": 0,
                    "model_name": candidate["name"],
                    "model_params": trial_params,
                }
            )

    if search_cfg["method"] == "random":
        rng = random.Random(seed)
        rng.shuffle(trials)
    trials = trials[: int(search_cfg["max_trials"])]
    for index, trial in enumerate(trials, start=1):
        trial["trial"] = index
    return trials


def search_sort_value(metrics: dict[str, float], selection_metric: str) -> float:
    value = metric_value(metrics, selection_metric)
    return -value if selection_metric == "r2" else value


def ranked_search_results(candidate_results: list[dict[str, Any]], selection_metric: str) -> list[dict[str, Any]]:
    return sorted(candidate_results, key=lambda item: search_sort_value(item["metrics"], selection_metric))


def optimization_trial_rows(candidate_results: list[dict[str, Any]], selection_metric: str) -> list[dict[str, Any]]:
    rows = []
    for item in candidate_results:
        metrics = item["metrics"]
        rows.append(
            {
                "trial": item["trial"],
                "model_name": item["model_name"],
                "model_params": json.dumps(item["model_params"], sort_keys=True, default=str),
                "selection_metric": selection_metric,
                "selection_value": metric_value(metrics, selection_metric),
                "mae": metrics.get("mae"),
                "rmse": metrics.get("rmse"),
                "r2": metrics.get("r2"),
                "status": "completed",
            }
        )
    return rows
