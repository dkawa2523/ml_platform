from __future__ import annotations

from pathlib import Path
from typing import Any

from ml_platform_core.artifacts import (
    prepare_run_dir,
    update_latest,
    write_config_snapshot,
    write_manifest,
)
from ml_platform_core.io import load_joblib, read_json, write_table
from ml_platform_core.result import RunResult

from .data import load_dataset, select_features


def _model_artifact_path(cfg: dict[str, Any], output_dir: Path) -> Path:
    value = cfg.get("model", {}).get("artifact_path")
    return Path(value) if value else output_dir / "latest_train" / "model.joblib"


def _model_info_path(cfg: dict[str, Any], model_path: Path) -> Path | None:
    value = cfg.get("model", {}).get("info_path")
    if value:
        return Path(value)
    candidate = model_path.parent / "model_info.json"
    return candidate if candidate.exists() else None


def _features_for_inference(df, cfg: dict[str, Any], model_path: Path) -> list[str]:
    data_cfg = cfg.get("data", {})
    explicit = data_cfg.get("feature_columns")
    if explicit:
        return select_features(
            df,
            target_column=data_cfg.get("target_column"),
            feature_columns=explicit,
            id_columns=data_cfg.get("id_columns"),
        )

    info_path = _model_info_path(cfg, model_path)
    if info_path:
        info = read_json(info_path)
        feature_columns = info.get("feature_columns")
        if feature_columns:
            return select_features(
                df,
                target_column=data_cfg.get("target_column"),
                feature_columns=feature_columns,
                id_columns=data_cfg.get("id_columns"),
            )

    return select_features(
        df,
        target_column=data_cfg.get("target_column"),
        feature_columns=None,
        id_columns=data_cfg.get("id_columns"),
    )


def run_infer(cfg: dict[str, Any]) -> RunResult:
    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    run_name = cfg.get("run", {}).get("name", "tabular_infer")
    run_dir = prepare_run_dir(output_dir, run_name)

    model_path = _model_artifact_path(cfg, output_dir)
    estimator = load_joblib(model_path)

    df = load_dataset(cfg)
    features = _features_for_inference(df, cfg, model_path)
    y_pred = estimator.predict(df[features])

    prediction_name = cfg.get("output", {}).get("prediction_name", "predictions.csv")
    predictions_path = write_table(df.assign(_prediction=y_pred), run_dir / prediction_name)
    config_path = write_config_snapshot(cfg, run_dir)

    manifest_inputs = {
        "config": config_path,
        "predictions": predictions_path,
        "model_source": model_path,
    }
    info_path = _model_info_path(cfg, model_path)
    if info_path:
        manifest_inputs["model_info_source"] = info_path
    manifest_path = write_manifest(run_dir, config=cfg, metrics={}, artifacts=manifest_inputs)
    update_latest(run_dir, output_dir / "latest_infer")
    update_latest(run_dir, output_dir / "latest")

    return RunResult(
        run_dir=run_dir,
        metrics={},
        artifacts={"config": config_path, "manifest": manifest_path},
        tables={"predictions": predictions_path},
        extra={"model_source": str(model_path), "feature_columns": features},
    )
