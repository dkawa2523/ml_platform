from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ml_platform_core.io import dump_joblib, write_json, write_table

from ..metrics import regression_metrics, regression_prediction_frame
from ..model_artifact import write_model_info
from ..models import TabularEstimator, build_model, model_candidates
from ..plotting import (
    write_feature_importance_plot_if_available,
    write_regression_plot_artifacts,
)
from .artifacts import _metrics_by_model_payload, _model_ref_payload, _safe_name


def _train_model(
    cfg: dict[str, Any],
    preprocess: dict[str, Any],
    candidate: dict[str, Any],
    pipeline_dir: Path,
    metric_names: list[str] | str | None,
) -> dict[str, Any]:
    model_name = candidate["name"]
    model_params = candidate["params"]
    stage_name = f"train_{_safe_name(model_name)}"
    stage_dir = pipeline_dir / stage_name
    stage_dir.mkdir(parents=True, exist_ok=True)

    model = build_model(model_name, model_params)
    estimator = TabularEstimator(
        transformer=preprocess["transformer"],
        model=model,
        feature_columns=preprocess["feature_columns"],
    )
    estimator.fit(preprocess["X_train"], preprocess["y_train"])
    y_pred = estimator.predict(preprocess["X_valid"])
    metrics = regression_metrics(preprocess["y_valid"], y_pred, metrics=metric_names)

    predictions_frame = regression_prediction_frame(
        preprocess["X_valid"],
        preprocess["y_valid"],
        y_pred,
        model_name=model_name,
    )
    validation_predictions_path = write_table(predictions_frame, stage_dir / "validation_predictions.csv")
    metrics_table_path = write_table(
        pd.DataFrame([{"metric": key, "value": value} for key, value in metrics.items()]),
        stage_dir / "metrics_table.csv",
    )
    plots = write_regression_plot_artifacts(preprocess["y_valid"], y_pred, stage_dir, prefix="validation")
    feature_importance_path, feature_importance_bar_path = write_feature_importance_plot_if_available(
        estimator, stage_dir
    )
    tables = {"validation_predictions": validation_predictions_path, "metrics_table": metrics_table_path}
    if feature_importance_path is not None:
        tables["feature_importance"] = feature_importance_path
    if feature_importance_bar_path is not None:
        plots["feature_importance"] = feature_importance_bar_path
        plots["feature_importance_bar"] = feature_importance_bar_path
    model_path = dump_joblib(estimator, stage_dir / "model.joblib")
    model_info_path = write_model_info(
        stage_dir / "model_info.json",
        feature_columns=preprocess["feature_columns"],
        target_column=preprocess["target_column"],
        feature_preset=preprocess["feature_preset"],
        model_name=model_name,
        model_params=model_params,
        artifact_kind="model",
        extra={"stage": stage_name, "feature_config": preprocess.get("feature_config", {})},
    )
    metrics_path = write_json(metrics, stage_dir / "metrics.json")

    return {
        "stage": stage_name,
        "stage_dir": stage_dir,
        "model_name": model_name,
        "model_params": model_params,
        "artifact_kind": "model",
        "estimator": estimator,
        "predictions": y_pred,
        "metrics": metrics,
        "artifacts": {
            "model": model_path,
            "model_info": model_info_path,
            "metrics": metrics_path,
        },
        "tables": tables,
        "plots": plots,
    }


def _train_model_candidates(
    cfg: dict[str, Any],
    preprocess: dict[str, Any],
    pipeline_dir: Path,
    metric_names: list[str] | str | None,
    selection_metric: str,
) -> dict[str, Any]:
    stage_dir = pipeline_dir / "model_candidates"
    stage_dir.mkdir(parents=True, exist_ok=True)

    model_cfg = cfg.get("model", {})
    candidates = model_candidates(model_cfg)
    if not candidates:
        raise ValueError("Training pipeline requires at least one model candidate.")

    model_results = [_train_model(cfg, preprocess, candidate, pipeline_dir, metric_names) for candidate in candidates]
    refs = [_model_ref_payload(item) for item in model_results]
    metrics_by_model = _metrics_by_model_payload(model_results, selection_metric)
    model_refs_path = write_json(
        {
            "stage": "model_candidates",
            "candidate_count": len(model_results),
            "selection_metric": selection_metric,
            "models": refs,
        },
        stage_dir / "model_refs.json",
    )
    metrics_by_model_path = write_json(
        {
            "stage": "model_candidates",
            "candidate_count": len(model_results),
            "selection_metric": selection_metric,
            "metrics_by_model": metrics_by_model,
        },
        stage_dir / "metrics_by_model.json",
    )
    return {
        "stage": "model_candidates",
        "stage_dir": stage_dir,
        "model_results": model_results,
        "model_refs": refs,
        "metrics_by_model": metrics_by_model,
        "artifacts": {
            "model_refs": model_refs_path,
            "metrics_by_model": metrics_by_model_path,
        },
    }
