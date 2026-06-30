from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pandas as pd

from ..ensemble import metric_value
from ..metrics import DEFAULT_REGRESSION_METRICS


LEADERBOARD_METRICS = ["rmse", "mae", "r2"]
LEADERBOARD_TOP_K = 5
LEADERBOARD_REPORT_SCHEMA_VERSION = "leaderboard_dashboard_v2"
SELECTION_METRICS = {"rmse", "mae", "r2"}


class FeatureTransformer(Protocol):
    def transform(self, X: pd.DataFrame) -> object: ...


class Predictor(Protocol):
    def predict(self, X: pd.DataFrame) -> np.ndarray: ...


FeatureFrame = pd.DataFrame
TargetVector = pd.Series
PredictionArray = np.ndarray


@dataclass(frozen=True)
class EnsembleMember:
    rank: int
    model_name: str
    model_params: dict[str, Any]
    stage: str
    artifact_path: str
    weight: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "model_name": self.model_name,
            "model_params": dict(self.model_params),
            "stage": self.stage,
            "artifact_path": self.artifact_path,
            "weight": self.weight,
        }


def ensemble_member_rows(members: list[EnsembleMember]) -> list[dict[str, Any]]:
    return [member.to_dict() for member in members]


@dataclass(frozen=True)
class PreprocessResult:
    stage: str
    stage_dir: Path
    transformer: FeatureTransformer
    feature_columns: list[str]
    target_column: str
    feature_preset: str
    feature_config: dict[str, Any]
    X_train: FeatureFrame
    X_valid: FeatureFrame
    y_train: TargetVector
    y_valid: TargetVector
    artifacts: dict[str, Path]
    tables: dict[str, Path]
    plots: dict[str, Path] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateResult:
    stage: str
    stage_dir: Path
    model_name: str
    model_params: dict[str, Any]
    artifact_kind: str
    estimator: Predictor
    predictions: PredictionArray | None
    metrics: dict[str, float]
    artifacts: dict[str, Path]
    tables: dict[str, Path]
    plots: dict[str, Path] = field(default_factory=dict)
    ensemble_method: str | None = None
    artifact_name: str = "model"
    selected_base_models: list[EnsembleMember] = field(default_factory=list)
    ensemble_results: list["CandidateResult"] = field(default_factory=list)
    best_ensemble: "CandidateResult | None" = None
    ensemble_refs: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class CandidateTrainingResult:
    stage: str
    stage_dir: Path
    model_results: list[CandidateResult]
    artifacts: dict[str, Path] = field(default_factory=dict)


def candidate_selector(item: CandidateResult) -> str:
    if item.artifact_kind == "ensemble" and item.ensemble_method:
        return f"ensemble:{item.ensemble_method}"
    return item.model_name


@dataclass(frozen=True)
class EvaluationResult:
    stage: str
    stage_dir: Path
    best: CandidateResult
    metrics: dict[str, Any]
    report: dict[str, Any]
    artifacts: dict[str, Path]
    tables: dict[str, Path]
    plots: dict[str, Path]


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


def metric_name(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def required_metric_names(metric_names: Any, selection_metric: str) -> list[str]:
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
            names.append(metric_name(name))
    return names


def _metric_names_from_iterable(metric_names: Any) -> list[str]:
    return [metric_name(name) for name in metric_names]


def _with_required_metrics(names: list[str], selection_metric: str) -> list[str]:
    for name in [*LEADERBOARD_METRICS, selection_metric]:
        if name not in names:
            names.append(name)
    return names


def safe_name(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value)
    return safe or "model"


def candidate_ref_payload(item: CandidateResult) -> dict[str, Any]:
    payload = {
        "stage": item.stage,
        "model_name": item.model_name,
        "ensemble_method": item.ensemble_method,
        "model_params": item.model_params,
        "artifact_kind": item.artifact_kind,
        "model": str(item.artifacts["model"]),
        "model_info": str(item.artifacts["model_info"]),
        "metrics": str(item.artifacts["metrics"]),
    }
    if item.tables.get("validation_predictions"):
        payload["validation_predictions"] = str(item.tables["validation_predictions"])
    if item.tables.get("ensemble_predictions"):
        payload["ensemble_predictions"] = str(item.tables["ensemble_predictions"])
    payload = {key: value for key, value in payload.items() if value is not None}
    return payload


def _metrics_by_candidate_payload(
    results: list[CandidateResult],
    selection_metric: str,
) -> dict[str, dict[str, Any]]:
    return {
        item.model_name: {
            "stage": item.stage,
            "artifact_kind": item.artifact_kind,
            "ensemble_method": item.ensemble_method,
            "selection_metric": selection_metric,
            "selection_value": metric_value(item.metrics, selection_metric),
            "metrics": item.metrics,
        }
        for item in results
    }
