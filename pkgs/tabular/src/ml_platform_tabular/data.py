from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml_platform_core.io import read_table


def resolve_data_path(cfg: dict[str, Any]) -> Path:
    """Resolve local data path.

    ClearML Dataset ID should be converted to local_path by clearml/adapter.py before
    pkgs are called. Relative paths are resolved by the current working directory.
    """
    data_cfg = cfg.get("data", {})
    local_path = data_cfg.get("local_path")
    if not local_path:
        raise ValueError("data.local_path is required after runtime resolution.")
    return Path(local_path)


def load_dataset(cfg: dict[str, Any]) -> pd.DataFrame:
    data_cfg = cfg.get("data", {})
    return read_table(resolve_data_path(cfg), preferred_name=data_cfg.get("dataset_file"))


def _normalize_columns(value: Any) -> list[str] | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    if isinstance(value, list):
        return [str(v) for v in value]
    raise ValueError(f"Column list must be null, string, or list: {value!r}")


def select_features(
    df: pd.DataFrame,
    *,
    target_column: str | None,
    feature_columns: list[str] | str | None,
    id_columns: list[str] | str | None = None,
    drop_columns: list[str] | str | None = None,
    passthrough_columns: list[str] | str | None = None,
) -> list[str]:
    id_columns = _normalize_columns(id_columns) or []
    feature_columns = _normalize_columns(feature_columns)
    drop_columns = _normalize_columns(drop_columns) or []
    passthrough_columns = _normalize_columns(passthrough_columns) or []

    missing_drop = [col for col in drop_columns if col not in df.columns]
    if missing_drop:
        raise ValueError(f"features.drop_columns not found: {missing_drop}")

    excluded = set(id_columns)
    if target_column:
        excluded.add(target_column)
    excluded.update(drop_columns)

    if feature_columns:
        missing = [col for col in feature_columns if col not in df.columns]
        if missing:
            raise ValueError(f"feature_columns not found: {missing}")
        overlap = sorted(set(feature_columns) & set(drop_columns))
        if overlap:
            raise ValueError(f"features.drop_columns cannot overlap Input/feature_columns: {overlap}")
        return feature_columns

    overlap = sorted(set(passthrough_columns) & set(drop_columns))
    if overlap:
        raise ValueError(f"features.drop_columns cannot overlap passthrough_columns: {overlap}")
    missing_passthrough = [col for col in passthrough_columns if col not in df.columns]
    if missing_passthrough:
        raise ValueError(f"features.passthrough_columns not found: {missing_passthrough}")
    selected_passthrough = [col for col in passthrough_columns if col not in excluded]
    if len(selected_passthrough) != len(passthrough_columns):
        omitted = sorted(set(passthrough_columns) - set(selected_passthrough))
        raise ValueError(f"features.passthrough_columns must be selectable feature columns: {omitted}")

    features = [col for col in df.columns if col not in excluded]
    if not features:
        raise ValueError("No feature columns were selected.")
    return features


def split_xy(df: pd.DataFrame, cfg: dict[str, Any]):
    data_cfg = cfg.get("data", {})
    target_column = data_cfg.get("target_column")
    if not target_column:
        raise ValueError("data.target_column is required for train/evaluate.")
    if target_column not in df.columns:
        raise ValueError(f"target_column not found: {target_column}")

    features = select_features(
        df,
        target_column=target_column,
        feature_columns=data_cfg.get("feature_columns"),
        id_columns=data_cfg.get("id_columns"),
        drop_columns=cfg.get("features", {}).get("drop_columns"),
        passthrough_columns=cfg.get("features", {}).get("passthrough_columns"),
    )
    X = df[features]
    y = df[target_column]
    return X, y, features


def train_valid_split(X: pd.DataFrame, y, cfg: dict[str, Any]):
    """Small deterministic split to avoid pulling sklearn into the MVP data layer."""
    split_cfg = cfg.get("split", {})
    valid_size = float(split_cfg.get("valid_size", 0.2))
    if not 0 < valid_size < 1:
        raise ValueError("split.valid_size must be between 0 and 1.")
    seed = int(cfg.get("run", {}).get("seed", 42))
    rng = np.random.default_rng(seed)
    indices = np.arange(len(X))
    rng.shuffle(indices)
    valid_count = max(1, int(round(len(indices) * valid_size)))
    valid_idx = indices[:valid_count]
    train_idx = indices[valid_count:]
    if len(train_idx) == 0:
        raise ValueError("Training split is empty. Provide more rows or reduce split.valid_size.")
    return X.iloc[train_idx], X.iloc[valid_idx], y.iloc[train_idx], y.iloc[valid_idx]
