from __future__ import annotations

from dataclasses import dataclass
import shutil
from pathlib import Path
from typing import Any

from ml_platform_core.io import write_json

from ..ensemble import metric_value
from .artifacts import CandidateResult


@dataclass(frozen=True)
class BestModelArtifacts:
    artifacts: dict[str, Path]
    best_model: dict[str, Any]
    best_ensemble: dict[str, Any] | None


def best_model_payload(best: CandidateResult, selection_metric: str, best_model_path: Path) -> dict[str, Any]:
    return {
        "model_name": best.model_name,
        "artifact_kind": best.artifact_kind,
        "stage": best.stage,
        "selection_metric": selection_metric,
        "selection_value": metric_value(best.metrics, selection_metric),
        "metrics": best.metrics,
        "model_params": best.model_params,
        "ensemble_method": best.ensemble_method,
        "source_artifact": str(best.artifacts["model"]),
        "best_model_artifact": str(best_model_path),
    }


def best_ensemble_payload(best_ensemble: CandidateResult | None, selection_metric: str) -> dict[str, Any] | None:
    if best_ensemble is None:
        return None
    return {
        "model_name": best_ensemble.model_name,
        "artifact_kind": best_ensemble.artifact_kind,
        "ensemble_method": best_ensemble.ensemble_method,
        "stage": best_ensemble.stage,
        "selection_metric": selection_metric,
        "selection_value": metric_value(best_ensemble.metrics, selection_metric),
        "metrics": best_ensemble.metrics,
        "model_params": best_ensemble.model_params,
        "source_artifact": str(best_ensemble.artifacts["model"]),
    }


def write_best_model_artifacts(
    *,
    best: CandidateResult,
    best_ensemble: CandidateResult | None,
    selection_metric: str,
    stage_dir: Path,
) -> BestModelArtifacts:
    best_model_path = stage_dir / "best_model.joblib"
    shutil.copy2(best.artifacts["model"], best_model_path)
    best_payload = best_model_payload(best, selection_metric, best_model_path)
    best_model_json_path = write_json(best_payload, stage_dir / "best_model.json")
    return BestModelArtifacts(
        artifacts={
            "best_model": best_model_path,
            "best_model_json": best_model_json_path,
        },
        best_model=best_payload,
        best_ensemble=best_ensemble_payload(best_ensemble, selection_metric),
    )
