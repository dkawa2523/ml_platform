from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ml_platform_core.io import dump_joblib, write_json, write_table

from ..data import load_dataset, split_metadata, split_xy, train_valid_split
from ..data_quality import build_data_quality_report
from ..features import build_feature_pipeline, normalize_feature_config
from ..plotting import (
    transformed_columns_from_transformer,
    write_feature_summary_tables,
    write_metrics_bar_plot,
)


def _transformed_columns(transformer: Any) -> list[str]:
    return transformed_columns_from_transformer(transformer)


def _write_feature_visibility_artifacts(
    *,
    df: pd.DataFrame,
    X: pd.DataFrame,
    X_train: pd.DataFrame,
    X_valid: pd.DataFrame,
    target_column: str,
    feature_columns: list[str],
    transformed_columns: list[str],
    transformer: Any,
    feature_config: dict[str, Any],
    stage_dir: Path,
) -> tuple[dict[str, Path], dict[str, Path]]:
    tables = write_feature_summary_tables(
        df=df,
        X=X,
        X_train=X_train,
        X_valid=X_valid,
        target_column=target_column,
        feature_columns=feature_columns,
        transformed_columns=transformed_columns,
        transformer=transformer,
        feature_config=feature_config,
        output_dir=stage_dir,
    )
    missing_rate = pd.read_csv(tables["missing_rate_by_column"])
    missingness_bar_path = write_metrics_bar_plot(
        [(row.column, row.missing_rate) for row in missing_rate.itertuples(index=False)],
        stage_dir / "missing_rate_by_column_bar.png",
        title="Feature missing rate",
        value_label="missing_rate",
    )
    return tables, {"missing_rate_by_column_bar": missingness_bar_path, "feature_missingness_bar": missingness_bar_path}


def _xy_frame(X: pd.DataFrame, y, target_column: str) -> pd.DataFrame:
    frame = X.reset_index(drop=True).copy()
    frame[target_column] = list(pd.Series(y).reset_index(drop=True))
    return frame


def _preprocess_features(cfg: dict[str, Any], pipeline_dir: Path) -> dict[str, Any]:
    stage_dir = pipeline_dir / "preprocess_features"
    stage_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataset(cfg)
    X, y, feature_columns = split_xy(df, cfg)
    X_train, X_valid, y_train, y_valid = train_valid_split(X, y, cfg, df=df)
    split_summary = split_metadata(cfg, train_rows=len(X_train), valid_rows=len(X_valid))

    feature_cfg = cfg.get("features", {})
    feature_config = normalize_feature_config(feature_cfg)
    feature_preset = feature_config["preset"]
    transformer = build_feature_pipeline(feature_preset, X_train, feature_config)
    transformed_columns = _transformed_columns(transformer)
    feature_tables, feature_plots = _write_feature_visibility_artifacts(
        df=df,
        X=X,
        X_train=X_train,
        X_valid=X_valid,
        target_column=cfg.get("data", {}).get("target_column"),
        feature_columns=feature_columns,
        transformed_columns=transformed_columns,
        transformer=transformer,
        feature_config=feature_config,
        stage_dir=stage_dir,
    )
    feature_summary_table_path = feature_tables["feature_summary_table"]
    missing_rate_by_column_path = feature_tables["missing_rate_by_column"]
    feature_type_counts_path = feature_tables["feature_type_counts"]

    train_features_path = write_table(
        pd.DataFrame(transformer.transform(X_train), columns=transformed_columns),
        stage_dir / "train_features.csv",
    )
    valid_features_path = write_table(
        pd.DataFrame(transformer.transform(X_valid), columns=transformed_columns),
        stage_dir / "valid_features.csv",
    )
    target_column = cfg.get("data", {}).get("target_column")
    processed_train_path = write_table(_xy_frame(X_train, y_train, target_column), stage_dir / "processed_train.csv")
    processed_valid_path = write_table(_xy_frame(X_valid, y_valid, target_column), stage_dir / "processed_valid.csv")
    preprocess_bundle_path = dump_joblib(
        {
            "transformer": transformer,
            "feature_columns": feature_columns,
            "target_column": target_column,
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
            "feature_columns": feature_columns,
            "id_columns": cfg.get("data", {}).get("id_columns", []),
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
    feature_summary_path = write_json(
        {
            "stage": "preprocess_features",
            "input_rows": int(len(df)),
            "train_rows": int(len(X_train)),
            "valid_rows": int(len(X_valid)),
            "split": split_summary,
            "target_column": target_column,
            "feature_count": int(len(feature_columns)),
            "numeric_feature_count": int(len(getattr(transformer, "numeric_cols", []))),
            "categorical_feature_count": int(len(getattr(transformer, "categorical_cols", []))),
            "passthrough_feature_count": int(len(getattr(transformer, "passthrough_cols", []))),
            "dropped_feature_count": int(len(feature_config["drop_columns"])),
            "transformed_feature_count": int(len(transformed_columns)),
            "id_columns": cfg.get("data", {}).get("id_columns", []),
            "feature_columns": feature_columns,
            "feature_preset": feature_preset,
            "feature_config": feature_config,
            "drop_columns": feature_config["drop_columns"],
            "passthrough_columns": feature_config["passthrough_columns"],
            "numeric_impute_strategy": feature_config["numeric_impute_strategy"],
            "categorical_impute_strategy": feature_config["categorical_impute_strategy"],
            "categorical_encoder": feature_config["categorical_encoder"],
            "scaling": feature_config["scaling"],
        },
        stage_dir / "feature_summary.json",
    )
    data_quality_summary, data_quality_summary_table, data_quality_warnings = build_data_quality_report(
        df,
        target_column=target_column,
        feature_columns=feature_columns,
        id_columns=cfg.get("data", {}).get("id_columns", []),
    )
    data_quality_summary_path = write_json(
        {"stage": "preprocess_features", "split": split_summary, **data_quality_summary},
        stage_dir / "data_quality_summary.json",
    )
    data_quality_summary_table_path = write_table(
        data_quality_summary_table,
        stage_dir / "data_quality_summary_table.csv",
    )
    data_quality_warnings_path = write_table(
        data_quality_warnings,
        stage_dir / "data_quality_warnings.csv",
    )

    return {
        "stage": "preprocess_features",
        "stage_dir": stage_dir,
        "transformer": transformer,
        "feature_columns": feature_columns,
        "target_column": target_column,
        "feature_preset": feature_preset,
        "feature_config": feature_config,
        "X_train": X_train,
        "X_valid": X_valid,
        "y_train": y_train,
        "y_valid": y_valid,
        "artifacts": {
            "preprocess_bundle": preprocess_bundle_path,
            "feature_spec": feature_spec_path,
            "feature_summary": feature_summary_path,
            "data_quality_summary": data_quality_summary_path,
        },
        "tables": {
            "feature_summary_table": feature_summary_table_path,
            "feature_summary": feature_summary_table_path,
            "missing_rate_by_column": missing_rate_by_column_path,
            "feature_missingness": missing_rate_by_column_path,
            "feature_type_counts": feature_type_counts_path,
            "data_quality_summary_table": data_quality_summary_table_path,
            "data_quality_warnings": data_quality_warnings_path,
            "train_features": train_features_path,
            "valid_features": valid_features_path,
            "processed_train": processed_train_path,
            "processed_valid": processed_valid_path,
        },
        "plots": feature_plots,
    }
