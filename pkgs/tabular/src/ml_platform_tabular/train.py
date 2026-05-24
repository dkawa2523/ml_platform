from __future__ import annotations

from pathlib import Path
from typing import Any

from ml_platform_core.artifacts import (
    prepare_run_dir,
    update_latest,
    write_config_snapshot,
    write_manifest,
)
from ml_platform_core.io import dump_joblib, write_json, write_table
from ml_platform_core.result import RunResult

from .data import load_dataset, split_xy, train_valid_split
from .features import build_feature_pipeline
from .metrics import regression_metrics
from .model_artifact import write_model_info
from .models import TabularEstimator, build_model


def run_train(cfg: dict[str, Any]) -> RunResult:
    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    run_name = cfg.get("run", {}).get("name", "tabular_train")
    run_dir = prepare_run_dir(output_dir, run_name)

    df = load_dataset(cfg)
    X, y, feature_names = split_xy(df, cfg)
    X_train, X_valid, y_train, y_valid = train_valid_split(X, y, cfg)

    feature_cfg = cfg.get("features", {})
    feature_preset = feature_cfg.get("preset", "basic")
    transformer = build_feature_pipeline(feature_preset, X_train, feature_cfg.get("params") or {})

    model_cfg = cfg.get("model", {})
    model_name = model_cfg.get("name", "ridge")
    model = build_model(model_name, model_cfg.get("params") or {})

    estimator = TabularEstimator(transformer=transformer, model=model, feature_columns=feature_names)
    estimator.fit(X_train, y_train)
    y_pred = estimator.predict(X_valid)

    metric_names = cfg.get("metrics", {}).get("names")
    metrics = regression_metrics(y_valid, y_pred, metrics=metric_names)
    predictions_path = write_table(
        X_valid.assign(_target=y_valid.values, _prediction=y_pred),
        run_dir / "validation_predictions.csv",
    )
    model_path = dump_joblib(estimator, run_dir / "model.joblib")
    model_info_path = write_model_info(
        run_dir / "model_info.json",
        feature_columns=feature_names,
        target_column=cfg.get("data", {}).get("target_column"),
        feature_preset=feature_preset,
        model_name=model_name,
    )
    metrics_path = write_json(metrics, run_dir / "metrics.json")
    config_path = write_config_snapshot(cfg, run_dir)

    artifacts = {
        "model": model_path,
        "model_info": model_info_path,
        "metrics": metrics_path,
        "config": config_path,
    }
    tables = {"validation_predictions": predictions_path}
    manifest_path = write_manifest(run_dir, config=cfg, metrics=metrics, artifacts=artifacts, tables=tables)
    artifacts["manifest"] = manifest_path

    update_latest(run_dir, output_dir / "latest_train")
    update_latest(run_dir, output_dir / "latest")

    return RunResult(
        run_dir=run_dir,
        metrics=metrics,
        artifacts=artifacts,
        tables=tables,
        extra={"feature_columns": feature_names},
    )
