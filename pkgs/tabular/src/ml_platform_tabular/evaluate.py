from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ml_platform_core.artifacts import (
    prepare_run_dir,
    update_latest,
    write_config_snapshot,
    write_manifest,
)
from ml_platform_core.io import load_joblib, write_json, write_table
from ml_platform_core.result import RunResult

from .data import load_dataset, split_xy
from .metrics import regression_metrics, regression_prediction_frame
from .model_artifact import default_model_path, load_model_info_for_model, model_info_path
from .plots import write_regression_plot_artifacts


def _model_artifact_path(cfg: dict[str, Any], output_dir: Path) -> Path:
    value = cfg.get("model", {}).get("artifact_path")
    return Path(value) if value else default_model_path(output_dir)


def run_evaluate(cfg: dict[str, Any]) -> RunResult:
    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    run_name = cfg.get("run", {}).get("name", "tabular_eval")
    run_dir = prepare_run_dir(output_dir, run_name)

    model_path = _model_artifact_path(cfg, output_dir)
    estimator = load_joblib(model_path)
    model_info = load_model_info_for_model(model_path)
    if not cfg.get("data", {}).get("feature_columns") and model_info.get("feature_columns"):
        cfg.setdefault("data", {})["feature_columns"] = model_info["feature_columns"]

    df = load_dataset(cfg)
    X, y, _ = split_xy(df, cfg)
    y_pred = estimator.predict(X)

    metric_names = cfg.get("metrics", {}).get("names")
    metrics = regression_metrics(y, y_pred, metrics=metric_names)
    predictions_path = write_table(regression_prediction_frame(X, y, y_pred), run_dir / "evaluation_predictions.csv")
    metrics_table_path = write_table(
        pd.DataFrame([{"metric": key, "value": value} for key, value in metrics.items()]),
        run_dir / "metrics_table.csv",
    )
    plots = write_regression_plot_artifacts(y, y_pred, run_dir, prefix="evaluation")
    metrics_path = write_json(metrics, run_dir / "metrics.json")
    config_path = write_config_snapshot(cfg, run_dir)

    artifacts = {"metrics": metrics_path, "config": config_path}
    info_path = model_info_path(model_path)
    if info_path.exists():
        artifacts["model_info"] = info_path
    tables = {"evaluation_predictions": predictions_path, "metrics_table": metrics_table_path}
    manifest_path = write_manifest(
        run_dir,
        config=cfg,
        metrics=metrics,
        artifacts={**artifacts, "model_source": model_path},
        tables=tables,
    )
    artifacts["manifest"] = manifest_path
    update_latest(run_dir, output_dir / "latest_eval")
    update_latest(run_dir, output_dir / "latest")

    return RunResult(
        run_dir=run_dir,
        metrics=metrics,
        artifacts=artifacts,
        tables=tables,
        plots=plots,
        extra={"model_source": str(model_path)},
    )
