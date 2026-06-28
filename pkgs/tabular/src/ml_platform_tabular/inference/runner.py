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
from ml_platform_core.io import load_joblib, write_table
from ml_platform_core.result import RunResult

from ..data import load_dataset
from ..plotting import write_prediction_summary_tables
from .metadata import (
    _feature_preset,
    _feature_spec_path,
    _known_target_column,
    _load_feature_spec,
    _load_model_info,
    _load_preprocess_bundle,
    _model_info_path,
    _preprocess_bundle_path,
)
from .prediction_frame import PREDICTION_SCHEMA_VERSION, _model_artifact_id
from .prediction_writer import _chunk_size, write_predictions
from .resolver import _model_artifact_path, _model_selector, _model_source_type
from .schema import (
    _effective_id_columns,
    _features_for_inference,
    _required_feature_columns,
    _schema_check_summary,
    _write_schema_check,
)


def run_infer(cfg: dict[str, Any]) -> RunResult:
    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    run_name = cfg.get("run", {}).get("name", "tabular_infer")
    run_dir = prepare_run_dir(output_dir, run_name)

    model_path = _model_artifact_path(cfg, output_dir)
    estimator = load_joblib(model_path)
    model_info = _load_model_info(cfg, model_path)
    feature_spec = _load_feature_spec(cfg, model_path)
    preprocess_bundle = _load_preprocess_bundle(cfg, model_path)
    schema_preprocess_bundle = dict(preprocess_bundle)
    if "transformer" not in schema_preprocess_bundle and hasattr(estimator, "transformer"):
        schema_preprocess_bundle["transformer"] = getattr(estimator, "transformer")

    df = load_dataset(cfg)
    id_columns = _effective_id_columns(cfg, feature_spec)
    required_features = _required_feature_columns(
        cfg,
        estimator=estimator,
        model_info=model_info,
        feature_spec=feature_spec,
        preprocess_bundle=preprocess_bundle,
    )
    features = _features_for_inference(
        df,
        cfg,
        required_features=required_features,
        id_columns=id_columns,
    )
    target_column = _known_target_column(cfg, feature_spec, model_info, preprocess_bundle)
    schema_summary = _schema_check_summary(
        df,
        feature_columns=features,
        id_columns=id_columns,
        target_column=target_column,
        preprocess_bundle=schema_preprocess_bundle,
    )
    schema_check_json_path, schema_check_table_path = _write_schema_check(schema_summary, run_dir)
    if schema_summary["status"] == "error":
        raise ValueError(f"Missing required inference features: {schema_summary['missing_features']}")

    prediction_name = cfg.get("output", {}).get("prediction_name", "predictions.csv")
    model_artifact_id = _model_artifact_id(model_info, model_path)
    chunk_size = _chunk_size(cfg)
    predictions_path = write_predictions(
        run_dir / prediction_name,
        df,
        estimator,
        features,
        chunk_size,
        id_columns=schema_summary["id_columns"],
        model_info=model_info,
        run_id=run_dir.name,
        model_artifact_id=model_artifact_id,
    )
    prediction_tables, prediction_plots = write_prediction_summary_tables(
        predictions_path,
        run_dir,
        target_column=cfg.get("data", {}).get("target_column"),
    )
    prediction_summary_path = prediction_tables["prediction_summary"]
    config_path = write_config_snapshot(cfg, run_dir)

    artifacts = {
        "config": config_path,
        "schema_check_summary": schema_check_json_path,
    }
    info_path = _model_info_path(cfg, model_path)
    if info_path:
        artifacts["model_info"] = info_path
    feature_spec_path = _feature_spec_path(cfg, model_path)
    if feature_spec_path and feature_spec_path.exists():
        artifacts["feature_spec"] = feature_spec_path
    preprocess_bundle_path = _preprocess_bundle_path(cfg, model_path)
    if preprocess_bundle_path and preprocess_bundle_path.exists():
        artifacts["preprocess_bundle"] = preprocess_bundle_path
    manifest_inputs = {
        **artifacts,
        "model_source": model_path,
    }
    model_cfg = cfg.get("model", {})
    manifest_extra = {
        "prediction_rows": int(len(df)),
        "prediction_file": prediction_name,
        "prediction_summary": str(prediction_summary_path),
        "prediction_schema_version": PREDICTION_SCHEMA_VERSION,
        "schema_check_status": schema_summary["status"],
        "schema_check_summary": str(schema_check_json_path),
        "source_type": _model_source_type(cfg),
        "source_task_id": model_cfg.get("source_task_id"),
        "model_selector": _model_selector(cfg),
        "local_model_path": model_cfg.get("local_model_path"),
        "model_source": str(model_path),
        "resolved_model_path": str(model_path),
        "model_info_path": str(info_path) if info_path else None,
        "feature_spec_path": str(feature_spec_path) if feature_spec_path else None,
        "preprocess_bundle_path": str(preprocess_bundle_path) if preprocess_bundle_path else None,
        "model_name": str(model_info.get("model_name") or model_info.get("best_model_name") or "unknown"),
        "ensemble_method": model_info.get("ensemble_method"),
        "artifact_kind": str(model_info.get("artifact_kind") or "model"),
        "model_artifact_id": model_artifact_id,
        "feature_columns": features,
        "id_columns": schema_summary["id_columns"],
        "target_column": target_column,
        "feature_preset": _feature_preset(feature_spec, model_info, preprocess_bundle),
        "chunk_size": chunk_size,
    }
    source_summary_path = write_table(
        pd.DataFrame(
            [
                {"field": "source_type", "value": manifest_extra["source_type"]},
                {"field": "source_task_id", "value": manifest_extra["source_task_id"]},
                {"field": "model_selector", "value": manifest_extra["model_selector"]},
                {"field": "resolved_model_name", "value": manifest_extra["model_name"]},
                {"field": "artifact_kind", "value": manifest_extra["artifact_kind"]},
                {"field": "model_name", "value": manifest_extra["model_name"]},
                {"field": "ensemble_method", "value": manifest_extra["ensemble_method"]},
                {"field": "target_column", "value": manifest_extra["target_column"]},
                {"field": "feature_preset", "value": manifest_extra["feature_preset"]},
                {"field": "schema_check_status", "value": manifest_extra["schema_check_status"]},
                {"field": "resolved_model_path", "value": manifest_extra["resolved_model_path"]},
                {"field": "model_artifact_id", "value": manifest_extra["model_artifact_id"]},
                {"field": "feature_spec_path", "value": manifest_extra["feature_spec_path"]},
                {"field": "preprocess_bundle_path", "value": manifest_extra["preprocess_bundle_path"]},
            ]
        ),
        run_dir / "source_summary.csv",
    )
    tables = {
        "predictions": predictions_path,
        "schema_check_summary": schema_check_table_path,
        **prediction_tables,
        "source_summary": source_summary_path,
    }
    manifest_path = write_manifest(
        run_dir,
        config=cfg,
        metrics={},
        artifacts=manifest_inputs,
        tables=tables,
        extra=manifest_extra,
    )
    artifacts["manifest"] = manifest_path
    update_latest(run_dir, output_dir / "latest_infer")
    update_latest(run_dir, output_dir / "latest")

    return RunResult(
        run_dir=run_dir,
        metrics={},
        artifacts=artifacts,
        tables=tables,
        plots={"prediction_distribution": prediction_plots["prediction_distribution_histogram"], **prediction_plots},
        extra=manifest_extra,
    )
