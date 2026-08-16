from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pandas as pd
from ml_platform_core.io import write_json, write_table

from ..model_artifact import write_model_info
from ..models import Predictor
from ..selection import metric_value
from .artifacts import (
    CandidateResult,
    EnsembleMember,
    PreprocessResult,
    candidate_ref_payload,
    ensemble_member_rows,
)


def write_member_table(selected_base_models: list[EnsembleMember], method: str, stage_dir: Path) -> Path:
    rows = ensemble_member_rows(selected_base_models)
    for row in rows:
        row["ensemble_method"] = method
    return write_table(
        pd.DataFrame(rows),
        stage_dir / f"ensemble_members_{method}.csv",
    )


def write_method_predictions(predictions: pd.DataFrame, method: str, stage_dir: Path) -> Path:
    return write_table(predictions, stage_dir / f"selection_predictions_{method}.csv")


def write_method_model_info(
    preprocess: PreprocessResult,
    method: str,
    model_params: dict[str, Any],
    selected_base_models: list[EnsembleMember],
    weights: list[float],
    model_path: Path,
    stage_dir: Path,
) -> Path:
    return write_model_info(
        stage_dir / f"model_info_{method}.json",
        feature_columns=preprocess.feature_columns,
        target_column=preprocess.target_column,
        feature_preset=preprocess.feature_preset,
        model_name=method,
        model_params=model_params,
        artifact_kind="ensemble",
        model_path=model_path,
        extra={
            "stage": "build_ensemble",
            "feature_config": preprocess.feature_config,
            "ensemble_method": method,
            "top_k": len(selected_base_models),
            "selection_metric": model_params["selection_metric"],
            "selected_base_models": ensemble_member_rows(selected_base_models),
            "weights": _stored_weights(method, weights),
            "target_names": preprocess.target_names,
            "coordinate_columns": preprocess.coordinate_columns,
            "id_columns": preprocess.id_columns,
            "target_strategy": "independent",
        },
    )


def _stored_weights(method: str, weights: list[float]) -> list[float]:
    return [] if method == "median" else weights


def method_result(
    method: str,
    model_params: dict[str, Any],
    estimator: Predictor,
    metrics: dict[str, float],
    selected_base_models: list[EnsembleMember],
    *,
    artifacts: dict[str, Path],
    tables: dict[str, Path],
    plots: dict[str, Path],
) -> CandidateResult:
    return CandidateResult(
        stage="build_ensemble",
        model_name=method,
        ensemble_method=method,
        model_params=model_params,
        artifact_kind="ensemble",
        artifact_name=f"model_{method}",
        estimator=estimator,
        metrics=metrics,
        selected_base_models=selected_base_models,
        artifacts=artifacts,
        tables=tables,
        plots=plots,
    )


def write_ensemble_metrics_summary(
    ranked_ensembles: list[CandidateResult],
    stage_dir: Path,
    selection_metric: str,
) -> Path:
    rows = _ensemble_metrics_rows(ranked_ensembles, selection_metric)
    return write_table(pd.DataFrame(rows), stage_dir / "ensemble_metrics_table.csv")


def _ensemble_metrics_rows(ranked_ensembles: list[CandidateResult], selection_metric: str) -> list[dict[str, Any]]:
    rows = []
    for item in ranked_ensembles:
        row = {
            "ensemble_method": item.ensemble_method,
            "model_name": item.model_name,
            "selection_metric": selection_metric,
            "selection_value": metric_value(item.metrics, selection_metric),
        }
        row.update(item.metrics)
        rows.append(row)
    return rows


def copy_best_ensemble_artifacts(best_ensemble: CandidateResult, stage_dir: Path) -> None:
    shutil.copy2(best_ensemble.artifacts["model"], stage_dir / "model.joblib")
    shutil.copy2(best_ensemble.artifacts["model_info"], stage_dir / "model_info.json")
    shutil.copy2(best_ensemble.artifacts["metrics"], stage_dir / "metrics.json")
    shutil.copy2(best_ensemble.tables["selection_predictions"], stage_dir / "selection_predictions.csv")
    shutil.copy2(best_ensemble.tables["metrics_table"], stage_dir / "metrics_table.csv")


def write_ensemble_reference_artifacts(
    ensemble_results: list[CandidateResult],
    best_ensemble: CandidateResult,
    methods: list[str],
    stage_dir: Path,
    selection_metric: str,
) -> tuple[list[dict[str, Any]], Path]:
    refs = [candidate_ref_payload(item) for item in ensemble_results]
    ensemble_refs_path = write_json(
        {
            "stage": "build_ensemble",
            "selection_metric": selection_metric,
            "methods": methods,
            "ensembles": refs,
            "best_ensemble": candidate_ref_payload(best_ensemble),
        },
        stage_dir / "ensemble_refs.json",
    )
    return refs, ensemble_refs_path


def ensemble_outputs(
    stage_dir: Path,
    ensemble_results: list[CandidateResult],
    ensemble_refs_path: Path,
    ensemble_metrics_table_path: Path,
) -> tuple[dict[str, Path], dict[str, Path]]:
    artifacts: dict[str, Path] = {
        "model": stage_dir / "model.joblib",
        "model_info": stage_dir / "model_info.json",
        "metrics": stage_dir / "metrics.json",
        "ensemble_refs": ensemble_refs_path,
    }
    tables: dict[str, Path] = {
        "selection_predictions": stage_dir / "selection_predictions.csv",
        "ensemble_metrics_table": ensemble_metrics_table_path,
        "ensemble_target_metrics": stage_dir / "metrics_table.csv",
    }
    for item in ensemble_results:
        _add_method_outputs(artifacts, tables, item)
    return artifacts, tables


def _add_method_outputs(artifacts: dict[str, Path], tables: dict[str, Path], item: CandidateResult) -> None:
    method = item.ensemble_method
    artifacts[f"model_{method}"] = item.artifacts["model"]
    artifacts[f"model_info_{method}"] = item.artifacts["model_info"]
    artifacts[f"metrics_{method}"] = item.artifacts["metrics"]
    tables[f"selection_predictions_{method}"] = item.tables["selection_predictions"]
    tables[f"ensemble_target_metrics_{method}"] = item.tables["metrics_table"]
    tables[f"ensemble_members_{method}"] = item.tables["ensemble_members"]
