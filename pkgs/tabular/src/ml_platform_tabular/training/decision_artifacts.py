from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from ml_platform_core.artifacts import utc_timestamp
from ml_platform_core.io import write_json, write_table

from ..ensemble import metric_value
from .artifacts import (
    CandidateResult,
    LEADERBOARD_REPORT_SCHEMA_VERSION,
    candidate_ref_payload,
)
from .summary import (
    _best_vs_ensemble_rows,
    _decision_summary_markdown,
    _decision_summary_payload,
    _summary_row,
)


@dataclass(frozen=True)
class DecisionArtifacts:
    artifacts: dict[str, Path]
    tables: dict[str, Path]
    metrics: dict[str, Any]
    report: dict[str, Any]


def _evaluation_metadata(
    model_results: list[CandidateResult],
    ensemble_items: list[CandidateResult],
    selection_metric: str,
) -> dict[str, Any]:
    return {
        "stage": "evaluate_models",
        "candidate_count": len(model_results),
        "ensemble_enabled": bool(ensemble_items),
        "ensemble_count": len(ensemble_items),
        "selection_metric": selection_metric,
    }


def _model_refs_payload(
    *,
    model_results: list[CandidateResult],
    ensemble_items: list[CandidateResult],
    best_ensemble: CandidateResult | None,
    selection_metric: str,
) -> dict[str, Any]:
    return {
        **_evaluation_metadata(model_results, ensemble_items, selection_metric),
        "models": [candidate_ref_payload(item) for item in model_results],
        "ensembles": [candidate_ref_payload(item) for item in ensemble_items],
        "ensemble": candidate_ref_payload(best_ensemble) if best_ensemble is not None else None,
    }


def _metrics_payload(
    *,
    model_results: list[CandidateResult],
    ensemble_items: list[CandidateResult],
    metrics_by_candidate: dict[str, dict[str, Any]],
    selection_metric: str,
) -> dict[str, Any]:
    return {
        **_evaluation_metadata(model_results, ensemble_items, selection_metric),
        "metrics_by_candidate": metrics_by_candidate,
    }


def _write_metrics_payload(payload: dict[str, Any], stage_dir: Path) -> Path:
    return write_json(payload, stage_dir / "metrics_by_candidate.json")


def _summary_rows(
    best: CandidateResult,
    best_single: CandidateResult | None,
    best_ensemble: CandidateResult | None,
    selection_metric: str,
) -> list[dict[str, Any]]:
    return [
        _summary_row("best_overall", best, selection_metric),
        _summary_row("best_single_model", best_single, selection_metric),
        _summary_row("best_ensemble", best_ensemble, selection_metric),
    ]


def _write_summary_table(summary_rows: list[dict[str, Any]], stage_dir: Path) -> Path:
    return write_table(pd.DataFrame(summary_rows), stage_dir / "evaluation_summary.csv")


def _write_best_vs_ensemble_table(best_vs_ensemble_rows: list[dict[str, Any]], stage_dir: Path) -> Path:
    return write_table(
        pd.DataFrame(best_vs_ensemble_rows),
        stage_dir / "best_vs_ensemble_summary.csv",
    )


def _ensemble_metrics(ranked_ensembles: list[CandidateResult], selection_metric: str) -> dict[str, dict[str, Any]]:
    return {
        item.model_name: {
            "ensemble_method": item.ensemble_method,
            "metrics": item.metrics,
            "selection_value": metric_value(item.metrics, selection_metric),
        }
        for item in ranked_ensembles
    }


def _write_decision_summary(
    *,
    best: CandidateResult,
    best_single: CandidateResult | None,
    best_ensemble: CandidateResult | None,
    selection_metric: str,
    leaderboard_rows: list[dict[str, Any]],
    best_vs_ensemble_rows: list[dict[str, Any]],
    created_at: str,
    task_id: str | None,
    code_version: str,
    stage_dir: Path,
) -> tuple[dict[str, Any], Path, Path]:
    decision_summary = _decision_summary_payload(
        best=best,
        best_single=best_single,
        best_ensemble=best_ensemble,
        selection_metric=selection_metric,
        leaderboard_rows=leaderboard_rows,
        best_vs_ensemble_rows=best_vs_ensemble_rows,
        created_at=created_at,
        task_id=task_id,
        code_version=code_version,
    )
    decision_summary_md_path = stage_dir / "decision_summary.md"
    decision_summary_md_path.write_text(_decision_summary_markdown(decision_summary), encoding="utf-8")
    decision_summary_json_path = write_json(decision_summary, stage_dir / "decision_summary.json")
    return decision_summary, decision_summary_md_path, decision_summary_json_path


def _evaluation_report_payload(
    *,
    metadata: dict[str, Any],
    created_at: str,
    code_version: str,
    task_id: str | None,
    best_model_payload: dict[str, Any],
    best_single: CandidateResult | None,
    best_ensemble_payload: dict[str, Any] | None,
    ranked_ensembles: list[CandidateResult],
    leaderboard_rows: list[dict[str, Any]],
    model_refs_payload: dict[str, Any],
    metrics_by_candidate: dict[str, dict[str, Any]],
    evaluation_predictions_path: Path | None,
    leaderboard_topk_path: Path,
    best_vs_ensemble_summary_path: Path,
    decision_summary_md_path: Path,
    decision_summary_json_path: Path,
) -> dict[str, Any]:
    selection_metric = metadata["selection_metric"]
    return {
        "report_schema_version": LEADERBOARD_REPORT_SCHEMA_VERSION,
        "created_at": created_at,
        "code_version": code_version,
        "source_task_id": task_id,
        **metadata,
        "best_model": best_model_payload,
        "best_single_model": _summary_row("best_single_model", best_single, selection_metric),
        "best_ensemble": best_ensemble_payload,
        "ranked_models": leaderboard_rows,
        "ensemble_metrics": _ensemble_metrics(ranked_ensembles, selection_metric),
        "model_refs": model_refs_payload,
        "metrics_by_candidate": metrics_by_candidate,
        "evaluation_predictions": str(evaluation_predictions_path) if evaluation_predictions_path else None,
        "leaderboard_topk": str(leaderboard_topk_path),
        "best_vs_ensemble_summary": str(best_vs_ensemble_summary_path),
        "decision_summary": str(decision_summary_md_path),
        "decision_summary_json": str(decision_summary_json_path),
    }


def _metrics_file_payload(
    *,
    best: CandidateResult,
    metadata: dict[str, Any],
    best_model_payload: dict[str, Any],
    best_ensemble_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        **best.metrics,
        "report_schema_version": LEADERBOARD_REPORT_SCHEMA_VERSION,
        "best_model": best_model_payload,
        "best_ensemble": best_ensemble_payload,
        "selection_metric": metadata["selection_metric"],
        "candidate_count": metadata["candidate_count"],
        "ensemble_enabled": metadata["ensemble_enabled"],
        "ensemble_count": metadata["ensemble_count"],
    }


def write_decision_artifacts(
    *,
    stage_dir: Path,
    model_results: list[CandidateResult],
    ensemble_items: list[CandidateResult],
    ranked_ensembles: list[CandidateResult],
    best: CandidateResult,
    best_single: CandidateResult | None,
    best_ensemble: CandidateResult | None,
    best_model_payload: dict[str, Any],
    best_ensemble_payload: dict[str, Any] | None,
    leaderboard_rows: list[dict[str, Any]],
    metrics_by_candidate: dict[str, dict[str, Any]],
    selection_metric: str,
    task_id: str | None,
    code_version: str,
    evaluation_predictions_path: Path | None,
    leaderboard_topk_path: Path,
) -> DecisionArtifacts:
    metadata = _evaluation_metadata(model_results, ensemble_items, selection_metric)
    model_refs_payload = _model_refs_payload(
        model_results=model_results,
        ensemble_items=ensemble_items,
        best_ensemble=best_ensemble,
        selection_metric=selection_metric,
    )
    model_refs_path = write_json(model_refs_payload, stage_dir / "model_refs.json")
    metrics_by_candidate_payload = _metrics_payload(
        model_results=model_results,
        ensemble_items=ensemble_items,
        metrics_by_candidate=metrics_by_candidate,
        selection_metric=selection_metric,
    )
    metrics_by_candidate_path = _write_metrics_payload(metrics_by_candidate_payload, stage_dir)

    summary_rows = _summary_rows(best, best_single, best_ensemble, selection_metric)
    evaluation_summary_path = _write_summary_table(summary_rows, stage_dir)
    best_vs_ensemble_rows = _best_vs_ensemble_rows(best_single, best_ensemble)
    best_vs_ensemble_summary_path = _write_best_vs_ensemble_table(best_vs_ensemble_rows, stage_dir)
    created_at = utc_timestamp()
    _, decision_summary_md_path, decision_summary_json_path = _write_decision_summary(
        best=best,
        best_single=best_single,
        best_ensemble=best_ensemble,
        selection_metric=selection_metric,
        leaderboard_rows=leaderboard_rows,
        best_vs_ensemble_rows=best_vs_ensemble_rows,
        created_at=created_at,
        task_id=task_id,
        code_version=code_version,
        stage_dir=stage_dir,
    )
    report = _evaluation_report_payload(
        metadata=metadata,
        created_at=created_at,
        code_version=code_version,
        task_id=task_id,
        best_model_payload=best_model_payload,
        best_single=best_single,
        best_ensemble_payload=best_ensemble_payload,
        ranked_ensembles=ranked_ensembles,
        leaderboard_rows=leaderboard_rows,
        model_refs_payload=model_refs_payload,
        metrics_by_candidate=metrics_by_candidate,
        evaluation_predictions_path=evaluation_predictions_path,
        leaderboard_topk_path=leaderboard_topk_path,
        best_vs_ensemble_summary_path=best_vs_ensemble_summary_path,
        decision_summary_md_path=decision_summary_md_path,
        decision_summary_json_path=decision_summary_json_path,
    )
    evaluation_report_path = write_json(report, stage_dir / "evaluation_report.json")
    metrics_payload = _metrics_file_payload(
        best=best,
        metadata=metadata,
        best_model_payload=best_model_payload,
        best_ensemble_payload=best_ensemble_payload,
    )
    metrics_path = write_json(metrics_payload, stage_dir / "metrics.json")
    return DecisionArtifacts(
        artifacts={
            "model_refs": model_refs_path,
            "metrics_by_candidate": metrics_by_candidate_path,
            "evaluation_report": evaluation_report_path,
            "decision_summary": decision_summary_md_path,
            "decision_summary_json": decision_summary_json_path,
            "metrics": metrics_path,
        },
        tables={
            "evaluation_summary": evaluation_summary_path,
            "best_vs_ensemble_summary": best_vs_ensemble_summary_path,
        },
        metrics=metrics_payload,
        report=report,
    )
