from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from ml_platform_core.artifacts import (
    prepare_run_dir,
    update_latest,
    write_config_snapshot,
    write_manifest,
)
from ml_platform_core.io import load_joblib, read_json, read_table, write_table
from ml_platform_core.result import RunResult

from .data import load_dataset, select_features
from .model_artifact import default_model_path
from .plots import write_prediction_summary_tables


PREDICTION_SCHEMA_VERSION = "v2.2"
RESERVED_PREDICTION_COLUMNS = {"prediction", "model_name", "artifact_kind", "model_artifact_id", "prediction_run_id"}


def _safe_name(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value)
    return safe or "model"


def _model_selector(cfg: dict[str, Any]) -> str:
    return str(cfg.get("model", {}).get("model_selector") or "best").strip()


def _model_source_type(cfg: dict[str, Any]) -> str:
    return str(cfg.get("model", {}).get("source_type") or "local_path").strip()


def _is_url(value: str) -> bool:
    return "://" in value


def _json_path(cfg: dict[str, Any], key: str) -> Path | None:
    value = cfg.get("model", {}).get(key)
    return Path(value) if value else None


def _read_json_if_exists(path: Path | None) -> dict[str, Any]:
    if path is not None and path.exists():
        return read_json(path)
    return {}


def _info_says_ensemble(path: Path) -> bool:
    info_path = path.parent / "model_info.json"
    info = _read_json_if_exists(info_path)
    return str(info.get("artifact_kind") or "").lower() == "ensemble"


def _ensemble_selector_parts(selector: str) -> tuple[bool, str | None]:
    if selector == "ensemble":
        return True, None
    if selector.startswith("ensemble:"):
        method = selector.split(":", 1)[1].strip()
        if not method:
            raise ValueError("model_selector=ensemble:<method> requires a method name.")
        return True, method
    return False, None


def _best_ensemble_from_refs(build_dir: Path) -> Path | None:
    refs = _read_json_if_exists(build_dir / "ensemble_refs.json")
    best = refs.get("best_ensemble") if isinstance(refs, dict) else None
    if isinstance(best, dict) and best.get("model"):
        path = Path(str(best["model"]))
        if path.exists():
            return path
        candidate = build_dir / path.name
        if candidate.exists():
            return candidate
    return None


def _ensemble_model_candidates(directory: Path, selector: str) -> list[Path]:
    _, method = _ensemble_selector_parts(selector)
    build_dirs = [directory / "build_ensemble", directory]
    candidates: list[Path] = []
    for build_dir in build_dirs:
        if method:
            candidates.append(build_dir / f"model_{method}.joblib")
        else:
            best = _best_ensemble_from_refs(build_dir)
            if best is not None:
                candidates.append(best)
            candidates.append(build_dir / "model.joblib")
    return candidates


def _selector_candidates(directory: Path, selector: str) -> list[Path]:
    selector = selector.strip()
    if selector == "best":
        return [
            directory / "evaluate_models" / "best_model.joblib",
            directory / "best_model.joblib",
            directory / "model.joblib",
        ]
    is_ensemble, _ = _ensemble_selector_parts(selector)
    if is_ensemble:
        return _ensemble_model_candidates(directory, selector)
    return [
        directory / f"train_{_safe_name(selector)}" / "model.joblib",
        directory / f"train_{selector}" / "model.joblib",
        directory / "model.joblib",
    ]


def _resolve_directory_model_path(directory: Path, selector: str, *, strict: bool = True) -> Path | None:
    for candidate in _selector_candidates(directory, selector):
        if not candidate.exists():
            continue
        is_ensemble, _ = _ensemble_selector_parts(selector)
        if is_ensemble and candidate.name == "model.joblib" and candidate.parent == directory:
            if not _info_says_ensemble(candidate):
                continue
        if selector != "best" and not is_ensemble and candidate.parent == directory:
            info = _read_json_if_exists(candidate.parent / "model_info.json")
            name = str(info.get("model_name") or info.get("best_model_name") or "")
            if name and name != selector:
                continue
        return candidate
    if strict:
        raise ValueError(f"Could not resolve model_selector={selector!r} under directory: {directory}")
    return None


def _path_from_value(value: Any, selector: str, *, strict: bool = True) -> Path | None:
    if not value:
        return None
    text = str(value)
    if _is_url(text):
        raise ValueError("Remote model URLs must be resolved by clearml/adapter.py before package inference.")
    path = Path(text)
    if path.is_dir():
        return _resolve_directory_model_path(path, selector, strict=strict)
    return path


def _latest_training_pipeline_model(output_dir: Path, selector: str) -> Path | None:
    latest_training = output_dir / "latest_training_pipeline"
    if not latest_training.exists():
        return None
    return _resolve_directory_model_path(latest_training, selector, strict=selector != "best")


def _model_artifact_path(cfg: dict[str, Any], output_dir: Path) -> Path:
    model_cfg = cfg.get("model", {})
    selector = _model_selector(cfg)
    for key in ("artifact_path", "local_model_path", "model_artifact_url"):
        path = _path_from_value(model_cfg.get(key), selector)
        if path is not None:
            return path

    latest_training = _latest_training_pipeline_model(output_dir, selector)
    if latest_training is not None:
        return latest_training
    return default_model_path(output_dir)


def _model_info_path(cfg: dict[str, Any], model_path: Path) -> Path | None:
    value = cfg.get("model", {}).get("info_path")
    if value:
        return Path(value)
    if model_path.name.startswith("model_") and model_path.suffix == ".joblib":
        method = model_path.stem.replace("model_", "", 1)
        for candidate in (
            model_path.parent / f"model_info_{method}.json",
            model_path.parent / f"ensemble_info_{method}.json",
        ):
            if candidate.exists():
                return candidate
    for candidate in (
        model_path.parent / "model_info.json",
        model_path.parent / "best_model.json",
        model_path.parent / "ensemble_info.json",
    ):
        if candidate.exists():
            return candidate
    return None


def _load_model_info(cfg: dict[str, Any], model_path: Path) -> dict[str, Any]:
    info_path = _model_info_path(cfg, model_path)
    return read_json(info_path) if info_path else {}


def _feature_spec_path(cfg: dict[str, Any], model_path: Path) -> Path | None:
    explicit = _json_path(cfg, "feature_spec_path")
    if explicit:
        return explicit
    for candidate in (
        model_path.parent / "feature_spec.json",
        model_path.parent.parent / "preprocess_features" / "feature_spec.json",
    ):
        if candidate.exists():
            return candidate
    return None


def _preprocess_bundle_path(cfg: dict[str, Any], model_path: Path) -> Path | None:
    explicit = _json_path(cfg, "preprocess_bundle_path")
    if explicit:
        return explicit
    for candidate in (
        model_path.parent / "preprocess_bundle.joblib",
        model_path.parent.parent / "preprocess_features" / "preprocess_bundle.joblib",
    ):
        if candidate.exists():
            return candidate
    return None


def _load_feature_spec(cfg: dict[str, Any], model_path: Path) -> dict[str, Any]:
    return _read_json_if_exists(_feature_spec_path(cfg, model_path))


def _load_preprocess_bundle(cfg: dict[str, Any], model_path: Path) -> dict[str, Any]:
    path = _preprocess_bundle_path(cfg, model_path)
    if path is None or not path.exists():
        return {}
    bundle = load_joblib(path)
    return bundle if isinstance(bundle, dict) else {}


def _estimator_feature_columns(estimator: Any) -> list[str] | None:
    columns = getattr(estimator, "feature_columns", None)
    if isinstance(columns, list):
        return [str(col) for col in columns]
    estimators = getattr(estimator, "estimators", None)
    if estimators:
        columns = getattr(estimators[0], "feature_columns", None)
        if isinstance(columns, list):
            return [str(col) for col in columns]
    return None


def _features_for_inference(
    df,
    cfg: dict[str, Any],
    *,
    model_path: Path,
    estimator: Any,
    model_info: dict[str, Any],
    feature_spec: dict[str, Any],
    preprocess_bundle: dict[str, Any],
) -> list[str]:
    data_cfg = cfg.get("data", {})
    explicit = data_cfg.get("feature_columns")
    if explicit:
        return select_features(
            df,
            target_column=data_cfg.get("target_column"),
            feature_columns=explicit,
            id_columns=data_cfg.get("id_columns"),
        )

    for feature_columns in (
        model_info.get("feature_columns"),
        _estimator_feature_columns(estimator),
        feature_spec.get("feature_columns"),
        preprocess_bundle.get("feature_columns"),
    ):
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
    feature_spec = _load_feature_spec(cfg, model_path)
    preprocess_bundle = _load_preprocess_bundle(cfg, model_path)

    df = load_dataset(cfg)
    features = _features_for_inference(
        df,
        cfg,
        model_path=model_path,
        estimator=estimator,
        model_info=model_info,
        feature_spec=feature_spec,
        preprocess_bundle=preprocess_bundle,
    )

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
    prediction_tables, prediction_plots = write_prediction_summary_tables(
        predictions_path,
        run_dir,
        target_column=cfg.get("data", {}).get("target_column"),
    )
    prediction_summary_path = prediction_tables["prediction_summary"]
    config_path = write_config_snapshot(cfg, run_dir)

    artifacts = {
        "config": config_path,
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
    data_cfg = cfg.get("data", {})
    model_cfg = cfg.get("model", {})
    manifest_extra = {
        "prediction_rows": int(len(df)),
        "prediction_file": prediction_name,
        "prediction_summary": str(prediction_summary_path),
        "prediction_schema_version": PREDICTION_SCHEMA_VERSION,
        "source_type": _model_source_type(cfg),
        "source_task_id": model_cfg.get("source_task_id"),
        "model_selector": _model_selector(cfg),
        "model_artifact_url": model_cfg.get("model_artifact_url"),
        "clearml_model_id": model_cfg.get("clearml_model_id"),
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
        "id_columns": _as_list(data_cfg.get("id_columns")),
        "target_column": data_cfg.get("target_column"),
        "chunk_size": chunk_size,
    }
    source_summary_path = write_table(
        pd.DataFrame(
            [
                {"field": "source_type", "value": manifest_extra["source_type"]},
                {"field": "source_task_id", "value": manifest_extra["source_task_id"]},
                {"field": "model_selector", "value": manifest_extra["model_selector"]},
                {"field": "artifact_kind", "value": manifest_extra["artifact_kind"]},
                {"field": "model_name", "value": manifest_extra["model_name"]},
                {"field": "ensemble_method", "value": manifest_extra["ensemble_method"]},
                {"field": "resolved_model_path", "value": manifest_extra["resolved_model_path"]},
                {"field": "model_artifact_id", "value": manifest_extra["model_artifact_id"]},
                {"field": "feature_spec_path", "value": manifest_extra["feature_spec_path"]},
                {"field": "preprocess_bundle_path", "value": manifest_extra["preprocess_bundle_path"]},
            ]
        ),
        run_dir / "source_summary.csv",
    )
    tables = {"predictions": predictions_path, **prediction_tables, "source_summary": source_summary_path}
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
