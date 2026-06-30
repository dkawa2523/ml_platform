from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifacts import (
    CandidateResult,
    EvaluationResult,
    _code_version,
    _metrics_by_candidate_payload,
    _runtime_task_id,
)
from .best_model_artifacts import BestModelArtifacts, write_best_model_artifacts
from .decision_artifacts import DecisionArtifacts, write_decision_artifacts
from .leaderboard_artifacts import LeaderboardArtifacts, build_leaderboard_rows, write_leaderboard_artifacts
from .prediction_artifacts import write_candidate_predictions, write_evaluation_predictions
from .ranking import ranked_results


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
    ranked, best, best_single, ranked_ensembles, best_ensemble = _rank_candidates(
        model_results,
        ensemble_items,
        selection_metric,
    )
    metrics_by_candidate = _metrics_by_candidate_payload(ranked, selection_metric)
    task_id = cfg.get("runtime", {}).get("clearml_task_id") or _runtime_task_id()
    code_version = _code_version()

    leaderboard_rows = build_leaderboard_rows(ranked, selection_metric)
    leaderboard_outputs = write_leaderboard_artifacts(
        leaderboard_rows=leaderboard_rows,
        metrics_by_candidate=metrics_by_candidate,
        selection_metric=selection_metric,
        stage_dir=stage_dir,
    )
    evaluation_predictions_path, prediction_plots = write_evaluation_predictions(best, stage_dir)
    candidate_predictions_path, candidate_plots = write_candidate_predictions(ranked, stage_dir)
    prediction_plots.update(candidate_plots)
    best_outputs = write_best_model_artifacts(
        best=best,
        best_ensemble=best_ensemble,
        selection_metric=selection_metric,
        stage_dir=stage_dir,
    )
    decision_outputs = write_decision_artifacts(
        stage_dir=stage_dir,
        model_results=model_results,
        ensemble_items=ensemble_items,
        ranked_ensembles=ranked_ensembles,
        best=best,
        best_single=best_single,
        best_ensemble=best_ensemble,
        best_model_payload=best_outputs.best_model,
        best_ensemble_payload=best_outputs.best_ensemble,
        leaderboard_rows=leaderboard_rows,
        metrics_by_candidate=metrics_by_candidate,
        selection_metric=selection_metric,
        task_id=task_id,
        code_version=code_version,
        evaluation_predictions_path=evaluation_predictions_path,
        leaderboard_topk_path=leaderboard_outputs.tables["leaderboard_topk"],
    )
    artifacts = _evaluation_artifacts(
        decision_outputs,
        best_outputs,
        evaluation_predictions_path,
        candidate_predictions_path,
    )
    tables = _evaluation_tables(
        leaderboard_outputs,
        decision_outputs,
        evaluation_predictions_path,
        candidate_predictions_path,
    )
    plots = {**leaderboard_outputs.plots, **prediction_plots}
    return EvaluationResult(
        stage="evaluate_models",
        stage_dir=stage_dir,
        best=best,
        metrics=decision_outputs.metrics,
        report=decision_outputs.report,
        artifacts=artifacts,
        tables=tables,
        plots=plots,
    )


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


def _evaluation_artifacts(
    decision_outputs: DecisionArtifacts,
    best_outputs: BestModelArtifacts,
    evaluation_predictions_path: Path | None,
    candidate_predictions_path: Path | None,
) -> dict[str, Path]:
    artifacts = {**decision_outputs.artifacts, **best_outputs.artifacts}
    _add_optional_path(artifacts, "evaluation_predictions", evaluation_predictions_path)
    _add_optional_path(artifacts, "candidate_predictions", candidate_predictions_path)
    return artifacts


def _evaluation_tables(
    leaderboard_outputs: LeaderboardArtifacts,
    decision_outputs: DecisionArtifacts,
    evaluation_predictions_path: Path | None,
    candidate_predictions_path: Path | None,
) -> dict[str, Path]:
    tables = {**leaderboard_outputs.tables, **decision_outputs.tables}
    _add_optional_path(tables, "evaluation_predictions", evaluation_predictions_path)
    _add_optional_path(tables, "candidate_predictions", candidate_predictions_path)
    return tables


def _add_optional_path(mapping: dict[str, Path], key: str, path: Path | None) -> None:
    if path is not None:
        mapping[key] = path
