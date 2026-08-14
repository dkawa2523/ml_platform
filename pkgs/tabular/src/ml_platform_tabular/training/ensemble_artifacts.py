from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from ml_platform_core.io import write_json, write_table

from ..selection import metric_value
from ..metrics import regression_prediction_frame
from ..model_artifact import write_model_info
from ..plotting import write_metrics_bar_plot, write_regression_plot_artifacts
from .artifacts import (
    CandidateResult,
    EnsembleMember,
    PredictionArray,
    Predictor,
    PreprocessResult,
    candidate_ref_payload,
    ensemble_member_rows,
)


def write_member_tables(selected_base_models: list[EnsembleMember], method: str, stage_dir: Path) -> dict[str, Path]:
    ensemble_members_path = write_table(
        pd.DataFrame(ensemble_member_rows(selected_base_models)),
        stage_dir / f"ensemble_members_{method}.csv",
    )
    ensemble_weights_path = write_table(
        _weights_frame(selected_base_models, method),
        stage_dir / f"ensemble_weights_{method}.csv",
    )
    return {
        "ensemble_members": ensemble_members_path,
        "ensemble_weights": ensemble_weights_path,
    }


def _weights_frame(selected_base_models: list[EnsembleMember], method: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "rank": item.rank,
                "model_name": item.model_name,
                "ensemble_method": method,
                "weight": item.weight,
                "uses_weighted_average": method != "median",
            }
            for item in selected_base_models
        ]
    )


def write_weight_plot(
    selected_base_models: list[EnsembleMember], method: str, stage_dir: Path, plots: dict[str, Path]
) -> None:
    if method == "median":
        return
    weight_plot_path = write_metrics_bar_plot(
        [(item.model_name, float(item.weight)) for item in selected_base_models if item.weight is not None],
        stage_dir / f"ensemble_weights_{method}.png",
        title=f"Ensemble weights: {method}",
        value_label="weight",
    )
    plots[f"ensemble_weights_{method}"] = weight_plot_path


def write_method_predictions(
    preprocess: PreprocessResult, method: str, y_pred: PredictionArray, stage_dir: Path
) -> tuple[Path, dict[str, Path]]:
    predictions_frame = regression_prediction_frame(
        preprocess.X_valid,
        preprocess.y_valid,
        y_pred,
        model_name=method,
    )
    ensemble_predictions_path = write_table(predictions_frame, stage_dir / f"ensemble_predictions_{method}.csv")
    method_plots = write_regression_plot_artifacts(preprocess.y_valid, y_pred, stage_dir, prefix=f"ensemble_{method}")
    return ensemble_predictions_path, method_plots


def write_method_model_info(
    preprocess: PreprocessResult,
    method: str,
    model_params: dict[str, Any],
    selected_base_models: list[EnsembleMember],
    weights: list[float],
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
        extra={
            "stage": "build_ensemble",
            "feature_config": preprocess.feature_config,
            "ensemble_method": method,
            "top_k": len(selected_base_models),
            "selection_metric": model_params["selection_metric"],
            "selected_base_models": ensemble_member_rows(selected_base_models),
            "weights": _stored_weights(method, weights),
        },
    )


def write_method_ensemble_info(
    method: str,
    top_k: int,
    selection_metric: str,
    selected_base_models: list[EnsembleMember],
    weights: list[float],
    model_path: Path,
    stage_dir: Path,
) -> Path:
    return write_json(
        {
            "enabled": True,
            "method": method,
            "top_k": top_k,
            "selection_metric": selection_metric,
            "produced_model_name": method,
            "selected_base_models": ensemble_member_rows(selected_base_models),
            "weights": _stored_weights(method, weights),
            "aggregation": "median" if method == "median" else "weighted_average",
            "model_artifact": str(model_path),
        },
        stage_dir / f"ensemble_info_{method}.json",
    )


def _stored_weights(method: str, weights: list[float]) -> list[float]:
    return [] if method == "median" else weights


def method_result(
    stage_dir: Path,
    method: str,
    model_params: dict[str, Any],
    estimator: Predictor,
    y_pred: PredictionArray,
    metrics: dict[str, float],
    selected_base_models: list[EnsembleMember],
    *,
    artifacts: dict[str, Path],
    tables: dict[str, Path],
    plots: dict[str, Path],
) -> CandidateResult:
    return CandidateResult(
        stage="build_ensemble",
        stage_dir=stage_dir,
        model_name=method,
        ensemble_method=method,
        model_params=model_params,
        artifact_kind="ensemble",
        artifact_name=f"model_{method}",
        estimator=estimator,
        predictions=y_pred,
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
    plots: dict[str, Path],
) -> Path:
    rows = _ensemble_metrics_rows(ranked_ensembles, selection_metric)
    table_path = write_table(pd.DataFrame(rows), stage_dir / "ensemble_metrics_table.csv")
    plots["ensemble_metrics_bar"] = write_metrics_bar_plot(
        [(row["ensemble_method"], row.get(selection_metric, row["selection_value"])) for row in rows],
        stage_dir / "ensemble_metrics_bar.png",
        title=f"Ensemble metrics ({selection_metric})",
        value_label=selection_metric,
    )
    return table_path


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
    shutil.copy2(best_ensemble.artifacts["ensemble_info"], stage_dir / "ensemble_info.json")
    shutil.copy2(best_ensemble.artifacts["metrics"], stage_dir / "metrics.json")
    shutil.copy2(best_ensemble.tables["ensemble_predictions"], stage_dir / "ensemble_predictions.csv")


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
        "ensemble_info": stage_dir / "ensemble_info.json",
        "metrics": stage_dir / "metrics.json",
        "ensemble_refs": ensemble_refs_path,
    }
    tables: dict[str, Path] = {
        "ensemble_predictions": stage_dir / "ensemble_predictions.csv",
        "ensemble_metrics_table": ensemble_metrics_table_path,
    }
    for item in ensemble_results:
        _add_method_outputs(artifacts, tables, item)
    return artifacts, tables


def _add_method_outputs(artifacts: dict[str, Path], tables: dict[str, Path], item: CandidateResult) -> None:
    method = item.ensemble_method
    artifacts[f"model_{method}"] = item.artifacts["model"]
    artifacts[f"model_info_{method}"] = item.artifacts["model_info"]
    artifacts[f"ensemble_info_{method}"] = item.artifacts["ensemble_info"]
    artifacts[f"metrics_{method}"] = item.artifacts["metrics"]
    tables[f"ensemble_predictions_{method}"] = item.tables["ensemble_predictions"]
    tables[f"ensemble_members_{method}"] = item.tables["ensemble_members"]
    tables[f"ensemble_weights_{method}"] = item.tables["ensemble_weights"]
