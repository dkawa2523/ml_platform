from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml_platform_core.io import read_table
from ml_platform_core.value_coercion import as_str_list


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


def select_features(
    df: pd.DataFrame,
    *,
    target_column: str | None,
    feature_columns: list[str] | str | None,
    id_columns: list[str] | str | None = None,
    drop_columns: list[str] | str | None = None,
    passthrough_columns: list[str] | str | None = None,
) -> list[str]:
    id_columns = as_str_list(id_columns) or []
    feature_columns = as_str_list(feature_columns)
    drop_columns = as_str_list(drop_columns) or []
    passthrough_columns = as_str_list(passthrough_columns) or []

    _validate_columns_exist(df, drop_columns, "features.drop_columns not found")
    excluded = _excluded_feature_columns(id_columns, target_column, drop_columns)
    if feature_columns:
        return _select_explicit_features(df, feature_columns, drop_columns)

    _validate_passthrough_columns(df, passthrough_columns, drop_columns, excluded)
    return _select_default_features(df, excluded)


def _validate_columns_exist(df: pd.DataFrame, columns: list[str], message: str) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"{message}: {missing}")


def _excluded_feature_columns(
    id_columns: list[str],
    target_column: str | None,
    drop_columns: list[str],
) -> set[str]:
    excluded = set(id_columns)
    if target_column:
        excluded.add(target_column)
    excluded.update(drop_columns)
    return excluded


def _select_explicit_features(
    df: pd.DataFrame,
    feature_columns: list[str],
    drop_columns: list[str],
) -> list[str]:
    _validate_columns_exist(df, feature_columns, "feature_columns not found")
    overlap = sorted(set(feature_columns) & set(drop_columns))
    if overlap:
        raise ValueError(f"features.drop_columns cannot overlap Input/feature_columns: {overlap}")
    return feature_columns


def _validate_passthrough_columns(
    df: pd.DataFrame,
    passthrough_columns: list[str],
    drop_columns: list[str],
    excluded: set[str],
) -> None:
    overlap = sorted(set(passthrough_columns) & set(drop_columns))
    if overlap:
        raise ValueError(f"features.drop_columns cannot overlap passthrough_columns: {overlap}")
    _validate_columns_exist(df, passthrough_columns, "features.passthrough_columns not found")
    selected_passthrough = [col for col in passthrough_columns if col not in excluded]
    if len(selected_passthrough) != len(passthrough_columns):
        omitted = sorted(set(passthrough_columns) - set(selected_passthrough))
        raise ValueError(f"features.passthrough_columns must be selectable feature columns: {omitted}")


def _select_default_features(df: pd.DataFrame, excluded: set[str]) -> list[str]:
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


def _valid_size(cfg: dict[str, Any]) -> float:
    split_cfg = cfg.get("split", {})
    valid_size = float(split_cfg.get("valid_size", 0.2))
    if not 0 < valid_size < 1:
        raise ValueError("split.valid_size must be between 0 and 1.")
    return valid_size


def _require_split_column(df: pd.DataFrame | None, column: Any, *, setting: str) -> str:
    if df is None:
        raise ValueError(f"{setting} requires the original dataframe for splitting.")
    if column is None or str(column).strip() == "":
        raise ValueError(f"{setting} is required for this split method.")
    name = str(column)
    if name not in df.columns:
        raise ValueError(f"{setting} not found: {name}")
    return name


def _check_non_empty_split(train_idx, valid_idx, *, method: str) -> None:
    if len(train_idx) == 0:
        raise ValueError(f"split.method={method} produced an empty training split.")
    if len(valid_idx) == 0:
        raise ValueError(f"split.method={method} produced an empty validation split.")


def _random_split_indices(row_count: int, cfg: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    valid_size = _valid_size(cfg)
    seed = int(cfg.get("run", {}).get("seed", 42))
    rng = np.random.default_rng(seed)
    indices = np.arange(row_count)
    rng.shuffle(indices)
    valid_count = max(1, int(round(len(indices) * valid_size)))
    valid_idx = indices[:valid_count]
    train_idx = indices[valid_count:]
    if len(train_idx) == 0:
        raise ValueError("Training split is empty. Provide more rows or reduce split.valid_size.")
    return train_idx, valid_idx


def _group_split_indices(df: pd.DataFrame | None, cfg: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    split_cfg = cfg.get("split", {}) or {}
    group_column = _require_split_column(df, split_cfg.get("group_column"), setting="split.group_column")
    assert df is not None
    groups = df[group_column].astype("object").where(df[group_column].notna(), "<MISSING>")
    unique_groups = np.array(sorted(groups.unique(), key=lambda value: str(value)), dtype=object)
    if len(unique_groups) < 2:
        raise ValueError("split.method=group requires at least two distinct groups.")
    valid_size = _valid_size(cfg)
    seed = int(cfg.get("run", {}).get("seed", 42))
    rng = np.random.default_rng(seed)
    shuffled = unique_groups.copy()
    rng.shuffle(shuffled)
    valid_group_count = max(1, int(round(len(shuffled) * valid_size)))
    if valid_group_count >= len(shuffled):
        valid_group_count = len(shuffled) - 1
    valid_groups = set(shuffled[:valid_group_count])
    valid_mask = groups.isin(valid_groups).to_numpy()
    indices = np.arange(len(df))
    valid_idx = indices[valid_mask]
    train_idx = indices[~valid_mask]
    _check_non_empty_split(train_idx, valid_idx, method="group")
    return train_idx, valid_idx


def _time_split_indices(df: pd.DataFrame | None, cfg: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    split_cfg = cfg.get("split", {}) or {}
    time_column = _require_split_column(df, split_cfg.get("time_column"), setting="split.time_column")
    assert df is not None
    values = pd.to_datetime(df[time_column], errors="coerce")
    invalid_count = int(values.isna().sum())
    if invalid_count:
        raise ValueError(f"split.time_column contains {invalid_count} values that cannot be parsed as datetimes.")
    order = np.argsort(values.to_numpy(), kind="stable")
    valid_size = _valid_size(cfg)
    valid_count = max(1, int(round(len(order) * valid_size)))
    if valid_count >= len(order):
        valid_count = len(order) - 1
    train_idx = order[:-valid_count]
    valid_idx = order[-valid_count:]
    _check_non_empty_split(train_idx, valid_idx, method="time")
    return train_idx, valid_idx


def _fixed_split_indices(df: pd.DataFrame | None, cfg: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    split_cfg = cfg.get("split", {}) or {}
    filter_column = _require_split_column(
        df,
        split_cfg.get("valid_filter_column"),
        setting="split.valid_filter_column",
    )
    filter_value = split_cfg.get("valid_filter_value")
    if filter_value is None or str(filter_value) == "":
        raise ValueError("split.valid_filter_value is required for split.method=fixed.")
    assert df is not None
    valid_mask = df[filter_column].astype(str).eq(str(filter_value)).to_numpy()
    indices = np.arange(len(df))
    valid_idx = indices[valid_mask]
    train_idx = indices[~valid_mask]
    _check_non_empty_split(train_idx, valid_idx, method="fixed")
    return train_idx, valid_idx


def split_metadata(cfg: dict[str, Any], *, train_rows: int, valid_rows: int) -> dict[str, Any]:
    split_cfg = cfg.get("split", {}) or {}
    method = str(split_cfg.get("method") or "random").strip().lower()
    return {
        "method": method,
        "train_rows": int(train_rows),
        "valid_rows": int(valid_rows),
        "valid_size": float(split_cfg.get("valid_size", 0.2)),
        "group_column": split_cfg.get("group_column"),
        "time_column": split_cfg.get("time_column"),
        "valid_filter_column": split_cfg.get("valid_filter_column"),
        "valid_filter_value": split_cfg.get("valid_filter_value"),
    }


def train_valid_split(X: pd.DataFrame, y, cfg: dict[str, Any], df: pd.DataFrame | None = None):
    """Small deterministic holdout split without pulling sklearn into the data layer."""
    split_cfg = cfg.get("split", {}) or {}
    method = str(split_cfg.get("method") or "random").strip().lower()
    if method == "random":
        train_idx, valid_idx = _random_split_indices(len(X), cfg)
    elif method == "group":
        train_idx, valid_idx = _group_split_indices(df, cfg)
    elif method == "time":
        train_idx, valid_idx = _time_split_indices(df, cfg)
    elif method == "fixed":
        train_idx, valid_idx = _fixed_split_indices(df, cfg)
    else:
        raise ValueError("split.method must be one of: random, group, time, fixed.")
    return X.iloc[train_idx], X.iloc[valid_idx], y.iloc[train_idx], y.iloc[valid_idx]
