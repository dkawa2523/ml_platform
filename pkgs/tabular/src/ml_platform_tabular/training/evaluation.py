from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Any

from ml_platform_core.io import write_json

from .artifacts import (
    CandidateResult,
    EvaluationResult,
    LEADERBOARD_REPORT_SCHEMA_VERSION,
)
from .best_model_artifacts import write_best_model_artifacts
from .leaderboard_artifacts import build_leaderboard_rows, write_leaderboard_artifacts
from .output_maps import evaluation_artifacts, evaluation_tables
from .prediction_artifacts import write_evaluation_diagnostics
from .ranking import ranked_results


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
    for name in ("CLEARML_TASK_ID", "TRAINS_TASK_ID", "TASK_ID"):
        value = os.environ.get(name)
        if value:
            return value
    return None


def evaluate_model_candidates(
    cfg: dict[str, Any],
    model_results: list[CandidateResult],
    ensemble_results: list[CandidateResult] | CandidateResult | None,
    pipeline_dir: Path,
    selection_metric: str,
) -> EvaluationResult:
    stage_dir = pipeline_dir / "evaluate_models"
    stage_dir.mkdir(parents=True, exist_ok=True)
    ensemble_items = _ensemble_items(ensemble_results)
    if not model_results and not ensemble_items:
        raise ValueError("evaluate_models requires at least one model or ensemble candidate.")
    ranked, best, _, _, best_ensemble = _rank_candidates(
        model_results,
        ensemble_items,
        selection_metric,
    )
    task_id = cfg.get("runtime", {}).get("clearml_task_id") or _runtime_task_id()
    version = _code_version()

    leaderboard_rows = build_leaderboard_rows(ranked, selection_metric)
    leaderboard_outputs = write_leaderboard_artifacts(
        leaderboard_rows=leaderboard_rows,
        stage_dir=stage_dir,
    )
    evaluation_predictions_path, diagnostic_tables, diagnostic_plots = write_evaluation_diagnostics(best, stage_dir)
    best_outputs = write_best_model_artifacts(
        best=best,
        best_ensemble=best_ensemble,
        selection_metric=selection_metric,
        stage_dir=stage_dir,
        task_id=task_id,
        code_version=version,
    )
    summary = _evaluation_summary(
        best_outputs=best_outputs,
        model_results=model_results,
        ensemble_items=ensemble_items,
        selection_metric=selection_metric,
        task_id=task_id,
        code_version=version,
    )
    metrics_path = write_json({**best.metrics, **summary}, stage_dir / "metrics.json")
    artifacts = evaluation_artifacts(best_outputs, metrics_path)
    tables = evaluation_tables(leaderboard_outputs, evaluation_predictions_path)
    tables.update(diagnostic_tables)
    return EvaluationResult(
        best=best,
        metrics=dict(best.metrics),
        summary=summary,
        artifacts=artifacts,
        tables=tables,
        plots={**leaderboard_outputs.plots, **diagnostic_plots},
    )


def _evaluation_summary(
    *,
    best_outputs,
    model_results: list[CandidateResult],
    ensemble_items: list[CandidateResult],
    selection_metric: str,
    task_id: str | None,
    code_version: str,
) -> dict[str, Any]:
    return {
        "report_schema_version": LEADERBOARD_REPORT_SCHEMA_VERSION,
        "code_version": code_version,
        "source_task_id": task_id,
        "best_model": best_outputs.best_model,
        "best_ensemble": best_outputs.best_ensemble,
        "selection_metric": selection_metric,
        "candidate_count": len(model_results),
        "ensemble_enabled": bool(ensemble_items),
        "ensemble_count": len(ensemble_items),
    }


def _ensemble_items(
    ensemble_results: list[CandidateResult] | CandidateResult | None,
) -> list[CandidateResult]:
    if ensemble_results is None:
        return []
    if isinstance(ensemble_results, CandidateResult):
        return list(ensemble_results.ensemble_results or [ensemble_results])
    return list(ensemble_results)


def _rank_candidates(
    model_results: list[CandidateResult],
    ensemble_items: list[CandidateResult],
    selection_metric: str,
) -> tuple[
    list[CandidateResult],
    CandidateResult,
    CandidateResult | None,
    list[CandidateResult],
    CandidateResult | None,
]:
    ranked = ranked_results([*model_results, *ensemble_items], selection_metric)
    ranked_models = ranked_results(model_results, selection_metric) if model_results else []
    ranked_ensembles = ranked_results(ensemble_items, selection_metric) if ensemble_items else []
    return (
        ranked,
        ranked[0],
        ranked_models[0] if ranked_models else None,
        ranked_ensembles,
        ranked_ensembles[0] if ranked_ensembles else None,
    )
