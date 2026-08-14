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
from ml_platform_core.io import load_joblib
from ml_platform_core.result import RunResult

from ..data import load_inference_dataset
from ..plotting import write_prediction_summary_tables
from .metadata import (
    _known_target_column,
    _load_model_info,
    _model_info_path,
)
from .prediction_frame import PREDICTION_SCHEMA_VERSION, _model_artifact_id
from .prediction_writer import write_predictions
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

    model_path, estimator, model_info = _load_model_context(cfg, output_dir)
    df = load_inference_dataset(cfg)
    features, schema_summary = _check_inference_schema(
        cfg,
        df,
        estimator=estimator,
        model_info=model_info,
    )
    schema_check_json_path = _write_schema_check(schema_summary, run_dir)
    if schema_summary["status"] == "error":
        raise ValueError(
            "Missing required inference features or invalid numeric values: "
            f"missing_features={schema_summary['missing_features']}, "
            f"invalid_numeric_features={schema_summary['invalid_numeric_features']}"
        )

    prediction_name = cfg.get("output", {}).get("prediction_name", "predictions.csv")
    model_artifact_id = _model_artifact_id(model_path)
    predictions_path = _write_predictions(
        run_dir,
        prediction_name,
        df,
        estimator,
        features,
        schema_summary,
        model_info=model_info,
    )
    prediction_tables, prediction_plots = write_prediction_summary_tables(
        predictions_path,
        run_dir,
    )

    artifacts = _inference_artifacts(cfg, run_dir, model_path, schema_check_json_path)
    manifest_extra = _manifest_extra(
        cfg,
        df,
        model_info=model_info,
        schema_summary=schema_summary,
        model_artifact_id=model_artifact_id,
    )
    tables = {
        "predictions": predictions_path,
        **prediction_tables,
    }
    return _finish_inference_run(
        cfg,
        run_dir,
        output_dir=output_dir,
        artifacts=artifacts,
        tables=tables,
        prediction_plots=prediction_plots,
        manifest_extra=manifest_extra,
    )


def _load_model_context(
    cfg: dict[str, Any],
    output_dir: Path,
) -> tuple[Path, Any, dict[str, Any]]:
    model_path = _model_artifact_path(cfg, output_dir)
    estimator = load_joblib(model_path)
    model_info = _load_model_info(cfg, model_path)
    return model_path, estimator, model_info


def _schema_transformer(estimator: Any) -> dict[str, Any]:
    transformer = getattr(estimator, "transformer", None)
    estimators = getattr(estimator, "estimators", None)
    if transformer is None and estimators:
        transformer = getattr(estimators[0], "transformer", None)
    if transformer is not None:
        return {"transformer": transformer}
    return {}


def _check_inference_schema(
    cfg: dict[str, Any],
    df: pd.DataFrame,
    *,
    estimator: Any,
    model_info: dict[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    id_columns = _effective_id_columns(cfg, model_info)
    required_features = _required_feature_columns(
        cfg,
        estimator=estimator,
        model_info=model_info,
    )
    features = _features_for_inference(
        df,
        cfg,
        required_features=required_features,
        id_columns=id_columns,
    )
    target_column = _known_target_column(cfg, model_info)
    schema_summary = _schema_check_summary(
        df,
        feature_columns=features,
        id_columns=id_columns,
        target_column=target_column,
        preprocess_bundle=_schema_transformer(estimator),
    )
    return features, schema_summary


def _write_predictions(
    run_dir: Path,
    prediction_name: str,
    df: pd.DataFrame,
    estimator: Any,
    features: list[str],
    schema_summary: dict[str, Any],
    *,
    model_info: dict[str, Any],
) -> Path:
    return write_predictions(
        run_dir / prediction_name,
        df,
        estimator,
        features,
        id_columns=schema_summary["id_columns"],
        coordinate_columns=list(model_info.get("coordinate_columns") or []),
    )


def _inference_artifacts(
    cfg: dict[str, Any],
    run_dir: Path,
    model_path: Path,
    schema_check_json_path: Path,
) -> dict[str, Path]:
    config_path = write_config_snapshot(cfg, run_dir)

    artifacts: dict[str, Path] = {
        "config": config_path,
        "schema_check_summary": schema_check_json_path,
    }
    info_path = _model_info_path(cfg, model_path)
    if info_path:
        artifacts["model_info"] = info_path
    return artifacts


def _manifest_extra(
    cfg: dict[str, Any],
    df: pd.DataFrame,
    *,
    model_info: dict[str, Any],
    schema_summary: dict[str, Any],
    model_artifact_id: str,
) -> dict[str, Any]:
    model_cfg = cfg.get("model", {})
    return {
        "prediction_rows": int(len(df)),
        "prediction_schema_version": PREDICTION_SCHEMA_VERSION,
        "schema_check_status": schema_summary["status"],
        "source_type": _model_source_type(cfg),
        "source_task_id": model_cfg.get("source_task_id"),
        "model_selector": _model_selector(cfg),
        "model_name": str(model_info.get("model_name") or "unknown"),
        "ensemble_method": model_info.get("ensemble_method"),
        "artifact_kind": str(model_info.get("artifact_kind") or "model"),
        "model_artifact_id": model_artifact_id,
    }


def _finish_inference_run(
    cfg: dict[str, Any],
    run_dir: Path,
    *,
    output_dir: Path,
    artifacts: dict[str, Path],
    tables: dict[str, Path],
    prediction_plots: dict[str, Path],
    manifest_extra: dict[str, Any],
) -> RunResult:
    manifest_path = write_manifest(
        run_dir,
        config=cfg,
        metrics={},
        artifacts=artifacts,
        tables=tables,
        extra=manifest_extra,
    )
    artifacts["manifest"] = manifest_path
    if not cfg.get("runtime", {}).get("use_clearml"):
        update_latest(run_dir, output_dir / "latest_infer")

    return RunResult(
        run_dir=run_dir,
        metrics={},
        artifacts=artifacts,
        tables=tables,
        plots=prediction_plots,
        extra=manifest_extra,
    )
