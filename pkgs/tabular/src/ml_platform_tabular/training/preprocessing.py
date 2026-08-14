from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ml_platform_core.io import dump_joblib, write_json, write_table
from ml_platform_core.value_coercion import as_str_list

from ..data import load_training_observations, split_metadata, split_xy, train_valid_split
from ..data_quality import build_data_quality_report
from ..features import FeatureTransformer, build_feature_pipeline, normalize_feature_config
from ..plotting import (
    transformed_columns_from_transformer,
    write_feature_diagnostics,
)
from ..target_sources import SOURCE_ROW_COLUMN, TARGET_COLUMN
from .artifacts import PreprocessResult


def _transformed_columns(transformer: FeatureTransformer) -> list[str]:
    return transformed_columns_from_transformer(transformer)


def _xy_frame(X: pd.DataFrame, y: pd.Series, target_column: str) -> pd.DataFrame:
    frame = X.reset_index(drop=True).copy()
    frame[target_column] = list(pd.Series(y).reset_index(drop=True))
    return frame


def _observation_config(cfg: dict[str, Any], target_column: str) -> dict[str, Any]:
    data_cfg = dict(cfg.get("data", {}) or {})
    id_columns = as_str_list(data_cfg.get("id_columns")) or []
    data_cfg.update(
        {
            "target_column": target_column,
            "id_columns": [*id_columns, TARGET_COLUMN, SOURCE_ROW_COLUMN],
        }
    )
    return {**cfg, "data": data_cfg}


def _target_split_rows(train_targets: pd.Series, valid_targets: pd.Series) -> list[dict[str, Any]]:
    rows = []
    target_names = pd.concat([train_targets, valid_targets]).drop_duplicates()
    for target in target_names:
        rows.append(
            {
                "target": str(target),
                "train_rows": int(train_targets.eq(target).sum()),
                "valid_rows": int(valid_targets.eq(target).sum()),
            }
        )
    return rows


def preprocess_features(cfg: dict[str, Any], pipeline_dir: Path) -> PreprocessResult:
    stage_dir = pipeline_dir / "preprocess_features"
    stage_dir.mkdir(parents=True, exist_ok=True)

    df, target_column, coordinate_columns, source_manifest = load_training_observations(cfg)
    id_columns = as_str_list(cfg.get("data", {}).get("id_columns")) or []
    observation_cfg = _observation_config(cfg, target_column)
    feature_frame, y, feature_columns = split_xy(df, observation_cfg)
    metadata_columns = [column for column in (TARGET_COLUMN, SOURCE_ROW_COLUMN) if column in df.columns]
    X = df[[*feature_columns, *metadata_columns]]
    target_labels = (
        df[TARGET_COLUMN].astype(str) if TARGET_COLUMN in df.columns else pd.Series(target_column, index=df.index)
    )
    X_train, X_valid, y_train, y_valid = train_valid_split(
        X,
        y,
        cfg,
        df=df,
        coordinate_columns=coordinate_columns or None,
        target_labels=target_labels,
    )
    split_summary = split_metadata(cfg, train_rows=len(X_train), valid_rows=len(X_valid))
    split_summary["targets"] = _target_split_rows(
        target_labels.loc[X_train.index],
        target_labels.loc[X_valid.index],
    )
    target_names = target_labels.drop_duplicates().tolist()

    feature_cfg = cfg.get("features", {})
    feature_config = normalize_feature_config(feature_cfg)
    feature_preset = feature_config["preset"]
    transformer = build_feature_pipeline(feature_preset, X_train[feature_columns], feature_config)
    transformed_columns = _transformed_columns(transformer)
    feature_tables, feature_plots = write_feature_diagnostics(
        df=df,
        X=feature_frame,
        feature_columns=feature_columns,
        transformer=transformer,
        feature_config=feature_config,
        output_dir=stage_dir,
    )
    missing_rate_by_column_path = feature_tables["missing_rate_by_column"]

    processed_train_path = write_table(_xy_frame(X_train, y_train, target_column), stage_dir / "processed_train.csv")
    processed_valid_path = write_table(_xy_frame(X_valid, y_valid, target_column), stage_dir / "processed_valid.csv")
    preprocess_bundle_path = dump_joblib(
        {
            "transformer": transformer,
            "feature_columns": feature_columns,
            "target_column": target_column,
            "target_names": target_names,
            "coordinate_columns": coordinate_columns,
            "id_columns": id_columns,
            "feature_preset": feature_preset,
            "feature_params": feature_config.get("params") or {},
            "feature_config": feature_config,
        },
        stage_dir / "preprocess_bundle.joblib",
    )
    feature_spec_path = write_json(
        {
            "stage": "preprocess_features",
            "input_rows": len(df),
            "train_rows": len(X_train),
            "valid_rows": len(X_valid),
            "split": split_summary,
            "target_column": target_column,
            "target_names": target_names,
            "coordinate_columns": coordinate_columns,
            "feature_columns": feature_columns,
            "id_columns": id_columns,
            "feature_preset": feature_preset,
            "feature_config": feature_config,
            "drop_columns": feature_config["drop_columns"],
            "passthrough_columns": feature_config["passthrough_columns"],
            "numeric_columns": getattr(transformer, "numeric_cols", []),
            "categorical_columns": getattr(transformer, "categorical_cols", []),
            "categorical_encoder": feature_config["categorical_encoder"],
            "numeric_impute_strategy": feature_config["numeric_impute_strategy"],
            "categorical_impute_strategy": feature_config["categorical_impute_strategy"],
            "scaling": feature_config["scaling"],
            "transformed_columns": transformed_columns,
        },
        stage_dir / "feature_spec.json",
    )
    data_quality_summary, data_quality_warnings = build_data_quality_report(
        df,
        target_column=target_column,
        feature_columns=feature_columns,
        numeric_columns=list(getattr(transformer, "numeric_cols", [])),
        categorical_columns=list(getattr(transformer, "categorical_cols", [])),
        id_columns=id_columns,
    )
    data_quality_summary_path = write_json(
        {
            "stage": "preprocess_features",
            "train_rows": int(len(X_train)),
            "valid_rows": int(len(X_valid)),
            "split": split_summary,
            "transformed_feature_count": int(len(transformed_columns)),
            **data_quality_summary,
        },
        stage_dir / "data_quality_summary.json",
    )
    data_quality_warnings_path = write_table(
        data_quality_warnings,
        stage_dir / "data_quality_warnings.csv",
    )
    target_sources_path = (
        write_json(source_manifest, stage_dir / "target_sources.json") if source_manifest is not None else None
    )

    return PreprocessResult(
        transformer=transformer,
        feature_columns=feature_columns,
        target_column=target_column,
        target_names=target_names,
        coordinate_columns=coordinate_columns,
        id_columns=id_columns,
        feature_preset=feature_preset,
        feature_config=feature_config,
        X_train=X_train,
        X_valid=X_valid,
        y_train=y_train,
        y_valid=y_valid,
        artifacts={
            "preprocess_bundle": preprocess_bundle_path,
            "feature_spec": feature_spec_path,
            "data_quality_summary": data_quality_summary_path,
            **({"target_sources": target_sources_path} if target_sources_path is not None else {}),
        },
        tables={
            "missing_rate_by_column": missing_rate_by_column_path,
            "data_quality_warnings": data_quality_warnings_path,
            "processed_train": processed_train_path,
            "processed_valid": processed_valid_path,
        },
        plots=feature_plots,
    )
