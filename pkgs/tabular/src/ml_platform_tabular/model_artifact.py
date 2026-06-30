from __future__ import annotations

from pathlib import Path
from typing import Any

from ml_platform_core.io import write_json


def default_model_path(output_dir: str | Path) -> Path:
    """Fallback model lookup path for local inference."""
    output_dir = Path(output_dir)
    return output_dir / "latest" / "model.joblib"


def write_model_info(
    path: str | Path,
    *,
    feature_columns: list[str],
    target_column: str | None,
    feature_preset: str,
    model_name: str,
    model_params: dict[str, Any] | None = None,
    artifact_kind: str = "model",
    extra: dict[str, Any] | None = None,
) -> Path:
    payload = {
        "feature_columns": feature_columns,
        "target_column": target_column,
        "feature_preset": feature_preset,
        "artifact_kind": artifact_kind,
        "model_name": model_name,
        "produced_model_name": model_name,
        "model_params": model_params or {},
        "best_model_name": model_name,
        "best_model_params": model_params or {},
    }
    if extra:
        payload.update(extra)
    return write_json(payload, path)
