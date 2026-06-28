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
    LEADERBOARD_REPORT_SCHEMA_VERSION,
    SELECTION_METRICS,
    _metric_name,
    _metric_names,
    _path_map,
    _safe_name,
)
from .candidate_training import _train_model_candidates
from .ensemble import _build_ensemble
from .evaluation import _evaluate_models
from .preprocessing import _preprocess_features
from .ranking import _ranked_results


def _run_training_pipeline(cfg: dict[str, Any]) -> RunResult:
    model_cfg = cfg.get("model", {})
    search_cfg = model_cfg.get("search") or {}
    if isinstance(search_cfg, dict) and as_bool(search_cfg.get("enabled")):
        raise ValueError(
            "model.search.enabled=true is future/experimental and is not part of the "
            "primary local training pipeline. Remove model.search or set enabled=false for "
            "preprocess_features -> train_<model>* -> build_ensemble -> evaluate_models."
        )

    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    run_name = cfg.get("run", {}).get("name", "tabular_training_pipeline")
    pipeline_dir = prepare_run_dir(output_dir, run_name)
    selection_metric = _metric_name(model_cfg.get("selection_metric") or "rmse")
    if selection_metric not in SELECTION_METRICS:
        raise ValueError("model.selection_metric must be one of: mae, rmse, r2.")
    metric_names = _metric_names(cfg.get("metrics", {}).get("names"), selection_metric)

    preprocess = _preprocess_features(cfg, pipeline_dir)
    trained = _train_model_candidates(cfg, preprocess, pipeline_dir, metric_names, selection_metric)
    model_results = trained["model_results"]
    ranked_models = _ranked_results(model_results, selection_metric)
    ensemble_result = _build_ensemble(cfg, preprocess, ranked_models, pipeline_dir, metric_names, selection_metric)
    evaluation = _evaluate_models(cfg, model_results, ensemble_result, pipeline_dir, selection_metric)
    ensemble_results = list((ensemble_result or {}).get("ensemble_results", [])) if ensemble_result else []

    artifacts: dict[str, Path] = {
        **preprocess["artifacts"],
        **trained["artifacts"],
        "leaderboard": evaluation["tables"]["leaderboard"],
        **evaluation["artifacts"],
    }
    tables: dict[str, Path] = {
        **preprocess["tables"],
        **evaluation["tables"],
    }
    plots: dict[str, Path] = dict(evaluation.get("plots", {}))
    for plot_name, plot_path in preprocess.get("plots", {}).items():
        plots[plot_name] = plot_path
    for item in model_results:
        key = _safe_name(item["model_name"])
        artifacts[f"model_{key}"] = item["artifacts"]["model"]
        artifacts[f"model_info_{key}"] = item["artifacts"]["model_info"]
        artifacts[f"metrics_{key}"] = item["artifacts"]["metrics"]
        tables[f"metrics_table_{key}"] = item["tables"]["metrics_table"]
        tables[f"validation_predictions_{key}"] = item["tables"]["validation_predictions"]
        if item.get("tables", {}).get("feature_importance"):
            tables[f"feature_importance_{key}"] = item["tables"]["feature_importance"]
        for plot_name, plot_path in item.get("plots", {}).items():
            plots[f"{plot_name}_{key}"] = plot_path
    if ensemble_result is not None:
        artifacts["ensemble"] = ensemble_result["artifacts"]["model"]
        artifacts["ensemble_info"] = ensemble_result["artifacts"]["ensemble_info"]
        artifacts["ensemble_model_info"] = ensemble_result["artifacts"]["model_info"]
        artifacts["ensemble_refs"] = ensemble_result["artifacts"]["ensemble_refs"]
        artifacts["ensemble_info_by_method"] = ensemble_result["artifacts"]["ensemble_info_by_method"]
        for table_name, table_path in ensemble_result.get("tables", {}).items():
            tables[table_name] = table_path
        for item in ensemble_results:
            method = item["ensemble_method"]
            artifacts[f"ensemble_{method}"] = item["artifacts"]["model"]
            artifacts[f"ensemble_model_info_{method}"] = item["artifacts"]["model_info"]
            artifacts[f"ensemble_info_{method}"] = item["artifacts"]["ensemble_info"]
            artifacts[f"ensemble_metrics_{method}"] = item["artifacts"]["metrics"]
        for plot_name, plot_path in ensemble_result.get("plots", {}).items():
            plots[plot_name] = plot_path

    summary = {
        "pipeline_kind": "training",
        "report_schema_version": LEADERBOARD_REPORT_SCHEMA_VERSION,
        "code_version": evaluation["report"].get("code_version"),
        "stages": [
            "preprocess_features",
            *[item["stage"] for item in model_results],
            *(["build_ensemble"] if ensemble_result is not None else []),
            "evaluate_models",
        ],
        "candidate_models": [item["model_name"] for item in model_results],
        "selection_metric": selection_metric,
        "model_refs": trained["model_refs"],
        "metrics_by_model": trained["metrics_by_model"],
        "metrics_by_candidate": evaluation["report"]["metrics_by_candidate"],
        "best_model": evaluation["report"]["best_model"],
        "ensemble": (
            {
                "enabled": True,
                "model_name": ensemble_result["model_name"],
                "ensemble_method": ensemble_result.get("ensemble_method"),
                "artifact": str(ensemble_result["artifacts"]["model"]),
                "selected_base_models": ensemble_result.get("selected_base_models", []),
                "methods": [item["ensemble_method"] for item in ensemble_results],
                "best_ensemble": evaluation["report"].get("best_ensemble"),
            }
            if ensemble_result is not None
            else {"enabled": False}
        ),
        "artifacts": _path_map(artifacts),
        "tables": _path_map(tables),
    }

    metrics_path = write_json(evaluation["metrics"], pipeline_dir / "metrics.json")
    config_path = write_config_snapshot(cfg, pipeline_dir)
    artifacts.update({"metrics": metrics_path, "config": config_path})
    manifest_path = write_manifest(
        pipeline_dir,
        config=cfg,
        metrics=evaluation["metrics"],
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
        metrics=evaluation["metrics"],
        artifacts=artifacts,
        tables=tables,
        plots=plots,
        extra=summary,
    )


def run_pipeline(cfg: dict[str, Any]) -> RunResult:
    if "data" not in cfg:
        raise ValueError("tabular_pipeline requires a stage-based training config with a data section.")
    return _run_training_pipeline(cfg)
