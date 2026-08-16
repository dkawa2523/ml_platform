"""Load, split, and transform preprocessing-stage data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
from ml_platform_core.value_coercion import as_str_list

from ..data import load_training_observations, split_control_columns, split_metadata, split_xy, train_valid_split
from ..features import build_feature_pipeline, normalize_feature_config
from ..plotting import transformed_columns_from_transformer
from ..target_sources import SOURCE_ROW_COLUMN, TARGET_COLUMN
from .artifacts import PreprocessResult


@dataclass(frozen=True)
class PreparedPreprocess:
    result: PreprocessResult
    source_frame: pd.DataFrame
    feature_frame: pd.DataFrame
    split_summary: dict[str, Any]
    source_manifest: dict[str, Any] | None
    transformed_columns: list[str]


def prepare_preprocess(cfg: dict[str, Any]) -> PreparedPreprocess:
    source_frame, target_column, coordinates, source_manifest = load_training_observations(cfg)
    ids = as_str_list(cfg.get("data", {}).get("id_columns")) or []
    feature_frame, target, feature_columns = split_xy(source_frame, _observation_config(cfg, target_column))
    model_frame = _model_frame(source_frame, feature_columns, cfg)
    labels = _target_labels(source_frame, target_column)
    X_train, X_valid, y_train, y_valid = train_valid_split(
        model_frame,
        target,
        cfg,
        df=source_frame,
        coordinate_columns=coordinates or None,
        target_labels=labels,
    )

    split_summary = split_metadata(cfg, train_rows=len(X_train), valid_rows=len(X_valid))
    split_summary["targets"] = _target_split_rows(labels.loc[X_train.index], labels.loc[X_valid.index])
    feature_config = normalize_feature_config(cfg.get("features", {}))
    feature_preset = feature_config["preset"]
    transformer = build_feature_pipeline(feature_preset, X_train[feature_columns], feature_config)
    result = PreprocessResult(
        transformer=transformer,
        feature_columns=feature_columns,
        target_column=target_column,
        target_names=labels.drop_duplicates().tolist(),
        coordinate_columns=coordinates,
        id_columns=ids,
        feature_preset=feature_preset,
        feature_config=feature_config,
        X_train=X_train,
        X_valid=X_valid,
        y_train=y_train,
        y_valid=y_valid,
        artifacts={},
        tables={},
    )
    return PreparedPreprocess(
        result=result,
        source_frame=source_frame,
        feature_frame=feature_frame,
        split_summary=split_summary,
        source_manifest=source_manifest,
        transformed_columns=transformed_columns_from_transformer(transformer),
    )


def _observation_config(cfg: dict[str, Any], target_column: str) -> dict[str, Any]:
    data_cfg = dict(cfg.get("data", {}) or {})
    ids = as_str_list(data_cfg.get("id_columns")) or []
    data_cfg.update({"target_column": target_column, "id_columns": [*ids, TARGET_COLUMN, SOURCE_ROW_COLUMN]})
    return {**cfg, "data": data_cfg}


def _model_frame(source: pd.DataFrame, feature_columns: list[str], cfg: dict[str, Any]) -> pd.DataFrame:
    metadata = [
        column
        for column in (*split_control_columns(cfg), TARGET_COLUMN, SOURCE_ROW_COLUMN)
        if column in source.columns and column not in feature_columns
    ]
    return source[[*feature_columns, *dict.fromkeys(metadata)]]


def _target_labels(source: pd.DataFrame, target_column: str) -> pd.Series:
    if TARGET_COLUMN in source.columns:
        return source[TARGET_COLUMN].astype(str)
    return pd.Series(target_column, index=source.index)


def _target_split_rows(train_targets: pd.Series, valid_targets: pd.Series) -> list[dict[str, Any]]:
    return [
        {
            "target": str(target),
            "train_rows": int(train_targets.eq(target).sum()),
            "valid_rows": int(valid_targets.eq(target).sum()),
        }
        for target in pd.concat([train_targets, valid_targets]).drop_duplicates()
    ]
