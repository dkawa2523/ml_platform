from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ml_platform_core.io import write_json

from ..selection import metric_value
from .artifacts import LEADERBOARD_REPORT_SCHEMA_VERSION, CandidateResult, candidate_selector


@dataclass(frozen=True)
class BestModelArtifacts:
    artifacts: dict[str, Path]
    best_model: dict[str, Any]
    best_ensemble: dict[str, Any] | None


def best_model_payload(
    best: CandidateResult,
    selection_metric: str,
    *,
    final_metrics: dict[str, float],
    task_id: str | None,
    code_version: str,
) -> dict[str, Any]:
    return {
        "report_schema_version": LEADERBOARD_REPORT_SCHEMA_VERSION,
        "code_version": code_version,
        "source_task_id": task_id,
        "model_name": best.model_name,
        "artifact_kind": best.artifact_kind,
        "stage": best.stage,
        "selection_metric": selection_metric,
        "selection_value": metric_value(best.metrics, selection_metric),
        "selection_scope": "selection_holdout",
        "selection_metrics": best.metrics,
        "metric_scope": "test_holdout",
        "metrics": final_metrics,
        "model_params": best.model_params,
        "ensemble_method": best.ensemble_method,
        "model_selector": "best",
        "candidate_selector": candidate_selector(best),
        "recommended_inference_settings": {
            "Model/source_type": "task_id",
            "Model/source_task_id": task_id or "<training_or_evaluate_task_id>",
            "Model/model_selector": "best",
        },
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
        "selection_scope": "selection_holdout",
        "selection_metrics": best_ensemble.metrics,
        "model_params": best_ensemble.model_params,
    }


def write_best_model_artifacts(
    *,
    best: CandidateResult,
    best_ensemble: CandidateResult | None,
    selection_metric: str,
    stage_dir: Path,
    task_id: str | None,
    code_version: str,
    final_metrics: dict[str, float],
) -> BestModelArtifacts:
    best_model_path = stage_dir / "best_model.joblib"
    model_info_path = stage_dir / "model_info.json"
    shutil.copy2(best.artifacts["model"], best_model_path)
    shutil.copy2(best.artifacts["model_info"], model_info_path)
    best_payload = best_model_payload(
        best,
        selection_metric,
        final_metrics=final_metrics,
        task_id=task_id,
        code_version=code_version,
    )
    best_model_json_path = write_json(best_payload, stage_dir / "best_model.json")
    return BestModelArtifacts(
        artifacts={
            "best_model": best_model_path,
            "model_info": model_info_path,
            "best_model_json": best_model_json_path,
        },
        best_model=best_payload,
        best_ensemble=best_ensemble_payload(best_ensemble, selection_metric),
    )
