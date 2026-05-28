from __future__ import annotations

import hashlib
import json
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
from .model_artifact import default_model_path


PREDICTION_SCHEMA_VERSION = "v2.2"
RESERVED_PREDICTION_COLUMNS = {"prediction", "model_name", "artifact_kind", "model_artifact_id", "prediction_run_id"}


def _model_artifact_path(cfg: dict[str, Any], output_dir: Path) -> Path:
    value = cfg.get("model", {}).get("artifact_path")
    return Path(value) if value else default_model_path(output_dir)


def _model_info_path(cfg: dict[str, Any], model_path: Path) -> Path | None:
    value = cfg.get("model", {}).get("info_path")
    if value:
        return Path(value)
    candidate = model_path.parent / "model_info.json"
    return candidate if candidate.exists() else None


def _load_model_info(cfg: dict[str, Any], model_path: Path) -> dict[str, Any]:
    info_path = _model_info_path(cfg, model_path)
    return read_json(info_path) if info_path else {}


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

    info = _load_model_info(cfg, model_path)
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


def _as_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _chunk_size(cfg: dict[str, Any]) -> int | None:
    value = cfg.get("output", {}).get("chunk_size")
    if value in {None, ""}:
        return None
    chunk_size = int(value)
    if chunk_size < 1:
        raise ValueError("output.chunk_size must be >= 1 when set.")
    return chunk_size


def _model_artifact_id(model_info: dict[str, Any], model_path: Path) -> str:
    if model_info:
        payload = {
            "artifact_kind": model_info.get("artifact_kind"),
            "model_name": model_info.get("model_name") or model_info.get("best_model_name"),
            "model_params": model_info.get("model_params") or model_info.get("best_model_params"),
            "produced_model_name": model_info.get("produced_model_name"),
            "search": model_info.get("search"),
            "ensemble_method": model_info.get("ensemble_method"),
            "selected_base_models": model_info.get("selected_base_models"),
        }
    else:
        payload = {"model_path": str(model_path)}
    text = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _prediction_frame(df, y_pred, *, model_info: dict[str, Any], run_id: str, model_artifact_id: str):
    conflicts = [column for column in RESERVED_PREDICTION_COLUMNS if column in df.columns]
    if conflicts:
        raise ValueError(f"Input table contains reserved prediction output columns: {conflicts}")
    model_name = str(model_info.get("model_name") or model_info.get("best_model_name") or "unknown")
    artifact_kind = str(model_info.get("artifact_kind") or "model")
    out = df.copy()
    out["prediction"] = y_pred
    out["model_name"] = model_name
    out["artifact_kind"] = artifact_kind
    out["model_artifact_id"] = model_artifact_id
    out["prediction_run_id"] = str(run_id)
    return out


def _write_chunked_predictions(path: Path, df, estimator, features: list[str], chunk_size: int, *, model_info: dict[str, Any], run_id: str, model_artifact_id: str) -> Path:
    if path.suffix.lower() != ".csv":
        raise ValueError("output.chunk_size currently supports CSV prediction output only.")
    path.parent.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(df), chunk_size):
        chunk = df.iloc[start : start + chunk_size]
        y_pred = estimator.predict(chunk[features])
        frame = _prediction_frame(chunk, y_pred, model_info=model_info, run_id=run_id, model_artifact_id=model_artifact_id)
        frame.to_csv(path, index=False, mode="w" if start == 0 else "a", header=start == 0)
    if len(df) == 0:
        frame = _prediction_frame(df, [], model_info=model_info, run_id=run_id, model_artifact_id=model_artifact_id)
        frame.to_csv(path, index=False)
    return path


def run_infer(cfg: dict[str, Any]) -> RunResult:
    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    run_name = cfg.get("run", {}).get("name", "tabular_infer")
    run_dir = prepare_run_dir(output_dir, run_name)

    model_path = _model_artifact_path(cfg, output_dir)
    estimator = load_joblib(model_path)
    model_info = _load_model_info(cfg, model_path)

    df = load_dataset(cfg)
    features = _features_for_inference(df, cfg, model_path)

    prediction_name = cfg.get("output", {}).get("prediction_name", "predictions.csv")
    model_artifact_id = _model_artifact_id(model_info, model_path)
    chunk_size = _chunk_size(cfg)
    if chunk_size:
        predictions_path = _write_chunked_predictions(
            run_dir / prediction_name,
            df,
            estimator,
            features,
            chunk_size,
            model_info=model_info,
            run_id=run_dir.name,
            model_artifact_id=model_artifact_id,
        )
    else:
        y_pred = estimator.predict(df[features])
        prediction_frame = _prediction_frame(
            df,
            y_pred,
            model_info=model_info,
            run_id=run_dir.name,
            model_artifact_id=model_artifact_id,
        )
        predictions_path = write_table(prediction_frame, run_dir / prediction_name)
    config_path = write_config_snapshot(cfg, run_dir)

    artifacts = {
        "config": config_path,
    }
    info_path = _model_info_path(cfg, model_path)
    if info_path:
        artifacts["model_info"] = info_path
    manifest_inputs = {
        **artifacts,
        "model_source": model_path,
    }
    tables = {"predictions": predictions_path}
    data_cfg = cfg.get("data", {})
    manifest_extra = {
        "prediction_rows": int(len(df)),
        "prediction_file": prediction_name,
        "prediction_schema_version": PREDICTION_SCHEMA_VERSION,
        "model_source": str(model_path),
        "model_name": str(model_info.get("model_name") or model_info.get("best_model_name") or "unknown"),
        "artifact_kind": str(model_info.get("artifact_kind") or "model"),
        "model_artifact_id": model_artifact_id,
        "feature_columns": features,
        "id_columns": _as_list(data_cfg.get("id_columns")),
        "target_column": data_cfg.get("target_column"),
        "chunk_size": chunk_size,
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
        extra=manifest_extra,
    )
