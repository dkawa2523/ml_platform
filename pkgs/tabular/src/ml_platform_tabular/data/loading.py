"""Dataset and target-source manifest loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from ml_platform_core.config import load_yaml
from ml_platform_core.io import read_table

from ..target_sources import SOURCE_ROW_COLUMN, TARGET_COLUMN, VALUE_COLUMN, load_target_sources


def resolve_data_path(cfg: dict[str, Any]) -> Path:
    """Return the local path after the runtime layer has resolved remote data."""
    local_path = cfg.get("data", {}).get("local_path")
    if not local_path:
        raise ValueError("data.local_path is required after runtime resolution.")
    return Path(local_path)


def load_dataset(cfg: dict[str, Any]) -> pd.DataFrame:
    data_cfg = cfg.get("data", {})
    return read_table(resolve_data_path(cfg), preferred_name=data_cfg.get("dataset_file"))


def load_training_observations(
    cfg: dict[str, Any],
) -> tuple[pd.DataFrame, str, list[str], dict[str, Any] | None]:
    """Return one logical observation frame for scalar or target-source input."""
    manifest = _source_manifest(cfg)
    if manifest is not None:
        frame = load_target_sources(resolve_data_path(cfg), manifest)
        coordinates = [
            column for column in frame.columns if column not in {TARGET_COLUMN, VALUE_COLUMN, SOURCE_ROW_COLUMN}
        ]
        return frame, VALUE_COLUMN, coordinates, manifest

    frame = load_dataset(cfg).copy()
    target_column = str(cfg.get("data", {}).get("target_column") or "").strip()
    if not target_column:
        raise ValueError("Set exactly one of data.target_column or data.source_manifest for training.")
    conflicts = [column for column in (TARGET_COLUMN, SOURCE_ROW_COLUMN) if column in frame.columns]
    if conflicts:
        raise ValueError(f"Scalar input uses reserved target-source columns: {conflicts}")
    frame[SOURCE_ROW_COLUMN] = np.arange(len(frame), dtype=np.int64)
    return frame, target_column, [], None


def load_inference_dataset(cfg: dict[str, Any]) -> pd.DataFrame:
    manifest = _source_manifest(cfg)
    if manifest is None:
        return load_dataset(cfg)
    return load_target_sources(resolve_data_path(cfg), manifest, require_values=False)


def _source_manifest(cfg: dict[str, Any]) -> dict[str, Any] | None:
    data_cfg = cfg.get("data", {}) or {}
    name = data_cfg.get("source_manifest")
    if name is None or name == "":
        return None
    if not isinstance(name, str):
        raise ValueError("data.source_manifest must be a relative YAML or JSON file name.")
    if data_cfg.get("target_column"):
        raise ValueError("data.target_column and data.source_manifest are mutually exclusive.")

    root = resolve_data_path(cfg).resolve()
    if not root.is_dir():
        raise ValueError("data.local_path must be a dataset directory when data.source_manifest is set.")
    path = _manifest_path(root, name)
    return load_yaml(path)


def _manifest_path(root: Path, name: str) -> Path:
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("data.source_manifest must stay within data.local_path.")
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("data.source_manifest must stay within data.local_path.") from exc
    return path
