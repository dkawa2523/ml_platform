"""Feature and regression-target selection."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from ml_platform_core.value_coercion import as_str_list

from .splitting import split_control_columns


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
    ids = as_str_list(id_columns) or []
    explicit = as_str_list(feature_columns)
    dropped = as_str_list(drop_columns) or []
    passthrough = as_str_list(passthrough_columns) or []
    split_controls = as_str_list(split_columns) or []

    _validate_columns_exist(df, dropped, "features.drop_columns not found")
    excluded = _excluded_feature_columns(ids, target_column, dropped, split_controls)
    if explicit:
        return _select_explicit_features(df, explicit, dropped, excluded)

    _validate_passthrough_columns(df, passthrough, dropped, excluded)
    return _select_default_features(df, excluded)


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
        split_columns=split_control_columns(cfg),
    )
    return df[features], _regression_target(df[target_column], target_column), features


def _validate_columns_exist(df: pd.DataFrame, columns: list[str], message: str) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"{message}: {missing}")


def _excluded_feature_columns(
    id_columns: list[str],
    target_column: str | None,
    drop_columns: list[str],
    split_columns: list[str],
) -> set[str]:
    excluded = {*id_columns, *drop_columns, *split_columns}
    if target_column:
        excluded.add(target_column)
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
    omitted = sorted(set(passthrough_columns) & excluded)
    if omitted:
        raise ValueError(f"features.passthrough_columns must be selectable feature columns: {omitted}")


def _select_default_features(df: pd.DataFrame, excluded: set[str]) -> list[str]:
    features = [column for column in df.columns if column not in excluded]
    if not features:
        raise ValueError("No feature columns were selected.")
    return features


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
