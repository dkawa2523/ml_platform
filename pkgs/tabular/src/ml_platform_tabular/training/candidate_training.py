from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd
from ml_platform_core.io import dump_joblib, write_json, write_table

from ..features import FeatureTransformer, build_feature_pipeline
from ..metrics import (
    regression_prediction_frame,
    target_labels,
    target_means,
    target_regression_metrics,
)
from ..model_artifact import write_model_info
from ..models import ModelCandidate, build_model, model_candidates, model_params_for_seed
from ..selection import validate_target_selection_metric
from ..target_model_bundle import TargetModelBundle
from .artifacts import CandidateResult, PreprocessResult, safe_name
from .selection_data import SelectionSplit, selection_split


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

    selection = selection_split(cfg, preprocess)
    selection_transformer = build_feature_pipeline(
        preprocess.feature_preset,
        selection.X_fit[preprocess.feature_columns],
        preprocess.feature_config,
    )
    selection_estimator = _fit_target_models(
        preprocess,
        selection.X_fit,
        selection.y_fit,
        model_name,
        model_params,
        seed,
        transformer=selection_transformer,
    )
    metrics, metrics_table, predictions = _evaluate_candidate(
        preprocess, selection, selection_estimator, model_name, metric_names
    )
    estimator = _fit_target_models(preprocess, preprocess.X_train, preprocess.y_train, model_name, model_params, seed)
    result = CandidateResult(
        stage=stage_name,
        model_name=model_name,
        model_params=model_params,
        artifact_kind="model",
        estimator=estimator,
        metrics=metrics,
        artifacts={},
        tables={},
        plots={},
    )
    artifacts, tables = _write_candidate_outputs(preprocess, result, seed, stage_dir, metrics_table, predictions)
    return replace(result, artifacts=artifacts, tables=tables)


def _fit_target_models(
    preprocess: PreprocessResult,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    model_name: str,
    model_params: dict[str, Any],
    seed: int,
    *,
    transformer: FeatureTransformer | None = None,
) -> TargetModelBundle:
    transformer = transformer or preprocess.transformer
    labels = target_labels(X_train, preprocess.target_names)
    models = {}
    for target in preprocess.target_names:
        mask = labels.eq(target).to_numpy()
        model = build_model(model_name, model_params, seed=seed)
        model.fit(
            transformer.transform(X_train.loc[mask, preprocess.feature_columns]),
            y_train.loc[mask],
        )
        models[target] = model
    return TargetModelBundle(
        transformer=transformer,
        models=models,
        feature_columns=preprocess.feature_columns,
    )


def _evaluate_candidate(
    preprocess: PreprocessResult,
    selection: SelectionSplit,
    estimator: TargetModelBundle,
    model_name: str,
    metric_names: list[str] | str | None,
) -> tuple[dict[str, float], pd.DataFrame, pd.DataFrame]:
    predictions = estimator.predict(selection.X_selection)
    train_labels = target_labels(selection.X_fit, preprocess.target_names)
    selection_labels = target_labels(selection.X_selection, preprocess.target_names)
    metrics, metrics_table = target_regression_metrics(
        selection.y_selection,
        predictions,
        selection_labels,
        metrics=metric_names,
        baseline_means=target_means(selection.y_fit, train_labels),
    )
    metrics_table.insert(0, "model_name", model_name)
    prediction_table = regression_prediction_frame(
        selection.X_selection, selection.y_selection, predictions, model_name=model_name
    )
    return metrics, metrics_table, prediction_table


def _write_candidate_outputs(
    preprocess: PreprocessResult,
    result: CandidateResult,
    seed: int,
    stage_dir: Path,
    metrics_table: pd.DataFrame,
    predictions: pd.DataFrame,
) -> tuple[dict[str, Path], dict[str, Path]]:
    model_path = dump_joblib(result.estimator, stage_dir / "model.joblib")
    artifacts = {
        "model": model_path,
        "model_info": write_model_info(
            stage_dir / "model_info.json",
            feature_columns=preprocess.feature_columns,
            target_column=preprocess.target_column,
            feature_preset=preprocess.feature_preset,
            model_name=result.model_name,
            model_params=result.model_params,
            artifact_kind="model",
            model_path=model_path,
            extra={
                "stage": result.stage,
                "feature_config": preprocess.feature_config,
                "target_names": preprocess.target_names,
                "coordinate_columns": preprocess.coordinate_columns,
                "id_columns": preprocess.id_columns,
                "target_strategy": "independent",
                "seed": seed,
            },
        ),
        "metrics": write_json(result.metrics, stage_dir / "metrics.json"),
    }
    tables = {
        "selection_predictions": write_table(predictions, stage_dir / "selection_predictions.csv"),
        "metrics_table": write_table(metrics_table, stage_dir / "metrics_table.csv"),
    }
    return artifacts, tables


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
