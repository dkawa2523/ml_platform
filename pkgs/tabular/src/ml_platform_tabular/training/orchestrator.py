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

from ..ensemble import as_bool
from .artifacts import (
    CandidateResult,
    EvaluationResult,
    LEADERBOARD_REPORT_SCHEMA_VERSION,
    PreprocessResult,
    SELECTION_METRICS,
    _path_map,
    ensemble_member_rows,
    metric_name,
    required_metric_names,
    safe_name,
)
from .candidate_training import train_model_candidates
from .ensemble import build_ensemble
from .evaluation import evaluate_model_candidates
from .preprocessing import preprocess_features
from .ranking import ranked_results


def _run_training_pipeline(cfg: dict[str, Any]) -> RunResult:
    model_cfg = cfg.get("model", {})
    _reject_search_primary_graph(model_cfg)
    pipeline_dir = _prepare_pipeline_dir(cfg)
    selection_metric, metric_names = _metric_settings(cfg, model_cfg)

    preprocess = preprocess_features(cfg, pipeline_dir)
    trained = train_model_candidates(cfg, preprocess, pipeline_dir, metric_names)
    model_results = trained.model_results
    ranked_models = ranked_results(model_results, selection_metric)
    ensemble_result = build_ensemble(cfg, preprocess, ranked_models, pipeline_dir, metric_names, selection_metric)
    evaluation = evaluate_model_candidates(cfg, model_results, ensemble_result, pipeline_dir, selection_metric)

    artifacts, tables, plots = _pipeline_outputs(preprocess, model_results, ensemble_result, evaluation)
    summary = _pipeline_summary(
        selection_metric=selection_metric,
        model_results=model_results,
        ensemble_result=ensemble_result,
        evaluation=evaluation,
        artifacts=artifacts,
        tables=tables,
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


def _reject_search_primary_graph(model_cfg: dict[str, Any]) -> None:
    search_cfg = model_cfg.get("search") or {}
    if isinstance(search_cfg, dict) and as_bool(search_cfg.get("enabled")):
        raise ValueError(
            "model.search.enabled=true is future/experimental and is not part of the "
            "primary local training pipeline. Remove model.search or set enabled=false for "
            "preprocess_features -> train_<model>* -> build_ensemble -> evaluate_models."
        )


def _prepare_pipeline_dir(cfg: dict[str, Any]) -> Path:
    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    run_name = cfg.get("run", {}).get("name", "tabular_training_pipeline")
    return prepare_run_dir(output_dir, run_name)


def _metric_settings(cfg: dict[str, Any], model_cfg: dict[str, Any]) -> tuple[str, list[str] | str | None]:
    selection_metric = metric_name(model_cfg.get("selection_metric") or "rmse")
    if selection_metric not in SELECTION_METRICS:
        raise ValueError("model.selection_metric must be one of: mae, rmse, r2.")
    metric_names = required_metric_names(cfg.get("metrics", {}).get("names"), selection_metric)
    return selection_metric, metric_names


def _pipeline_outputs(
    preprocess: PreprocessResult,
    model_results: list[CandidateResult],
    ensemble_result: CandidateResult | None,
    evaluation: EvaluationResult,
) -> tuple[dict[str, Path], dict[str, Path], dict[str, Path]]:
    artifacts: dict[str, Path] = {
        **preprocess.artifacts,
        "leaderboard": evaluation.tables["leaderboard"],
        **evaluation.artifacts,
    }
    tables: dict[str, Path] = {
        **preprocess.tables,
        **evaluation.tables,
    }
    plots: dict[str, Path] = dict(evaluation.plots)
    for plot_name, plot_path in preprocess.plots.items():
        plots[plot_name] = plot_path
    _add_model_outputs(artifacts, tables, plots, model_results)
    _add_ensemble_outputs(artifacts, tables, plots, ensemble_result)
    return artifacts, tables, plots


def _add_model_outputs(
    artifacts: dict[str, Path],
    tables: dict[str, Path],
    plots: dict[str, Path],
    model_results: list[CandidateResult],
) -> None:
    for item in model_results:
        key = safe_name(item.model_name)
        artifacts[f"model_{key}"] = item.artifacts["model"]
        artifacts[f"model_info_{key}"] = item.artifacts["model_info"]
        artifacts[f"metrics_{key}"] = item.artifacts["metrics"]
        tables[f"metrics_table_{key}"] = item.tables["metrics_table"]
        tables[f"validation_predictions_{key}"] = item.tables["validation_predictions"]
        if item.tables.get("feature_importance"):
            tables[f"feature_importance_{key}"] = item.tables["feature_importance"]
        for plot_name, plot_path in item.plots.items():
            plots[f"{plot_name}_{key}"] = plot_path


def _add_ensemble_outputs(
    artifacts: dict[str, Path],
    tables: dict[str, Path],
    plots: dict[str, Path],
    ensemble_result: CandidateResult | None,
) -> None:
    if ensemble_result is not None:
        ensemble_results = _ensemble_results(ensemble_result)
        artifacts["ensemble"] = ensemble_result.artifacts["model"]
        artifacts["ensemble_info"] = ensemble_result.artifacts["ensemble_info"]
        artifacts["ensemble_model_info"] = ensemble_result.artifacts["model_info"]
        artifacts["ensemble_refs"] = ensemble_result.artifacts["ensemble_refs"]
        for table_name, table_path in ensemble_result.tables.items():
            tables[table_name] = table_path
        for item in ensemble_results:
            method = item.ensemble_method
            artifacts[f"ensemble_{method}"] = item.artifacts["model"]
            artifacts[f"ensemble_model_info_{method}"] = item.artifacts["model_info"]
            artifacts[f"ensemble_info_{method}"] = item.artifacts["ensemble_info"]
            artifacts[f"ensemble_metrics_{method}"] = item.artifacts["metrics"]
        for plot_name, plot_path in ensemble_result.plots.items():
            plots[plot_name] = plot_path


def _pipeline_summary(
    *,
    selection_metric: str,
    model_results: list[CandidateResult],
    ensemble_result: CandidateResult | None,
    evaluation: EvaluationResult,
    artifacts: dict[str, Path],
    tables: dict[str, Path],
) -> dict[str, Any]:
    ensemble_results = _ensemble_results(ensemble_result)
    return {
        "pipeline_kind": "training",
        "report_schema_version": LEADERBOARD_REPORT_SCHEMA_VERSION,
        "code_version": evaluation.report.get("code_version"),
        "stages": _pipeline_stages(model_results, ensemble_result),
        "candidate_models": [item.model_name for item in model_results],
        "selection_metric": selection_metric,
        "metrics_by_candidate": evaluation.report["metrics_by_candidate"],
        "best_model": evaluation.report["best_model"],
        "ensemble": _ensemble_summary(ensemble_result, ensemble_results, evaluation),
        "artifacts": _path_map(artifacts),
        "tables": _path_map(tables),
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
        "artifact": str(ensemble_result.artifacts["model"]),
        "selected_base_models": ensemble_member_rows(ensemble_result.selected_base_models),
        "methods": [item.ensemble_method for item in ensemble_results],
        "best_ensemble": evaluation.report.get("best_ensemble"),
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
    metrics_path = write_json(evaluation.metrics, pipeline_dir / "metrics.json")
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
    update_latest(pipeline_dir, output_dir / "latest_training_pipeline")
    update_latest(pipeline_dir, output_dir / "latest")

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
