from __future__ import annotations

import json
from typing import Any

from ..ensemble import metric_value
from .artifacts import LEADERBOARD_METRICS


def _selection_sort_value(metrics: dict[str, float], selection_metric: str) -> float:
    value = metric_value(metrics, selection_metric)
    return -value if selection_metric == "r2" else value


def _ranked_results(results: list[dict[str, Any]], selection_metric: str) -> list[dict[str, Any]]:
    return sorted(results, key=lambda item: _selection_sort_value(item["metrics"], selection_metric))


def _selector_for_item(item: dict[str, Any]) -> str:
    if item["artifact_kind"] == "ensemble" and item.get("ensemble_method"):
        return f"ensemble:{item['ensemble_method']}"
    return str(item["model_name"])


def _leaderboard_rows(results: list[dict[str, Any]], selection_metric: str) -> list[dict[str, Any]]:
    rows = []
    for rank, item in enumerate(results, start=1):
        artifact_kind = item["artifact_kind"]
        ensemble_method = item.get("ensemble_method")
        infer_target = (
            f"ensemble:{ensemble_method}" if artifact_kind == "ensemble" and ensemble_method else item["model_name"]
        )
        row = {
            "rank": rank,
            "model_name": item["model_name"],
            "artifact_kind": artifact_kind,
            "ensemble_method": ensemble_method,
            "stage": item["stage"],
            "selection_metric": selection_metric,
            "ref_kind": "task_artifact",
            "infer_selector": "Model/model_selector",
            "infer_target": infer_target,
            "model_params": json.dumps(item["model_params"], sort_keys=True, default=str),
            "artifact_name": item.get("artifact_name", "model"),
            "artifact_path": str(item["artifacts"]["model"]),
        }
        for name in LEADERBOARD_METRICS:
            row[name] = item["metrics"].get(name)
        rows.append(row)
    return rows
