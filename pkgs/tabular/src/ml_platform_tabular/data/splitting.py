"""Deterministic random, coordinate, group, time, and fixed holdout splitting."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def split_control_columns(cfg: dict[str, Any]) -> list[str]:
    split_cfg = cfg.get("split", {}) or {}
    method = str(split_cfg.get("method") or "random").strip().lower()
    setting = {"group": "group_column", "time": "time_column", "fixed": "valid_filter_column"}.get(method)
    if setting is None:
        return []
    column = split_cfg.get(setting)
    return [str(column)] if column is not None and str(column).strip() else []


def split_metadata(cfg: dict[str, Any], *, train_rows: int, valid_rows: int) -> dict[str, Any]:
    split_cfg = cfg.get("split", {}) or {}
    method = str(split_cfg.get("method") or "random").strip().lower()
    total_rows = train_rows + valid_rows
    return {
        "method": method,
        "train_rows": train_rows,
        "valid_rows": valid_rows,
        "valid_size": float(split_cfg.get("valid_size", 0.2)),
        "actual_valid_size": float(valid_rows / total_rows) if total_rows else 0.0,
        "group_column": split_cfg.get("group_column"),
        "time_column": split_cfg.get("time_column"),
        "valid_filter_column": split_cfg.get("valid_filter_column"),
        "valid_filter_value": split_cfg.get("valid_filter_value"),
    }


def train_valid_split(
    X: pd.DataFrame,
    y,
    cfg: dict[str, Any],
    df: pd.DataFrame | None = None,
    *,
    coordinate_columns: list[str] | None = None,
    target_labels: pd.Series | None = None,
):
    """Return a deterministic holdout without importing sklearn into the data layer."""
    method = str((cfg.get("split", {}) or {}).get("method") or "random").strip().lower()
    splitters = {
        "group": lambda: _group_split_indices(df, cfg),
        "time": lambda: _time_split_indices(df, cfg),
        "fixed": lambda: _fixed_split_indices(df, cfg),
    }
    if method == "random":
        train_idx, valid_idx = _random_split_indices(len(X), cfg, df=df, coordinate_columns=coordinate_columns)
    elif method in splitters:
        train_idx, valid_idx = splitters[method]()
    else:
        raise ValueError("split.method must be one of: random, group, time, fixed.")
    _validate_target_split(target_labels, train_idx, valid_idx)
    return X.iloc[train_idx], X.iloc[valid_idx], y.iloc[train_idx], y.iloc[valid_idx]


def _valid_size(cfg: dict[str, Any]) -> float:
    valid_size = float(cfg.get("split", {}).get("valid_size", 0.2))
    if not 0 < valid_size < 1:
        raise ValueError("split.valid_size must be between 0 and 1.")
    return valid_size


def _require_split_column(df: pd.DataFrame | None, column: Any, *, setting: str) -> tuple[pd.DataFrame, str]:
    if df is None:
        raise ValueError(f"{setting} requires the original dataframe for splitting.")
    if column is None or str(column).strip() == "":
        raise ValueError(f"{setting} is required for this split method.")
    name = str(column)
    if name not in df.columns:
        raise ValueError(f"{setting} not found: {name}")
    return df, name


def _check_non_empty_split(train_idx, valid_idx, *, method: str) -> None:
    if len(train_idx) == 0:
        raise ValueError(f"split.method={method} produced an empty training split.")
    if len(valid_idx) == 0:
        raise ValueError(f"split.method={method} produced an empty validation split.")


def _random_split_indices(
    row_count: int,
    cfg: dict[str, Any],
    *,
    df: pd.DataFrame | None = None,
    coordinate_columns: list[str] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    if coordinate_columns:
        return _coordinate_split_indices(df, coordinate_columns, cfg)
    rng = np.random.default_rng(int(cfg.get("run", {}).get("seed", 42)))
    indices = np.arange(row_count)
    rng.shuffle(indices)
    valid_count = max(1, round(len(indices) * _valid_size(cfg)))
    train_idx, valid_idx = indices[valid_count:], indices[:valid_count]
    if len(train_idx) == 0:
        raise ValueError("Training split is empty. Provide more rows or reduce split.valid_size.")
    return train_idx, valid_idx


def _coordinate_split_indices(
    df: pd.DataFrame | None,
    coordinate_columns: list[str],
    cfg: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    if df is None:
        raise ValueError("Coordinate-based random split requires the observation dataframe.")
    missing = [column for column in coordinate_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Coordinate columns not found: {missing}")
    coordinates = df[coordinate_columns].copy()
    coordinates["__split_seed__"] = int(cfg.get("run", {}).get("seed", 42))
    row_hashes = pd.util.hash_pandas_object(coordinates, index=False).to_numpy(dtype=np.uint64)
    coordinate_hashes = np.unique(row_hashes)
    if len(coordinate_hashes) < 2:
        raise ValueError("Coordinate-based random split requires at least two distinct coordinates.")
    valid_count = min(max(1, round(len(coordinate_hashes) * _valid_size(cfg))), len(coordinate_hashes) - 1)
    valid_hashes = set(np.sort(coordinate_hashes)[:valid_count].tolist())
    valid_mask = np.fromiter((value in valid_hashes for value in row_hashes), dtype=bool, count=len(row_hashes))
    return _masked_indices(valid_mask, method="random")


def _group_split_indices(df: pd.DataFrame | None, cfg: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    split_cfg = cfg.get("split", {}) or {}
    df, column = _require_split_column(df, split_cfg.get("group_column"), setting="split.group_column")
    groups = df[column].astype("object").where(df[column].notna(), "<MISSING>")
    unique_groups = np.array(sorted(groups.unique(), key=str), dtype=object)
    if len(unique_groups) < 2:
        raise ValueError("split.method=group requires at least two distinct groups.")
    rng = np.random.default_rng(int(cfg.get("run", {}).get("seed", 42)))
    rng.shuffle(unique_groups)
    valid_count = min(max(1, round(len(unique_groups) * _valid_size(cfg))), len(unique_groups) - 1)
    return _masked_indices(groups.isin(set(unique_groups[:valid_count])).to_numpy(), method="group")


def _time_split_indices(df: pd.DataFrame | None, cfg: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    split_cfg = cfg.get("split", {}) or {}
    df, column = _require_split_column(df, split_cfg.get("time_column"), setting="split.time_column")
    values = pd.to_datetime(df[column], errors="coerce")
    invalid_count = int(values.isna().sum())
    if invalid_count:
        raise ValueError(f"split.time_column contains {invalid_count} values that cannot be parsed as datetimes.")
    counts = values.value_counts(sort=False).sort_index()
    if len(counts) < 2:
        raise ValueError("split.method=time requires at least two distinct timestamps.")
    target_valid_rows = max(1, round(len(values) * _valid_size(cfg)))
    valid_rows_by_cutoff = counts.iloc[::-1].cumsum().iloc[::-1]
    cutoff = (valid_rows_by_cutoff.iloc[1:] - target_valid_rows).abs().idxmin()
    return _masked_indices(values.ge(cutoff).to_numpy(), method="time")


def _fixed_split_indices(df: pd.DataFrame | None, cfg: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    split_cfg = cfg.get("split", {}) or {}
    df, column = _require_split_column(df, split_cfg.get("valid_filter_column"), setting="split.valid_filter_column")
    filter_value = split_cfg.get("valid_filter_value")
    if filter_value is None or str(filter_value) == "":
        raise ValueError("split.valid_filter_value is required for split.method=fixed.")
    return _masked_indices(df[column].astype(str).eq(str(filter_value)).to_numpy(), method="fixed")


def _masked_indices(valid_mask: np.ndarray, *, method: str) -> tuple[np.ndarray, np.ndarray]:
    indices = np.arange(len(valid_mask))
    train_idx, valid_idx = indices[~valid_mask], indices[valid_mask]
    _check_non_empty_split(train_idx, valid_idx, method=method)
    return train_idx, valid_idx


def _validate_target_split(targets: pd.Series | None, train_idx, valid_idx) -> None:
    if targets is None:
        return
    target_names = set(targets.astype(str))
    missing_train = sorted(target_names - set(targets.iloc[train_idx].astype(str)))
    missing_valid = sorted(target_names - set(targets.iloc[valid_idx].astype(str)))
    if missing_train or missing_valid:
        raise ValueError(
            "Split must contain training and validation observations for every target "
            f"(missing_train={missing_train}, missing_valid={missing_valid})."
        )
