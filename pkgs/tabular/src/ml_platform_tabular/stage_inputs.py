from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from ml_platform_core.io import load_joblib, read_json, read_table

from .target_sources import SOURCE_ROW_COLUMN, TARGET_COLUMN
from .training.artifacts import CandidateResult, PreprocessResult, safe_name


def json_value(value: Any, *, default: Any) -> Any:
    if value is None or value == "":
        return default
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return default
        return json.loads(text)
    return value


def stage_inputs(cfg: dict[str, Any]) -> dict[str, Any]:
    inputs = cfg.get("stage_inputs") or {}
    if not isinstance(inputs, dict):
        raise ValueError("stage_inputs must be a mapping.")
    return inputs


def required_path(inputs: dict[str, Any], key: str) -> Path:
    value = inputs.get(key)
    if not value:
        raise ValueError(f"stage_inputs.{key} is required for this stage.")
    return _checked_path(value, f"stage_inputs.{key}")


def load_preprocess(cfg: dict[str, Any]) -> PreprocessResult:
    inputs = stage_inputs(cfg)
    bundle_path = required_path(inputs, "preprocess_bundle")
    processed_train_path = required_path(inputs, "processed_train")
    processed_valid_path = required_path(inputs, "processed_valid")
    bundle = _preprocess_bundle(bundle_path)
    train_df = read_table(processed_train_path)
    valid_df = read_table(processed_valid_path)
    target_column, feature_columns, input_columns = _preprocess_columns(bundle, train_df)
    return _preprocess_result(
        bundle,
        train_df,
        valid_df,
        target_column,
        feature_columns,
        input_columns,
        bundle_path,
        processed_train_path,
        processed_valid_path,
    )


def _preprocess_bundle(path: Path) -> dict[str, Any]:
    bundle = load_joblib(path)
    if not isinstance(bundle, Mapping):
        raise ValueError("preprocess_bundle must contain a mapping.")
    return dict(bundle)


def _preprocess_columns(bundle: Mapping[str, Any], train_df) -> tuple[str, list[str], list[str]]:
    target_column = bundle.get("target_column")
    if not target_column:
        raise ValueError("preprocess_bundle.target_column is required.")
    target_column = str(target_column)
    feature_columns = bundle.get("feature_columns")
    if not feature_columns:
        feature_columns = [col for col in train_df.columns if col != target_column]
    feature_columns = [str(column) for column in feature_columns]
    metadata_columns = [column for column in (TARGET_COLUMN, SOURCE_ROW_COLUMN) if column in train_df.columns]
    input_columns = [*feature_columns, *metadata_columns]
    return target_column, feature_columns, input_columns


def _preprocess_result(
    bundle: Mapping[str, Any],
    train_df,
    valid_df,
    target_column: str,
    feature_columns: list[str],
    input_columns: list[str],
    bundle_path: Path,
    processed_train_path: Path,
    processed_valid_path: Path,
) -> PreprocessResult:
    target_names = bundle.get("target_names") or [target_column]
    coordinate_columns = bundle.get("coordinate_columns") or []
    return PreprocessResult(
        transformer=bundle["transformer"],
        feature_columns=feature_columns,
        target_column=target_column,
        target_names=[str(name) for name in target_names],
        coordinate_columns=[str(name) for name in coordinate_columns],
        id_columns=[str(name) for name in (bundle.get("id_columns") or [])],
        feature_preset=bundle.get("feature_preset", "basic"),
        feature_config=bundle.get("feature_config", {}),
        X_train=train_df[input_columns],
        X_valid=valid_df[input_columns],
        y_train=train_df[target_column],
        y_valid=valid_df[target_column],
        artifacts={
            "preprocess_bundle": bundle_path,
        },
        tables={
            "processed_train": processed_train_path,
            "processed_valid": processed_valid_path,
        },
    )


def model_refs(inputs: dict[str, Any]) -> list[CandidateResult]:
    refs = [_model_ref(item) for item in _refs_array(inputs, "model_refs")]
    if not refs:
        raise ValueError("stage_inputs.model_refs must contain at least one model ref.")
    return refs


def ensemble_refs(inputs: dict[str, Any]) -> list[CandidateResult]:
    return [_ensemble_reference(item) for item in _refs_array(inputs, "ensemble_refs")]


def _refs_array(inputs: dict[str, Any], key: str) -> list[dict[str, Any]]:
    raw = json_value(inputs.get(key), default=[])
    if not raw:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"stage_inputs.{key} must be a JSON array.")
    return [_ref_item(item, key, index) for index, item in enumerate(raw)]


def _ref_item(item: Any, key: str, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError(f"stage_inputs.{key}[{index}] must be a mapping.")
    return dict(item)


def _model_ref(item: dict[str, Any]) -> CandidateResult:
    model_path = _checked_path(item.get("model"), "Model ref artifact")
    metrics_path = _checked_path(item.get("metrics"), "Metrics ref", must_exist=False)
    model_info_path = _optional_path(item, "model_info", label="Model info ref")
    metrics = _read_existing_json(metrics_path)
    model_info = _read_existing_json(model_info_path)
    model_name = _model_name(item, model_info, model_path)
    model_params = _model_params(item, model_info, model_name)
    return CandidateResult(
        stage=str(item.get("stage") or f"train_{safe_name(model_name)}"),
        model_name=model_name,
        ensemble_method=item.get("ensemble_method"),
        model_params=dict(model_params),
        artifact_kind=str(item.get("artifact_kind") or model_info.get("artifact_kind") or "model"),
        estimator=load_joblib(model_path),
        metrics=metrics,
        artifacts={
            "model": model_path,
            "metrics": metrics_path,
            **({"model_info": model_info_path} if model_info_path is not None else {}),
        },
        tables=_prediction_tables(item),
    )


def _checked_path(value: Any, label: str, *, must_exist: bool = True) -> Path:
    if not value:
        raise ValueError(f"{label} is required.")
    text = str(value)
    if "${" in text:
        raise ValueError(f"{label} still contains an unresolved ClearML placeholder: {text}")
    path = Path(text)
    if must_exist and not path.exists():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    return path


def _optional_path(item: dict[str, Any], key: str, *, label: str) -> Path | None:
    value = item.get(key)
    if not value:
        return None
    return _checked_path(value, label, must_exist=False)


def _read_existing_json(path: Path | None) -> dict[str, Any]:
    return read_json(path) if path and path.exists() else {}


def _model_name(item: dict[str, Any], model_info: dict[str, Any], model_path: Path) -> str:
    return str(item.get("model_name") or model_info.get("model_name") or model_path.parent.name.replace("train_", ""))


def _model_params(item: dict[str, Any], model_info: dict[str, Any], model_name: str) -> dict[str, Any]:
    params = item.get("model_params")
    if params is None:
        params = model_info.get("model_params") or {}
    if not isinstance(params, dict):
        raise ValueError(f"model_params for {model_name} must be a mapping.")
    return dict(params)


def _prediction_tables(item: dict[str, Any]) -> dict[str, Path]:
    path = _optional_path(item, "validation_predictions", label="Validation predictions ref")
    return {"validation_predictions": path} if path is not None else {}


def _ensemble_reference(item: dict[str, Any]) -> CandidateResult:
    ref = replace(_model_ref(item), artifact_kind="ensemble")
    artifacts = dict(ref.artifacts)
    tables = dict(ref.tables)
    ensemble_predictions = _optional_path(item, "ensemble_predictions", label="Ensemble predictions ref")
    if ensemble_predictions is not None:
        tables["ensemble_predictions"] = ensemble_predictions
    return replace(ref, artifacts=artifacts, tables=tables)
