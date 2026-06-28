from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..ensemble import metric_value
from ..metrics import DEFAULT_REGRESSION_METRICS


LEADERBOARD_METRICS = ["rmse", "mae", "r2"]
LEADERBOARD_TOP_K = 5
LEADERBOARD_REPORT_SCHEMA_VERSION = "leaderboard_dashboard_v2"
SELECTION_METRICS = {"rmse", "mae", "r2"}


@dataclass(frozen=True)
class EvaluationResult:
    stage: str
    stage_dir: Path
    best: dict[str, Any]
    metrics: dict[str, Any]
    report: dict[str, Any]
    artifacts: dict[str, Path]
    tables: dict[str, Path]
    plots: dict[str, Path]

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "stage_dir": self.stage_dir,
            "best": self.best,
            "metrics": self.metrics,
            "report": self.report,
            "artifacts": self.artifacts,
            "tables": self.tables,
            "plots": self.plots,
        }


def _path_map(mapping: dict[str, Path]) -> dict[str, str]:
    return {name: str(path) for name, path in mapping.items()}


def _code_version() -> str:
    try:
        root = Path(__file__).resolve().parents[5]
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return "unknown"
    version = completed.stdout.strip()
    return version or "unknown"


def _runtime_task_id() -> str | None:
    import os

    for name in ("CLEARML_TASK_ID", "TRAINS_TASK_ID", "TASK_ID"):
        value = os.environ.get(name)
        if value:
            return value
    return None


def _metric_name(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _metric_names(metric_names: Any, selection_metric: str) -> list[str] | str | None:
    if metric_names is None:
        names = list(DEFAULT_REGRESSION_METRICS)
    elif isinstance(metric_names, str):
        names = [_metric_name(name) for name in metric_names.split(",") if name.strip()]
    else:
        names = [_metric_name(name) for name in metric_names]
    for name in [*LEADERBOARD_METRICS, selection_metric]:
        if name not in names:
            names.append(name)
    return names


def _safe_name(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value)
    return safe or "model"


def _model_ref_payload(item: dict[str, Any]) -> dict[str, Any]:
    tables = item.get("tables", {})
    payload = {
        "stage": item["stage"],
        "model_name": item["model_name"],
        "ensemble_method": item.get("ensemble_method"),
        "model_params": item["model_params"],
        "artifact_kind": item["artifact_kind"],
        "model": str(item["artifacts"]["model"]),
        "model_info": str(item["artifacts"]["model_info"]),
        "metrics": str(item["artifacts"]["metrics"]),
    }
    if tables.get("validation_predictions"):
        payload["validation_predictions"] = str(tables["validation_predictions"])
    if tables.get("ensemble_predictions"):
        payload["ensemble_predictions"] = str(tables["ensemble_predictions"])
    payload = {key: value for key, value in payload.items() if value is not None}
    return payload


def _metrics_by_model_payload(
    results: list[dict[str, Any]],
    selection_metric: str,
) -> dict[str, dict[str, Any]]:
    return {
        item["model_name"]: {
            "stage": item["stage"],
            "artifact_kind": item["artifact_kind"],
            "ensemble_method": item.get("ensemble_method"),
            "selection_metric": selection_metric,
            "selection_value": metric_value(item["metrics"], selection_metric),
            "metrics": item["metrics"],
        }
        for item in results
    }
