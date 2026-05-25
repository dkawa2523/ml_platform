from __future__ import annotations

from pathlib import Path
from typing import Any

from ml_platform_core.io import read_json, write_json


def default_model_path(output_dir: str | Path) -> Path:
    """Default model lookup path for downstream eval/infer tasks.

    `outputs/latest` always means the latest run of any task. To avoid eval/infer
    overwriting the trained model lookup, train also writes `outputs/latest_train`.
    """
    output_dir = Path(output_dir)
    preferred = output_dir / "latest_train" / "model.joblib"
    fallback = output_dir / "latest" / "model.joblib"
    return preferred if preferred.exists() else fallback


def model_info_path(model_path: str | Path) -> Path:
    return Path(model_path).with_name("model_info.json")


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
        "model_params": model_params or {},
        "best_model_name": model_name,
        "best_model_params": model_params or {},
    }
    if extra:
        payload.update(extra)
    return write_json(payload, path)


def load_model_info_for_model(model_path: str | Path) -> dict[str, Any]:
    info_path = model_info_path(model_path)
    if info_path.exists():
        return read_json(info_path)
    return {}


def feature_columns_from_model_info(model_path: str | Path) -> list[str] | None:
    info = load_model_info_for_model(model_path)
    columns = info.get("feature_columns")
    if isinstance(columns, list):
        return [str(c) for c in columns]
    return None
