from __future__ import annotations

from pathlib import Path
from typing import Any

from ml_platform_core.artifacts import (
    prepare_run_dir,
    update_latest,
    write_config_snapshot,
    write_manifest,
)
from ml_platform_core.io import write_json
from ml_platform_core.result import RunResult

from ..policy import validate_primary_training_graph
from ..selection import metric_settings
from .artifacts import (
    LEADERBOARD_REPORT_SCHEMA_VERSION,
    CandidateResult,
    EvaluationResult,
)
from .candidate_training import train_model_candidates
from .ensemble import build_ensemble
from .evaluation import evaluate_model_candidates
from .output_maps import training_pipeline_outputs
from .preprocessing import preprocess_features
from .ranking import ranked_results


def _run_training_pipeline(cfg: dict[str, Any]) -> RunResult:
    model_cfg = cfg.get("model", {})
    validate_primary_training_graph(model_cfg)
    pipeline_dir = _prepare_pipeline_dir(cfg)
    selection_metric, metric_names = metric_settings(cfg, model_cfg)

    preprocess = preprocess_features(cfg, pipeline_dir)
    model_results = train_model_candidates(cfg, preprocess, pipeline_dir, metric_names)
    ranked_models = ranked_results(model_results, selection_metric)
    ensemble_result = build_ensemble(cfg, preprocess, ranked_models, pipeline_dir, metric_names, selection_metric)
    evaluation = evaluate_model_candidates(
        cfg, preprocess, model_results, ensemble_result, pipeline_dir, selection_metric
    )

    artifacts, tables, plots = training_pipeline_outputs(preprocess, model_results, ensemble_result, evaluation)
    summary = _pipeline_summary(
        selection_metric=selection_metric,
        model_results=model_results,
        ensemble_result=ensemble_result,
        evaluation=evaluation,
    )
    return _finish_training_pipeline(
        cfg,
        pipeline_dir,
        output_dir=Path(cfg.get("runtime", {}).get("output_dir", "outputs")),
        evaluation=evaluation,
        artifacts=artifacts,
        tables=tables,
        plots=plots,
        summary=summary,
    )


def _prepare_pipeline_dir(cfg: dict[str, Any]) -> Path:
    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    run_name = cfg.get("run", {}).get("name", "tabular_training_pipeline")
    return prepare_run_dir(output_dir, run_name)


def _pipeline_summary(
    *,
    selection_metric: str,
    model_results: list[CandidateResult],
    ensemble_result: CandidateResult | None,
    evaluation: EvaluationResult,
) -> dict[str, Any]:
    ensemble_results = _ensemble_results(ensemble_result)
    return {
        "pipeline_kind": "training",
        "report_schema_version": LEADERBOARD_REPORT_SCHEMA_VERSION,
        "code_version": evaluation.summary.get("code_version"),
        "stages": _pipeline_stages(model_results, ensemble_result),
        "candidate_models": [item.model_name for item in model_results],
        "selection_metric": selection_metric,
        "best_model": evaluation.summary["best_model"],
        "ensemble": _ensemble_summary(ensemble_result, ensemble_results, evaluation),
    }


def _pipeline_stages(model_results: list[CandidateResult], ensemble_result: CandidateResult | None) -> list[str]:
    return [
        "preprocess_features",
        *[item.stage for item in model_results],
        *(["build_ensemble"] if ensemble_result is not None else []),
        "evaluate_models",
    ]


def _ensemble_summary(
    ensemble_result: CandidateResult | None,
    ensemble_results: list[CandidateResult],
    evaluation: EvaluationResult,
) -> dict[str, Any]:
    if ensemble_result is None:
        return {"enabled": False}
    return {
        "enabled": True,
        "model_name": ensemble_result.model_name,
        "ensemble_method": ensemble_result.ensemble_method,
        "methods": [item.ensemble_method for item in ensemble_results],
        "best_ensemble": evaluation.summary.get("best_ensemble"),
    }


def _ensemble_results(ensemble_result: CandidateResult | None) -> list[CandidateResult]:
    return list(ensemble_result.ensemble_results) if ensemble_result else []


def _finish_training_pipeline(
    cfg: dict[str, Any],
    pipeline_dir: Path,
    *,
    output_dir: Path,
    evaluation: EvaluationResult,
    artifacts: dict[str, Path],
    tables: dict[str, Path],
    plots: dict[str, Path],
    summary: dict[str, Any],
) -> RunResult:
    metrics_path = write_json({**evaluation.metrics, **evaluation.summary}, pipeline_dir / "metrics.json")
    config_path = write_config_snapshot(cfg, pipeline_dir)
    artifacts.update({"metrics": metrics_path, "config": config_path})
    manifest_path = write_manifest(
        pipeline_dir,
        config=cfg,
        metrics=evaluation.metrics,
        artifacts=artifacts,
        tables=tables,
        plots=plots,
        extra=summary,
    )
    artifacts["manifest"] = manifest_path
    if not cfg.get("runtime", {}).get("use_clearml"):
        update_latest(pipeline_dir, output_dir / "latest_training_pipeline")

    return RunResult(
        run_dir=pipeline_dir,
        metrics=evaluation.metrics,
        artifacts=artifacts,
        tables=tables,
        plots=plots,
        extra=summary,
    )


def run_pipeline(cfg: dict[str, Any]) -> RunResult:
    if "data" not in cfg:
        raise ValueError("tabular_pipeline requires a stage-based training config with a data section.")
    return _run_training_pipeline(cfg)
