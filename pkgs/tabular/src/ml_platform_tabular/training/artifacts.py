from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from ..features import FeatureTransformer
from ..models import Predictor
from ..selection import REPORT_METRICS


LEADERBOARD_METRICS = list(REPORT_METRICS)
LEADERBOARD_TOP_K = 5
LEADERBOARD_REPORT_SCHEMA_VERSION = "leaderboard_dashboard_v2"


def safe_name(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value)
    return safe or "model"


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
    transformer: FeatureTransformer
    feature_columns: list[str]
    target_column: str
    target_names: list[str]
    coordinate_columns: list[str]
    id_columns: list[str]
    feature_preset: str
    feature_config: dict[str, Any]
    X_train: pd.DataFrame
    X_valid: pd.DataFrame
    y_train: pd.Series
    y_valid: pd.Series
    artifacts: dict[str, Path]
    tables: dict[str, Path]
    plots: dict[str, Path] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateResult:
    stage: str
    model_name: str
    model_params: dict[str, Any]
    artifact_kind: str
    estimator: Predictor
    metrics: dict[str, float]
    artifacts: dict[str, Path]
    tables: dict[str, Path]
    plots: dict[str, Path] = field(default_factory=dict)
    ensemble_method: str | None = None
    artifact_name: str = "model"
    selected_base_models: list[EnsembleMember] = field(default_factory=list)
    ensemble_results: list["CandidateResult"] = field(default_factory=list)


def candidate_selector(item: CandidateResult) -> str:
    if item.artifact_kind == "ensemble" and item.ensemble_method:
        return f"ensemble:{item.ensemble_method}"
    return item.model_name


def candidate_ref_payload(item: CandidateResult) -> dict[str, Any]:
    payload = {
        "stage": item.stage,
        "model_name": item.model_name,
        "ensemble_method": item.ensemble_method,
        "model_params": item.model_params,
        "artifact_kind": item.artifact_kind,
        "model": _path_text(item.artifacts.get("model")),
        "model_info": _path_text(item.artifacts.get("model_info")),
        "metrics": _path_text(item.artifacts.get("metrics")),
        "validation_predictions": _path_text(item.tables.get("validation_predictions")),
        "ensemble_predictions": _path_text(item.tables.get("ensemble_predictions")),
    }
    return {key: value for key, value in payload.items() if value is not None}


def _path_text(value: object | None) -> str | None:
    return str(value) if value is not None else None


@dataclass(frozen=True)
class EvaluationResult:
    best: CandidateResult
    metrics: dict[str, float]
    summary: dict[str, Any]
    artifacts: dict[str, Path]
    tables: dict[str, Path]
    plots: dict[str, Path]
