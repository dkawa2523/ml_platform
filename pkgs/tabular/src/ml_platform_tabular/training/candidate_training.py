from __future__ import annotations

from pathlib import Path
from typing import Any

from ml_platform_core.io import dump_joblib, write_json, write_table

from ..metrics import (
    regression_prediction_frame,
    target_labels,
    target_means,
    target_regression_metrics,
)
from ..model_artifact import write_model_info
from ..models import ModelCandidate, build_model, model_candidates, model_params_for_seed
from ..selection import validate_target_selection_metric
from .artifacts import CandidateResult, PreprocessResult, safe_name
from ..target_model_bundle import TargetModelBundle


def train_model(
    cfg: dict[str, Any],
    preprocess: PreprocessResult,
    candidate: ModelCandidate,
    pipeline_dir: Path,
    metric_names: list[str] | str | None,
) -> CandidateResult:
    model_name = candidate.name
    seed = int(cfg.get("run", {}).get("seed", 42))
    model_params = model_params_for_seed(model_name, candidate.params, seed)
    stage_name = f"train_{safe_name(model_name)}"
    stage_dir = pipeline_dir / stage_name
    stage_dir.mkdir(parents=True, exist_ok=True)
    selection_metric = str(cfg.get("model", {}).get("selection_metric") or "rmse").strip().lower().replace("-", "_")
    validate_target_selection_metric(selection_metric, len(preprocess.target_names))

    models = {}
    train_targets = target_labels(preprocess.X_train, preprocess.target_names)
    for target in preprocess.target_names:
        mask = train_targets.eq(target).to_numpy()
        model = build_model(model_name, model_params, seed=seed)
        model.fit(
            preprocess.transformer.transform(preprocess.X_train.loc[mask, preprocess.feature_columns]),
            preprocess.y_train.loc[mask],
        )
        models[target] = model
    estimator = TargetModelBundle(
        transformer=preprocess.transformer,
        models=models,
        feature_columns=preprocess.feature_columns,
    )
    y_pred = estimator.predict(preprocess.X_valid)
    valid_targets = target_labels(preprocess.X_valid, preprocess.target_names)
    metrics, metrics_table = target_regression_metrics(
        preprocess.y_valid,
        y_pred,
        valid_targets,
        metrics=metric_names,
        baseline_means=target_means(preprocess.y_train, train_targets),
    )

    predictions_frame = regression_prediction_frame(
        preprocess.X_valid,
        preprocess.y_valid,
        y_pred,
        model_name=model_name,
    )
    validation_predictions_path = write_table(predictions_frame, stage_dir / "validation_predictions.csv")
    metrics_table.insert(0, "model_name", model_name)
    metrics_table_path = write_table(metrics_table, stage_dir / "metrics_table.csv")
    tables = {"validation_predictions": validation_predictions_path, "metrics_table": metrics_table_path}
    model_path = dump_joblib(estimator, stage_dir / "model.joblib")
    model_info_path = write_model_info(
        stage_dir / "model_info.json",
        feature_columns=preprocess.feature_columns,
        target_column=preprocess.target_column,
        feature_preset=preprocess.feature_preset,
        model_name=model_name,
        model_params=model_params,
        artifact_kind="model",
        extra={
            "stage": stage_name,
            "feature_config": preprocess.feature_config,
            "target_names": preprocess.target_names,
            "coordinate_columns": preprocess.coordinate_columns,
            "id_columns": preprocess.id_columns,
            "target_strategy": "independent",
            "seed": seed,
        },
    )
    metrics_path = write_json(metrics, stage_dir / "metrics.json")

    return CandidateResult(
        stage=stage_name,
        model_name=model_name,
        model_params=model_params,
        artifact_kind="model",
        estimator=estimator,
        metrics=metrics,
        artifacts={
            "model": model_path,
            "model_info": model_info_path,
            "metrics": metrics_path,
        },
        tables=tables,
        plots={},
    )


def train_model_candidates(
    cfg: dict[str, Any],
    preprocess: PreprocessResult,
    pipeline_dir: Path,
    metric_names: list[str] | str | None,
) -> list[CandidateResult]:
    model_cfg = cfg.get("model", {})
    candidates = model_candidates(model_cfg)
    if not candidates:
        raise ValueError("Training pipeline requires at least one model candidate.")

    return [train_model(cfg, preprocess, candidate, pipeline_dir, metric_names) for candidate in candidates]
