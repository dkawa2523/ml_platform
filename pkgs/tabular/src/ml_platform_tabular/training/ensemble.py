from __future__ import annotations

from pathlib import Path
from typing import Any

from ml_platform_core.io import dump_joblib, write_json, write_table

from ..ensemble import ensemble_config, ensemble_weights
from ..metrics import target_labels, target_means, target_regression_metrics
from ..models import MeanTopKEnsemble, MedianEnsemble
from .artifacts import CandidateResult, EnsembleMember, PreprocessResult
from .ensemble_artifacts import (
    copy_best_ensemble_artifacts,
    ensemble_outputs,
    method_result,
    write_ensemble_metrics_summary,
    write_ensemble_reference_artifacts,
    write_member_table,
    write_method_model_info,
    write_method_predictions,
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
    ensemble_results = [
        _build_method_ensemble(
            method,
            selected,
            preprocess,
            stage_dir,
            metric_names,
            selection_metric,
        )
        for method in ensemble_cfg.methods
    ]

    ranked_ensembles = ranked_results(ensemble_results, selection_metric)
    best_ensemble = ranked_ensembles[0]
    ensemble_metrics_table_path = write_ensemble_metrics_summary(ranked_ensembles, stage_dir, selection_metric)
    copy_best_ensemble_artifacts(best_ensemble, stage_dir)
    _, ensemble_refs_path = write_ensemble_reference_artifacts(
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
        model_name=best_ensemble.model_name,
        ensemble_method=best_ensemble.ensemble_method,
        model_params=best_ensemble.model_params,
        artifact_kind="ensemble",
        estimator=best_ensemble.estimator,
        metrics=best_ensemble.metrics,
        selected_base_models=best_ensemble.selected_base_models,
        ensemble_results=ensemble_results,
        artifacts=artifacts,
        tables=tables,
        plots={},
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
) -> CandidateResult:
    weights = ensemble_weights(selected, method, selection_metric)
    estimator = _ensemble_estimator(method, selected, weights)
    y_pred = estimator.predict(preprocess.X_valid)
    train_targets = target_labels(preprocess.X_train, preprocess.target_names)
    valid_targets = target_labels(preprocess.X_valid, preprocess.target_names)
    metrics, metrics_table = target_regression_metrics(
        preprocess.y_valid,
        y_pred,
        valid_targets,
        metrics=metric_names,
        baseline_means=target_means(preprocess.y_train, train_targets),
    )
    metrics_table.insert(0, "model_name", method)
    metrics_table_path = write_table(metrics_table, stage_dir / f"metrics_table_{method}.csv")
    model_params = _ensemble_model_params(method, len(selected), selection_metric)
    selected_base_models = _selected_base_models(selected, method, weights)
    member_table = write_member_table(selected_base_models, method, stage_dir)
    prediction_path = write_method_predictions(preprocess, method, y_pred, stage_dir)
    model_path = dump_joblib(estimator, stage_dir / f"model_{method}.joblib")
    model_info_path = write_method_model_info(
        preprocess,
        method,
        model_params,
        selected_base_models,
        weights,
        stage_dir,
    )
    metrics_path = write_json(metrics, stage_dir / f"metrics_{method}.json")
    return method_result(
        method,
        model_params,
        estimator,
        metrics,
        selected_base_models,
        artifacts={
            "model": model_path,
            "model_info": model_info_path,
            "metrics": metrics_path,
        },
        tables={
            "ensemble_predictions": prediction_path,
            "metrics_table": metrics_table_path,
            "ensemble_members": member_table,
        },
        plots={},
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
