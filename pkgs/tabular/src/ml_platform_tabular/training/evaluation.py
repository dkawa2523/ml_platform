from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from ml_platform_core.io import write_json, write_table

from ..ensemble import metric_value
from ..plotting import (
    topk_candidate_predictions,
    write_candidate_prediction_vs_actual_plot,
    write_candidate_residual_histogram,
    write_candidate_residual_vs_predicted_plot,
    write_leaderboard_metric_panel,
    write_leaderboard_pareto_plot,
    write_leaderboard_table,
    write_metrics_bar_plot,
    write_metrics_by_candidate_table,
    write_prediction_vs_actual_plot,
    write_residual_histogram,
    write_residual_vs_predicted_plot,
)
from .artifacts import (
    LEADERBOARD_REPORT_SCHEMA_VERSION,
    LEADERBOARD_TOP_K,
    EvaluationResult,
    _code_version,
    _metrics_by_model_payload,
    _model_ref_payload,
    _runtime_task_id,
)
from .ranking import _leaderboard_rows, _ranked_results
from .recommendation import _recommendation_payload
from .summary import (
    _best_vs_ensemble_rows,
    _decision_summary_markdown,
    _decision_summary_payload,
    _summary_row,
)


def _prediction_table_path(item: dict[str, Any]) -> Path | None:
    tables = item.get("tables", {})
    path = tables.get("validation_predictions") or tables.get("ensemble_predictions")
    return Path(path) if path else None


def _write_evaluation_predictions(best: dict[str, Any], stage_dir: Path) -> tuple[Path | None, dict[str, Path]]:
    source = _prediction_table_path(best)
    if source is None or not source.exists():
        return None, {}
    destination = stage_dir / "evaluation_predictions.csv"
    if source != destination:
        shutil.copy2(source, destination)
    frame = pd.read_csv(destination)
    if {"actual", "prediction"} <= set(frame.columns):
        scatter = write_prediction_vs_actual_plot(
            frame["actual"],
            frame["prediction"],
            stage_dir / "best_prediction_vs_actual.png",
            title="Best prediction vs actual",
        )
        residual = write_residual_histogram(
            frame["actual"],
            frame["prediction"],
            stage_dir / "best_residual_histogram.png",
            title="Best residual histogram",
        )
        residual_vs_predicted = write_residual_vs_predicted_plot(
            frame["actual"],
            frame["prediction"],
            stage_dir / "best_residual_vs_predicted.png",
            title="Best residuals vs predicted",
        )
        plots = {
            "best_prediction_vs_actual": scatter,
            "best_residual_histogram": residual,
            "best_residual_vs_predicted": residual_vs_predicted,
        }
    else:
        plots = {}
    return destination, plots


def _write_candidate_predictions(
    candidates: list[dict[str, Any]], stage_dir: Path
) -> tuple[Path | None, dict[str, Path]]:
    frames = []
    for rank, item in enumerate(candidates, start=1):
        source = _prediction_table_path(item)
        if source is None or not source.exists():
            continue
        frame = pd.read_csv(source)
        if not {"actual", "prediction"} <= set(frame.columns):
            continue
        candidate_name = str(item["model_name"])
        frame = frame.copy()
        frame.insert(0, "candidate_rank", rank)
        frame.insert(1, "candidate_name", candidate_name)
        frame.insert(2, "artifact_kind", item["artifact_kind"])
        frame.insert(3, "ensemble_method", item.get("ensemble_method"))
        frame.insert(4, "source_stage", item["stage"])
        if "residual" not in frame.columns:
            frame["residual"] = pd.to_numeric(frame["actual"], errors="coerce") - pd.to_numeric(
                frame["prediction"], errors="coerce"
            )
        if "abs_error" not in frame.columns:
            frame["abs_error"] = frame["residual"].abs()
        frames.append(frame)
    if not frames:
        return None, {}
    combined = pd.concat(frames, ignore_index=True)
    predictions_path = write_table(combined, stage_dir / "candidate_predictions.csv")
    topk = topk_candidate_predictions(combined, top_k=LEADERBOARD_TOP_K)
    plots = {
        "topk_prediction_vs_actual": write_candidate_prediction_vs_actual_plot(
            topk,
            stage_dir / "topk_prediction_vs_actual.png",
            title=f"Top-{LEADERBOARD_TOP_K} prediction vs actual",
        ),
        "topk_residual_histogram": write_candidate_residual_histogram(
            topk,
            stage_dir / "topk_residual_histogram.png",
            title=f"Top-{LEADERBOARD_TOP_K} residual histogram",
        ),
        "topk_residual_vs_predicted": write_candidate_residual_vs_predicted_plot(
            topk,
            stage_dir / "topk_residual_vs_predicted.png",
            title=f"Top-{LEADERBOARD_TOP_K} residuals vs predicted",
        ),
    }
    return predictions_path, plots


def evaluate_model_candidates(
    cfg: dict[str, Any],
    model_results: list[dict[str, Any]],
    ensemble_results: list[dict[str, Any]] | dict[str, Any] | None,
    pipeline_dir: Path,
    selection_metric: str,
) -> EvaluationResult:
    stage_dir = pipeline_dir / "evaluate_models"
    stage_dir.mkdir(parents=True, exist_ok=True)
    if ensemble_results is None:
        ensemble_items: list[dict[str, Any]] = []
    elif isinstance(ensemble_results, dict) and "ensemble_results" in ensemble_results:
        ensemble_items = list(ensemble_results.get("ensemble_results") or [])
    elif isinstance(ensemble_results, dict):
        ensemble_items = [ensemble_results]
    else:
        ensemble_items = list(ensemble_results)
    candidates = [*model_results]
    candidates.extend(ensemble_items)
    ranked = _ranked_results(candidates, selection_metric)
    best = ranked[0]
    ranked_models = _ranked_results(model_results, selection_metric) if model_results else []
    best_single = ranked_models[0] if ranked_models else None
    ranked_ensembles = _ranked_results(ensemble_items, selection_metric) if ensemble_items else []
    best_ensemble = ranked_ensembles[0] if ranked_ensembles else None
    metrics_by_model = _metrics_by_model_payload(ranked, selection_metric)
    task_id = cfg.get("runtime", {}).get("clearml_task_id") or _runtime_task_id()
    code_version = _code_version()

    leaderboard_rows = _leaderboard_rows(ranked, selection_metric)
    leaderboard_path = write_leaderboard_table(leaderboard_rows, stage_dir / "leaderboard.csv")
    leaderboard_topk_path = write_leaderboard_table(
        leaderboard_rows[:LEADERBOARD_TOP_K],
        stage_dir / "leaderboard_topk.csv",
    )
    evaluation_predictions_path, plots = _write_evaluation_predictions(best, stage_dir)
    candidate_predictions_path, candidate_plots = _write_candidate_predictions(ranked, stage_dir)
    plots.update(candidate_plots)
    model_refs_payload = {
        "stage": "evaluate_models",
        "candidate_count": len(model_results),
        "ensemble_enabled": bool(ensemble_items),
        "ensemble_count": len(ensemble_items),
        "selection_metric": selection_metric,
        "models": [_model_ref_payload(item) for item in model_results],
        "ensembles": [_model_ref_payload(item) for item in ensemble_items],
        "ensemble": _model_ref_payload(best_ensemble) if best_ensemble is not None else None,
    }
    model_refs_path = write_json(model_refs_payload, stage_dir / "model_refs.json")
    metrics_payload = {
        "stage": "evaluate_models",
        "candidate_count": len(model_results),
        "ensemble_enabled": bool(ensemble_items),
        "ensemble_count": len(ensemble_items),
        "selection_metric": selection_metric,
        "metrics_by_model": metrics_by_model,
        "metrics_by_candidate": metrics_by_model,
    }
    metrics_by_model_path = write_json(metrics_payload, stage_dir / "metrics_by_model.json")
    metrics_by_candidate_path = write_json(metrics_payload, stage_dir / "metrics_by_candidate.json")
    metrics_by_candidate_table_path = write_metrics_by_candidate_table(
        metrics_by_model,
        stage_dir / "metrics_by_candidate.csv",
    )
    bar_items = []
    for candidate_name, payload in metrics_by_model.items():
        metrics = payload.get("metrics", {})
        if isinstance(metrics, dict) and isinstance(metrics.get(selection_metric), (int, float)):
            bar_items.append((candidate_name, float(metrics[selection_metric])))
    metrics_by_candidate_bar_path = write_metrics_bar_plot(
        bar_items,
        stage_dir / "metrics_by_candidate_bar.png",
        title=f"Metrics by candidate ({selection_metric})",
        value_label=selection_metric,
        sort="value_desc" if selection_metric == "r2" else "value_asc",
    )
    leaderboard_topk_score_bar_path = write_metrics_bar_plot(
        [(row["model_name"], row.get(selection_metric)) for row in leaderboard_rows],
        stage_dir / "leaderboard_topk_score_bar.png",
        title=f"Leaderboard top-{LEADERBOARD_TOP_K} ({selection_metric})",
        value_label=selection_metric,
        top_n=LEADERBOARD_TOP_K,
        sort="input",
    )
    leaderboard_metric_panel_path = write_leaderboard_metric_panel(
        leaderboard_rows,
        stage_dir / "leaderboard_metric_panel.png",
        top_k=LEADERBOARD_TOP_K,
    )
    leaderboard_pareto_path = write_leaderboard_pareto_plot(
        leaderboard_rows,
        stage_dir / "leaderboard_pareto_rmse_r2.png",
        top_k=max(LEADERBOARD_TOP_K, 10),
    )
    best_model_path = stage_dir / "best_model.joblib"
    shutil.copy2(best["artifacts"]["model"], best_model_path)
    best_payload = {
        "model_name": best["model_name"],
        "artifact_kind": best["artifact_kind"],
        "stage": best["stage"],
        "selection_metric": selection_metric,
        "selection_value": metric_value(best["metrics"], selection_metric),
        "metrics": best["metrics"],
        "model_params": best["model_params"],
        "ensemble_method": best.get("ensemble_method"),
        "source_artifact": str(best["artifacts"]["model"]),
        "best_model_artifact": str(best_model_path),
    }
    best_ensemble_payload = None
    if best_ensemble is not None:
        best_ensemble_payload = {
            "model_name": best_ensemble["model_name"],
            "artifact_kind": best_ensemble["artifact_kind"],
            "ensemble_method": best_ensemble.get("ensemble_method"),
            "stage": best_ensemble["stage"],
            "selection_metric": selection_metric,
            "selection_value": metric_value(best_ensemble["metrics"], selection_metric),
            "metrics": best_ensemble["metrics"],
            "model_params": best_ensemble["model_params"],
            "source_artifact": str(best_ensemble["artifacts"]["model"]),
        }
    best_model_json_path = write_json(best_payload, stage_dir / "best_model.json")
    summary_rows = [
        _summary_row("best_overall", best, selection_metric),
        _summary_row("best_single_model", best_single, selection_metric),
        _summary_row("best_ensemble", best_ensemble, selection_metric),
    ]
    evaluation_summary_path = write_table(pd.DataFrame(summary_rows), stage_dir / "evaluation_summary.csv")
    leaderboard_decision_summary_path = write_table(
        pd.DataFrame(summary_rows),
        stage_dir / "leaderboard_decision_summary.csv",
    )
    best_vs_ensemble_rows = _best_vs_ensemble_rows(best_single, best_ensemble)
    best_vs_ensemble_summary_path = write_table(
        pd.DataFrame(best_vs_ensemble_rows),
        stage_dir / "best_vs_ensemble_summary.csv",
    )
    recommendation = _recommendation_payload(
        best=best,
        best_single=best_single,
        best_ensemble=best_ensemble,
        selection_metric=selection_metric,
        leaderboard_rows=leaderboard_rows,
        task_id=task_id,
    )
    recommendation_path = write_json(recommendation, stage_dir / "recommendation.json")
    decision_summary = _decision_summary_payload(
        best=best,
        best_single=best_single,
        best_ensemble=best_ensemble,
        selection_metric=selection_metric,
        leaderboard_rows=leaderboard_rows,
        best_vs_ensemble_rows=best_vs_ensemble_rows,
        recommendation=recommendation,
        task_id=task_id,
        code_version=code_version,
    )
    decision_summary_md_path = stage_dir / "decision_summary.md"
    decision_summary_md_path.write_text(_decision_summary_markdown(decision_summary), encoding="utf-8")
    decision_summary_json_path = write_json(decision_summary, stage_dir / "decision_summary.json")
    report = {
        "report_schema_version": LEADERBOARD_REPORT_SCHEMA_VERSION,
        "created_at": recommendation["created_at"],
        "code_version": code_version,
        "source_task_id": task_id,
        "stage": "evaluate_models",
        "candidate_count": len(model_results),
        "ensemble_enabled": bool(ensemble_items),
        "ensemble_count": len(ensemble_items),
        "selection_metric": selection_metric,
        "best_model": best_payload,
        "best_single_model": _summary_row("best_single_model", best_single, selection_metric),
        "best_ensemble": best_ensemble_payload,
        "ranked_models": leaderboard_rows,
        "ensemble_metrics": {
            item["model_name"]: {
                "ensemble_method": item.get("ensemble_method"),
                "metrics": item["metrics"],
                "selection_value": metric_value(item["metrics"], selection_metric),
            }
            for item in ranked_ensembles
        },
        "model_refs": model_refs_payload,
        "metrics_by_model": metrics_by_model,
        "metrics_by_candidate": metrics_by_model,
        "evaluation_predictions": str(evaluation_predictions_path) if evaluation_predictions_path else None,
        "leaderboard_topk": str(leaderboard_topk_path),
        "leaderboard_decision_summary": str(leaderboard_decision_summary_path),
        "best_vs_ensemble_summary": str(best_vs_ensemble_summary_path),
        "recommendation": str(recommendation_path),
        "decision_summary": str(decision_summary_md_path),
        "decision_summary_json": str(decision_summary_json_path),
    }
    evaluation_report_path = write_json(report, stage_dir / "evaluation_report.json")
    metrics_payload = {
        **best["metrics"],
        "report_schema_version": LEADERBOARD_REPORT_SCHEMA_VERSION,
        "best_model": best_payload,
        "best_ensemble": best_ensemble_payload,
        "selection_metric": selection_metric,
        "candidate_count": len(model_results),
        "ensemble_enabled": bool(ensemble_items),
        "ensemble_count": len(ensemble_items),
    }
    metrics_path = write_json(metrics_payload, stage_dir / "metrics.json")
    artifacts = {
        "model_refs": model_refs_path,
        "metrics_by_model": metrics_by_model_path,
        "metrics_by_candidate": metrics_by_candidate_path,
        "best_model": best_model_path,
        "best_model_json": best_model_json_path,
        "evaluation_report": evaluation_report_path,
        "recommendation": recommendation_path,
        "decision_summary": decision_summary_md_path,
        "decision_summary_json": decision_summary_json_path,
        "metrics": metrics_path,
    }
    if evaluation_predictions_path is not None:
        artifacts["evaluation_predictions"] = evaluation_predictions_path
    if candidate_predictions_path is not None:
        artifacts["candidate_predictions"] = candidate_predictions_path
    return EvaluationResult(
        stage="evaluate_models",
        stage_dir=stage_dir,
        best=best,
        metrics=metrics_payload,
        report=report,
        artifacts=artifacts,
        tables={
            "leaderboard": leaderboard_path,
            "leaderboard_topk": leaderboard_topk_path,
            "metrics_by_candidate": metrics_by_candidate_table_path,
            "evaluation_summary": evaluation_summary_path,
            "leaderboard_decision_summary": leaderboard_decision_summary_path,
            "best_vs_ensemble_summary": best_vs_ensemble_summary_path,
            **({"evaluation_predictions": evaluation_predictions_path} if evaluation_predictions_path else {}),
            **({"candidate_predictions": candidate_predictions_path} if candidate_predictions_path else {}),
        },
        plots={
            "metrics_by_candidate_bar": metrics_by_candidate_bar_path,
            "leaderboard_topk_score_bar": leaderboard_topk_score_bar_path,
            "leaderboard_metric_panel": leaderboard_metric_panel_path,
            "leaderboard_pareto_rmse_r2": leaderboard_pareto_path,
            **plots,
        },
    )


def _evaluate_models(
    cfg: dict[str, Any],
    model_results: list[dict[str, Any]],
    ensemble_results: list[dict[str, Any]] | dict[str, Any] | None,
    pipeline_dir: Path,
    selection_metric: str,
) -> dict[str, Any]:
    return evaluate_model_candidates(cfg, model_results, ensemble_results, pipeline_dir, selection_metric).to_dict()
