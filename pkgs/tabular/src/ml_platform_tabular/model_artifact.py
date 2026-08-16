from __future__ import annotations

from pathlib import Path
from typing import Any

from ml_platform_core.artifacts import file_hash
from ml_platform_core.io import write_json

MODEL_ARTIFACT_SCHEMA_VERSION = 1


def default_model_path(output_dir: str | Path) -> Path:
    """Fallback model lookup path for local inference."""
    output_dir = Path(output_dir)
    return output_dir / "latest_training_pipeline" / "evaluate_models" / "best_model.joblib"


def write_model_info(
    path: str | Path,
    *,
    feature_columns: list[str],
    target_column: str | None,
    feature_preset: str,
    model_name: str,
    model_params: dict[str, Any] | None = None,
    artifact_kind: str = "model",
    model_path: str | Path | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    payload = {
        "model_artifact_schema_version": MODEL_ARTIFACT_SCHEMA_VERSION,
        "feature_columns": feature_columns,
        "target_column": target_column,
        "feature_preset": feature_preset,
        "artifact_kind": artifact_kind,
        "model_name": model_name,
        "model_params": model_params or {},
    }
    if model_path is not None:
        payload["model_sha256"] = file_hash(model_path)
    if extra:
        payload.update(extra)
    return write_json(payload, path)


def validate_model_artifact(
    model_path: str | Path,
    model_info: dict[str, Any],
    *,
    require_integrity: bool,
) -> None:
    """Validate artifact version and integrity before deserialization."""
    version = model_info.get("model_artifact_schema_version")
    expected_hash = model_info.get("model_sha256")
    if version is None and not require_integrity:
        return
    if version != MODEL_ARTIFACT_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported model artifact schema version: {version!r}; expected {MODEL_ARTIFACT_SCHEMA_VERSION}."
        )
    if not isinstance(expected_hash, str) or not expected_hash:
        raise ValueError("model_info.model_sha256 is required for this model artifact.")
    actual_hash = file_hash(model_path)
    if actual_hash != expected_hash:
        raise ValueError("Model artifact hash does not match model_info.model_sha256.")
