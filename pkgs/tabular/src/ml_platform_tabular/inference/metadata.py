from __future__ import annotations

from pathlib import Path
from typing import Any

from ml_platform_core.io import read_json


def read_json_if_exists(path: Path | None) -> dict[str, Any]:
    return read_json(path) if path is not None and path.exists() else {}


def model_info_path(cfg: dict[str, Any], model_path: Path) -> Path | None:
    explicit = cfg.get("model", {}).get("info_path")
    if explicit:
        return Path(explicit)
    if model_path.name.startswith("model_") and model_path.suffix == ".joblib":
        method = model_path.stem.removeprefix("model_")
        candidate = model_path.parent / f"model_info_{method}.json"
        if candidate.exists():
            return candidate
    candidate = model_path.parent / "model_info.json"
    return candidate if candidate.exists() else None


def load_model_info(cfg: dict[str, Any], model_path: Path) -> dict[str, Any]:
    path = model_info_path(cfg, model_path)
    if path is None:
        raise ValueError(f"model_info.json is required next to the model artifact: {model_path}")
    return read_json(path)


def known_target_column(cfg: dict[str, Any], model_info: dict[str, Any]) -> str | None:
    value = cfg.get("data", {}).get("target_column") or model_info.get("target_column")
    return str(value) if value else None
