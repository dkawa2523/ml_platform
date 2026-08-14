from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from ml_platform_core.config import load_yaml
from ml_platform_core.io import read_table
from ml_platform_core.value_coercion import as_str_list

from .target_sources import (
    SOURCE_ROW_COLUMN,
    TARGET_COLUMN,
    VALUE_COLUMN,
    load_target_sources,
)


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


def load_training_observations(
    cfg: dict[str, Any],
) -> tuple[pd.DataFrame, str, list[str], dict[str, Any] | None]:
    """Return one logical observation frame for scalar or target-source input."""
    manifest = _source_manifest(cfg)
    if manifest is not None:
        frame = load_target_sources(resolve_data_path(cfg), manifest)
        coordinate_columns = [
            column for column in frame.columns if column not in {TARGET_COLUMN, VALUE_COLUMN, SOURCE_ROW_COLUMN}
        ]
        return frame, VALUE_COLUMN, coordinate_columns, manifest

    frame = load_dataset(cfg).copy()
    target_column = str(cfg.get("data", {}).get("target_column") or "").strip()
    if not target_column:
        raise ValueError("Set exactly one of data.target_column or data.source_manifest for training.")
    conflicts = [column for column in (TARGET_COLUMN, SOURCE_ROW_COLUMN) if column in frame.columns]
    if conflicts:
        raise ValueError(f"Scalar input uses reserved target-source columns: {conflicts}")
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
    relative = Path(str(name))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("data.source_manifest must stay within data.local_path.")
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("data.source_manifest must stay within data.local_path.") from exc
    return load_yaml(path)


def select_features(
    df: pd.DataFrame,
    *,
    target_column: str | None,
    feature_columns: list[str] | str | None,
    id_columns: list[str] | str | None = None,
    drop_columns: list[str] | str | None = None,
    passthrough_columns: list[str] | str | None = None,
    split_columns: list[str] | str | None = None,
) -> list[str]:
    id_columns = as_str_list(id_columns) or []
    feature_columns = as_str_list(feature_columns)
    drop_columns = as_str_list(drop_columns) or []
    passthrough_columns = as_str_list(passthrough_columns) or []
    split_columns = as_str_list(split_columns) or []

    _validate_columns_exist(df, drop_columns, "features.drop_columns not found")
    excluded = _excluded_feature_columns(id_columns, target_column, drop_columns, split_columns)
    if feature_columns:
        return _select_explicit_features(df, feature_columns, drop_columns, excluded)

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
    split_columns: list[str],
) -> set[str]:
    excluded = set(id_columns)
    if target_column:
        excluded.add(target_column)
    excluded.update(drop_columns)
    excluded.update(split_columns)
    return excluded


def _select_explicit_features(
    df: pd.DataFrame,
    feature_columns: list[str],
    drop_columns: list[str],
    excluded: set[str],
) -> list[str]:
    _validate_columns_exist(df, feature_columns, "feature_columns not found")
    overlap = sorted(set(feature_columns) & set(drop_columns))
    if overlap:
        raise ValueError(f"features.drop_columns cannot overlap Input/feature_columns: {overlap}")
    protected = sorted(set(feature_columns) & (excluded - set(drop_columns)))
    if protected:
        raise ValueError(f"data.feature_columns cannot include target, ID, or split-control columns: {protected}")
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
        split_columns=_split_control_columns(cfg),
    )
    X = df[features]
    y = _regression_target(df[target_column], target_column)
    return X, y, features


def _regression_target(values: pd.Series, target_column: str) -> pd.Series:
    if (
        pd.api.types.is_datetime64_any_dtype(values.dtype)
        or pd.api.types.is_timedelta64_dtype(values.dtype)
        or pd.api.types.is_complex_dtype(values.dtype)
    ):
        raise ValueError(f"target_column must contain finite real numeric values: {target_column}")
    numeric = pd.to_numeric(values, errors="coerce")
    if pd.api.types.is_complex_dtype(numeric.dtype):
        raise ValueError(f"target_column must contain finite real numeric values: {target_column}")
    missing_count = int(values.isna().sum())
    invalid_count = int((values.notna() & numeric.isna()).sum())
    non_finite_count = int((numeric.notna() & ~np.isfinite(numeric.astype(float))).sum())
    if missing_count or invalid_count or non_finite_count:
        raise ValueError(
            f"target_column must contain finite numeric values: {target_column} "
            f"(missing={missing_count}, non_numeric={invalid_count}, non_finite={non_finite_count})"
        )
    return numeric.astype(float)


def _split_control_columns(cfg: dict[str, Any]) -> list[str]:
    split_cfg = cfg.get("split", {}) or {}
    method = str(split_cfg.get("method") or "random").strip().lower()
    setting = {
        "group": "group_column",
        "time": "time_column",
        "fixed": "valid_filter_column",
    }.get(method)
    if setting is None:
        return []
    column = split_cfg.get(setting)
    return [str(column)] if column is not None and str(column).strip() else []


def _valid_size(cfg: dict[str, Any]) -> float:
    split_cfg = cfg.get("split", {})
    valid_size = float(split_cfg.get("valid_size", 0.2))
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
    valid_size = _valid_size(cfg)
    seed = int(cfg.get("run", {}).get("seed", 42))
    rng = np.random.default_rng(seed)
    indices = np.arange(row_count)
    rng.shuffle(indices)
    valid_count = max(1, round(len(indices) * valid_size))
    valid_idx = indices[:valid_count]
    train_idx = indices[valid_count:]
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
    _validate_columns_exist(df, coordinate_columns, "Coordinate columns not found")
    valid_size = _valid_size(cfg)
    coordinates = df[coordinate_columns].copy()
    coordinates["__split_seed__"] = int(cfg.get("run", {}).get("seed", 42))
    row_hashes = pd.util.hash_pandas_object(coordinates, index=False).to_numpy(dtype=np.uint64)
    coordinate_hashes = np.unique(row_hashes)
    if len(coordinate_hashes) < 2:
        raise ValueError("Coordinate-based random split requires at least two distinct coordinates.")
    valid_count = max(1, round(len(coordinate_hashes) * valid_size))
    valid_count = min(valid_count, len(coordinate_hashes) - 1)
    valid_hashes = set(np.sort(coordinate_hashes)[:valid_count].tolist())
    valid_mask = np.fromiter((value in valid_hashes for value in row_hashes), dtype=bool, count=len(row_hashes))
    indices = np.arange(len(df))
    train_idx = indices[~valid_mask]
    valid_idx = indices[valid_mask]
    _check_non_empty_split(train_idx, valid_idx, method="random")
    return train_idx, valid_idx


def _group_split_indices(df: pd.DataFrame | None, cfg: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    split_cfg = cfg.get("split", {}) or {}
    df, group_column = _require_split_column(df, split_cfg.get("group_column"), setting="split.group_column")
    groups = df[group_column].astype("object").where(df[group_column].notna(), "<MISSING>")
    unique_groups = np.array(sorted(groups.unique(), key=lambda value: str(value)), dtype=object)
    if len(unique_groups) < 2:
        raise ValueError("split.method=group requires at least two distinct groups.")
    valid_size = _valid_size(cfg)
    seed = int(cfg.get("run", {}).get("seed", 42))
    rng = np.random.default_rng(seed)
    shuffled = unique_groups.copy()
    rng.shuffle(shuffled)
    valid_group_count = max(1, round(len(shuffled) * valid_size))
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
    df, time_column = _require_split_column(df, split_cfg.get("time_column"), setting="split.time_column")
    values = pd.to_datetime(df[time_column], errors="coerce")
    invalid_count = int(values.isna().sum())
    if invalid_count:
        raise ValueError(f"split.time_column contains {invalid_count} values that cannot be parsed as datetimes.")
    valid_size = _valid_size(cfg)
    target_valid_rows = max(1, round(len(values) * valid_size))
    counts = values.value_counts(sort=False).sort_index()
    if len(counts) < 2:
        raise ValueError("split.method=time requires at least two distinct timestamps.")
    valid_rows_by_cutoff = counts.iloc[::-1].cumsum().iloc[::-1]
    cutoff = (valid_rows_by_cutoff.iloc[1:] - target_valid_rows).abs().idxmin()
    valid_mask = values.ge(cutoff).to_numpy()
    indices = np.arange(len(df))
    train_idx = indices[~valid_mask]
    valid_idx = indices[valid_mask]
    _check_non_empty_split(train_idx, valid_idx, method="time")
    return train_idx, valid_idx


def _fixed_split_indices(df: pd.DataFrame | None, cfg: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    split_cfg = cfg.get("split", {}) or {}
    df, filter_column = _require_split_column(
        df,
        split_cfg.get("valid_filter_column"),
        setting="split.valid_filter_column",
    )
    filter_value = split_cfg.get("valid_filter_value")
    if filter_value is None or str(filter_value) == "":
        raise ValueError("split.valid_filter_value is required for split.method=fixed.")
    valid_mask = df[filter_column].astype(str).eq(str(filter_value)).to_numpy()
    indices = np.arange(len(df))
    valid_idx = indices[valid_mask]
    train_idx = indices[~valid_mask]
    _check_non_empty_split(train_idx, valid_idx, method="fixed")
    return train_idx, valid_idx


def split_metadata(cfg: dict[str, Any], *, train_rows: int, valid_rows: int) -> dict[str, Any]:
    split_cfg = cfg.get("split", {}) or {}
    method = str(split_cfg.get("method") or "random").strip().lower()
    total_rows = train_rows + valid_rows
    return {
        "method": method,
        "train_rows": int(train_rows),
        "valid_rows": int(valid_rows),
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
    """Small deterministic holdout split without pulling sklearn into the data layer."""
    split_cfg = cfg.get("split", {}) or {}
    method = str(split_cfg.get("method") or "random").strip().lower()
    if method == "random":
        train_idx, valid_idx = _random_split_indices(
            len(X),
            cfg,
            df=df,
            coordinate_columns=coordinate_columns,
        )
    elif method == "group":
        train_idx, valid_idx = _group_split_indices(df, cfg)
    elif method == "time":
        train_idx, valid_idx = _time_split_indices(df, cfg)
    elif method == "fixed":
        train_idx, valid_idx = _fixed_split_indices(df, cfg)
    else:
        raise ValueError("split.method must be one of: random, group, time, fixed.")
    _validate_target_split(target_labels, train_idx, valid_idx)
    return X.iloc[train_idx], X.iloc[valid_idx], y.iloc[train_idx], y.iloc[valid_idx]


def _validate_target_split(targets: pd.Series | None, train_idx, valid_idx) -> None:
    if targets is None:
        return
    target_names = set(targets.astype(str))
    train_targets = set(targets.iloc[train_idx].astype(str))
    valid_targets = set(targets.iloc[valid_idx].astype(str))
    missing_train = sorted(target_names - train_targets)
    missing_valid = sorted(target_names - valid_targets)
    if missing_train or missing_valid:
        raise ValueError(
            "Split must contain training and validation observations for every target "
            f"(missing_train={missing_train}, missing_valid={missing_valid})."
        )
