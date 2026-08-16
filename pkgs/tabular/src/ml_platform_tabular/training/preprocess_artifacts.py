"""Persist preprocessing-stage artifacts, tables, and plots."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from ml_platform_core.io import dump_joblib, write_json, write_table

from ..data_quality import build_data_quality_report
from ..plotting import write_feature_diagnostics
from .preprocess_data import PreparedPreprocess


def write_preprocess_outputs(
    prepared: PreparedPreprocess,
    stage_dir: Path,
) -> tuple[dict[str, Path], dict[str, Path], dict[str, Path]]:
    result = prepared.result
    feature_tables, plots = write_feature_diagnostics(
        df=prepared.source_frame,
        X=prepared.feature_frame,
        feature_columns=result.feature_columns,
        transformer=result.transformer,
        feature_config=result.feature_config,
        output_dir=stage_dir,
    )
    quality_summary, quality_warnings = _data_quality(prepared)
    processed_tables = _write_processed_tables(prepared, quality_warnings, stage_dir)
    artifacts = {
        "preprocess_bundle": _write_bundle(prepared, stage_dir),
        "feature_spec": _write_feature_spec(prepared, stage_dir),
        "data_quality_summary": _write_data_quality(prepared, quality_summary, stage_dir),
    }
    if prepared.source_manifest is not None:
        artifacts["target_sources"] = write_json(prepared.source_manifest, stage_dir / "target_sources.json")
    return artifacts, {**feature_tables, **processed_tables}, plots


def _data_quality(prepared: PreparedPreprocess) -> tuple[dict[str, Any], pd.DataFrame]:
    result = prepared.result
    return build_data_quality_report(
        prepared.source_frame,
        target_column=result.target_column,
        feature_columns=result.feature_columns,
        numeric_columns=list(getattr(result.transformer, "numeric_cols", [])),
        categorical_columns=list(getattr(result.transformer, "categorical_cols", [])),
        id_columns=result.id_columns,
    )


def _write_processed_tables(
    prepared: PreparedPreprocess,
    quality_warnings: pd.DataFrame,
    stage_dir: Path,
) -> dict[str, Path]:
    result = prepared.result
    return {
        "data_quality_warnings": write_table(quality_warnings, stage_dir / "data_quality_warnings.csv"),
        "processed_train": write_table(
            _xy_frame(result.X_train, result.y_train, result.target_column), stage_dir / "processed_train.csv"
        ),
        "processed_valid": write_table(
            _xy_frame(result.X_valid, result.y_valid, result.target_column), stage_dir / "processed_valid.csv"
        ),
    }


def _write_bundle(prepared: PreparedPreprocess, stage_dir: Path) -> Path:
    result = prepared.result
    return dump_joblib(
        {
            "transformer": result.transformer,
            "feature_columns": result.feature_columns,
            "metadata_columns": [column for column in result.X_train if column not in result.feature_columns],
            "target_column": result.target_column,
            "target_names": result.target_names,
            "coordinate_columns": result.coordinate_columns,
            "id_columns": result.id_columns,
            "feature_preset": result.feature_preset,
            "feature_params": result.feature_config.get("params") or {},
            "feature_config": result.feature_config,
        },
        stage_dir / "preprocess_bundle.joblib",
    )


def _write_feature_spec(prepared: PreparedPreprocess, stage_dir: Path) -> Path:
    result = prepared.result
    config = result.feature_config
    return write_json(
        {
            "stage": "preprocess_features",
            "input_rows": len(prepared.source_frame),
            "train_rows": len(result.X_train),
            "valid_rows": len(result.X_valid),
            "split": prepared.split_summary,
            "target_column": result.target_column,
            "target_names": result.target_names,
            "coordinate_columns": result.coordinate_columns,
            "feature_columns": result.feature_columns,
            "id_columns": result.id_columns,
            "feature_preset": result.feature_preset,
            "feature_config": config,
            "drop_columns": config["drop_columns"],
            "passthrough_columns": config["passthrough_columns"],
            "numeric_columns": getattr(result.transformer, "numeric_cols", []),
            "categorical_columns": getattr(result.transformer, "categorical_cols", []),
            "categorical_encoder": config["categorical_encoder"],
            "numeric_impute_strategy": config["numeric_impute_strategy"],
            "categorical_impute_strategy": config["categorical_impute_strategy"],
            "scaling": config["scaling"],
            "transformed_columns": prepared.transformed_columns,
        },
        stage_dir / "feature_spec.json",
    )


def _write_data_quality(prepared: PreparedPreprocess, quality_summary: dict[str, Any], stage_dir: Path) -> Path:
    result = prepared.result
    return write_json(
        {
            "stage": "preprocess_features",
            "train_rows": len(result.X_train),
            "valid_rows": len(result.X_valid),
            "split": prepared.split_summary,
            "transformed_feature_count": len(prepared.transformed_columns),
            **quality_summary,
        },
        stage_dir / "data_quality_summary.json",
    )


def _xy_frame(X: pd.DataFrame, y: pd.Series, target_column: str) -> pd.DataFrame:
    frame = X.reset_index(drop=True).copy()
    frame[target_column] = list(pd.Series(y).reset_index(drop=True))
    return frame
