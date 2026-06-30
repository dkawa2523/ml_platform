from __future__ import annotations

from pathlib import Path
from typing import Any

from ml_platform_core.io import dump_joblib, write_json

from ..ensemble import ensemble_config, ensemble_weights
from ..metrics import regression_metrics
from ..models import MeanTopKEnsemble, MedianEnsemble
from .artifacts import CandidateResult, EnsembleMember, PreprocessResult
from .ensemble_artifacts import (
    copy_best_ensemble_artifacts,
    ensemble_outputs,
    method_result,
    write_ensemble_metrics_summary,
    write_ensemble_reference_artifacts,
    write_member_tables,
    write_method_ensemble_info,
    write_method_model_info,
    write_method_predictions,
    write_weight_plot,
)
from .ranking import ranked_results


def build_ensemble(
    cfg: dict[str, Any],
    preprocess: PreprocessResult,
    ranked: list[CandidateResult],
    pipeline_dir: Path,
    metric_names: list[str] | str | None,
    selection_metric: str,
) -> CandidateResult | None:
    ensemble_cfg = ensemble_config(cfg.get("model", {}))
    if not ensemble_cfg.enabled:
        return None

    stage_dir = _stage_dir(pipeline_dir)
    selected = _selected_candidates(ranked, ensemble_cfg.top_k)
    plots: dict[str, Path] = {}
    ensemble_results = [
        _build_method_ensemble(
            method,
            selected,
            preprocess,
            stage_dir,
            metric_names,
            selection_metric,
            plots,
        )
        for method in ensemble_cfg.methods
    ]

    ranked_ensembles = ranked_results(ensemble_results, selection_metric)
    best_ensemble = ranked_ensembles[0]
    ensemble_metrics_table_path = write_ensemble_metrics_summary(ranked_ensembles, stage_dir, selection_metric, plots)
    copy_best_ensemble_artifacts(best_ensemble, stage_dir)
    refs, ensemble_refs_path = write_ensemble_reference_artifacts(
        ensemble_results, best_ensemble, ensemble_cfg.methods, stage_dir, selection_metric
    )
    artifacts, tables = ensemble_outputs(
        stage_dir,
        ensemble_results,
        ensemble_refs_path,
        ensemble_metrics_table_path,
    )
    return CandidateResult(
        stage="build_ensemble",
        stage_dir=stage_dir,
        model_name=best_ensemble.model_name,
        ensemble_method=best_ensemble.ensemble_method,
        model_params=best_ensemble.model_params,
        artifact_kind="ensemble",
        estimator=best_ensemble.estimator,
        predictions=best_ensemble.predictions,
        metrics=best_ensemble.metrics,
        selected_base_models=best_ensemble.selected_base_models,
        ensemble_results=ensemble_results,
        best_ensemble=best_ensemble,
        ensemble_refs=refs,
        artifacts=artifacts,
        tables=tables,
        plots=plots,
    )


def _stage_dir(pipeline_dir: Path) -> Path:
    stage_dir = pipeline_dir / "build_ensemble"
    stage_dir.mkdir(parents=True, exist_ok=True)
    return stage_dir


def _selected_candidates(ranked: list[CandidateResult], top_k: int) -> list[CandidateResult]:
    return ranked[: min(int(top_k), len(ranked))]


def _build_method_ensemble(
    method: str,
    selected: list[CandidateResult],
    preprocess: PreprocessResult,
    stage_dir: Path,
    metric_names: list[str] | str | None,
    selection_metric: str,
    plots: dict[str, Path],
) -> CandidateResult:
    weights = ensemble_weights(selected, method, selection_metric)
    estimator = _ensemble_estimator(method, selected, weights)
    y_pred = estimator.predict(preprocess.X_valid)
    metrics = regression_metrics(preprocess.y_valid, y_pred, metrics=metric_names)
    model_params = _ensemble_model_params(method, len(selected), selection_metric)
    selected_base_models = _selected_base_models(selected, method, weights)
    member_tables = write_member_tables(selected_base_models, method, stage_dir)
    write_weight_plot(selected_base_models, method, stage_dir, plots)
    prediction_path, method_plots = write_method_predictions(preprocess, method, y_pred, stage_dir)
    plots.update(method_plots)
    model_path = dump_joblib(estimator, stage_dir / f"model_{method}.joblib")
    model_info_path = write_method_model_info(
        preprocess,
        method,
        model_params,
        selected_base_models,
        weights,
        stage_dir,
    )
    ensemble_info_path = write_method_ensemble_info(
        method,
        len(selected),
        selection_metric,
        selected_base_models,
        weights,
        model_path,
        stage_dir,
    )
    metrics_path = write_json(metrics, stage_dir / f"metrics_{method}.json")
    return method_result(
        stage_dir,
        method,
        model_params,
        estimator,
        y_pred,
        metrics,
        selected_base_models,
        artifacts={
            "model": model_path,
            "model_info": model_info_path,
            "ensemble_info": ensemble_info_path,
            "metrics": metrics_path,
        },
        tables={
            "ensemble_predictions": prediction_path,
            **member_tables,
        },
        plots=method_plots,
    )


def _ensemble_estimator(method: str, selected: list[CandidateResult], weights: list[float]):
    estimators = [item.estimator for item in selected]
    if method == "median":
        return MedianEnsemble(estimators)
    return MeanTopKEnsemble(estimators, weights=weights)


def _ensemble_model_params(method: str, top_k: int, selection_metric: str) -> dict[str, Any]:
    return {
        "method": method,
        "top_k": top_k,
        "selection_metric": selection_metric,
    }


def _selected_base_models(selected: list[CandidateResult], method: str, weights: list[float]) -> list[EnsembleMember]:
    return [
        EnsembleMember(
            rank=rank,
            model_name=item.model_name,
            model_params=item.model_params,
            stage=item.stage,
            artifact_path=str(item.artifacts["model"]),
            weight=(weights[rank - 1] if method != "median" else None),
        )
        for rank, item in enumerate(selected, start=1)
    ]
