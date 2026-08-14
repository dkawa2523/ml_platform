"""ClearML-free stage runner for tabular training pipelines.

This module executes one stage at a time. ClearML resolves artifact URLs before
calling this code; package code only receives local paths or plain JSON refs.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ml_platform_core.result import RunResult
from ml_platform_core.stages import as_stage_name

from .models import ModelCandidate
from .selection import metric_settings
from .stage_inputs import ensemble_refs, load_preprocess, model_refs, stage_inputs
from .stage_result import finish_stage, stage_run_dir
from .training.artifacts import (
    CandidateResult,
    PreprocessResult,
    ensemble_member_rows,
    safe_name,
)
from .training.candidate_training import train_model
from .training.ensemble import build_ensemble
from .training.evaluation import evaluate_model_candidates
from .training.preprocessing import preprocess_features
from .training.ranking import ranked_results

__all__ = ["run_stage"]

StageRunner = Callable[[dict[str, Any]], RunResult]


def _metric_settings(cfg: dict[str, Any]) -> tuple[str, list[str]]:
    return metric_settings(cfg, cfg.get("model", {}))


def _path_map(paths: dict[str, Path]) -> dict[str, str]:
    return {key: str(value) for key, value in paths.items()}


def _finish_dict_stage(
    cfg: dict[str, Any],
    run_dir: Path,
    result: CandidateResult | PreprocessResult,
    *,
    metrics: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> RunResult:
    return finish_stage(
        cfg,
        run_dir,
        metrics=result.metrics if isinstance(result, CandidateResult) and metrics is None else metrics or {},
        artifacts=result.artifacts,
        tables=result.tables,
        plots=result.plots,
        extra=extra,
    )


def _run_preprocess(cfg: dict[str, Any]) -> RunResult:
    run_dir = stage_run_dir(cfg, "preprocess_features")
    stage = preprocess_features(cfg, run_dir)
    return _finish_dict_stage(
        cfg,
        run_dir,
        stage,
        metrics={},
        extra={
            "pipeline_stage": "preprocess_features",
            "artifacts": _path_map(stage.artifacts),
            "tables": _path_map(stage.tables),
            "plots": _path_map(stage.plots),
        },
    )


def _run_train_model(cfg: dict[str, Any]) -> RunResult:
    preprocess = load_preprocess(cfg)
    _, metric_names = _metric_settings(cfg)
    model_cfg = cfg.get("model", {})
    model_name = str(model_cfg.get("name") or "ridge")
    model_params = model_cfg.get("params") or {}
    if not isinstance(model_params, dict):
        raise ValueError("model.params must be a mapping for train_model stage.")

    run_dir = stage_run_dir(cfg, f"train_{safe_name(model_name)}")
    result = train_model(cfg, preprocess, ModelCandidate(model_name, model_params), run_dir, metric_names)
    return _finish_dict_stage(
        cfg,
        run_dir,
        result,
        extra={
            "pipeline_stage": "train_model",
            "stage_name": result.stage,
            "model_name": result.model_name,
            "model_params": result.model_params,
        },
    )


def _run_build_ensemble(cfg: dict[str, Any]) -> RunResult:
    preprocess = load_preprocess(cfg)
    inputs = stage_inputs(cfg)
    selection_metric, metric_names = _metric_settings(cfg)
    refs = model_refs(inputs)
    ranked = ranked_results(refs, selection_metric)

    run_dir = stage_run_dir(cfg, "build_ensemble")
    result = build_ensemble(cfg, preprocess, ranked, run_dir, metric_names, selection_metric)
    if result is None:
        raise ValueError("build_ensemble stage requires model.ensemble.enabled=true.")
    return _finish_dict_stage(
        cfg,
        run_dir,
        result,
        extra={
            "pipeline_stage": "build_ensemble",
            "stage_name": "build_ensemble",
            "model_name": result.model_name,
            "ensemble_method": result.ensemble_method,
            "ensemble_methods": [item.ensemble_method for item in result.ensemble_results],
            "selected_base_models": ensemble_member_rows(result.selected_base_models),
        },
    )


def _run_evaluate_models(cfg: dict[str, Any]) -> RunResult:
    inputs = stage_inputs(cfg)
    selection_metric, _ = _metric_settings(cfg)
    models = model_refs(inputs)
    ensembles = ensemble_refs(inputs)

    run_dir = stage_run_dir(cfg, "evaluate_models")
    result = evaluate_model_candidates(cfg, models, ensembles, run_dir, selection_metric)
    artifacts = dict(result.artifacts)
    tables = dict(result.tables)
    metrics = dict(result.metrics)
    best_model_path = artifacts.get("best_model")
    if best_model_path and best_model_path.exists():
        copied = run_dir / "best_model.joblib"
        if best_model_path != copied:
            shutil.copy2(best_model_path, copied)
            artifacts["best_model"] = copied
    return finish_stage(
        cfg,
        run_dir,
        metrics=metrics,
        artifacts=artifacts,
        tables=tables,
        plots=result.plots,
        extra={
            "pipeline_stage": "evaluate_models",
            "stage_name": "evaluate_models",
            "report_schema_version": result.report.get("report_schema_version"),
            "code_version": result.report.get("code_version"),
            "source_task_id": result.report.get("source_task_id"),
            "best_model": result.report["best_model"],
            "candidate_count": result.report["candidate_count"],
            "ensemble_enabled": result.report["ensemble_enabled"],
            "ensemble_count": result.report.get("ensemble_count", 0),
        },
    )


STAGE_RUNNERS: dict[str, StageRunner] = {
    "preprocess_features": _run_preprocess,
    "train_model": _run_train_model,
    "build_ensemble": _run_build_ensemble,
    "evaluate_models": _run_evaluate_models,
}


def run_stage(cfg: dict[str, Any]) -> RunResult:
    raw_stage = str(cfg.get("run", {}).get("stage") or "").strip()
    if not raw_stage:
        raise ValueError("run.stage is required for tabular_stage.")
    stage = as_stage_name(raw_stage)
    return STAGE_RUNNERS[stage](cfg)
