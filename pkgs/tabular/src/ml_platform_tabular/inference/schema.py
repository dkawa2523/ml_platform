from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ml_platform_core.io import write_json, write_table
from ml_platform_core.value_coercion import as_str_list

from ..data import select_features


def _as_list(value: Any) -> list[str]:
    return as_str_list(value) or []


def _estimator_feature_columns(estimator: Any) -> list[str] | None:
    columns = getattr(estimator, "feature_columns", None)
    if isinstance(columns, list):
        return [str(col) for col in columns]
    estimators = getattr(estimator, "estimators", None)
    if estimators:
        columns = getattr(estimators[0], "feature_columns", None)
        if isinstance(columns, list):
            return [str(col) for col in columns]
    return None


def _required_feature_columns(
    cfg: dict[str, Any],
    *,
    estimator: Any,
    model_info: dict[str, Any],
    feature_spec: dict[str, Any],
    preprocess_bundle: dict[str, Any],
) -> list[str] | None:
    data_cfg = cfg.get("data", {})
    explicit = data_cfg.get("feature_columns")
    if explicit:
        return _as_list(explicit)

    for feature_columns in (
        feature_spec.get("feature_columns"),
        model_info.get("feature_columns"),
        _estimator_feature_columns(estimator),
        preprocess_bundle.get("feature_columns"),
    ):
        if feature_columns:
            return _as_list(feature_columns)
    return None


def _effective_id_columns(cfg: dict[str, Any], feature_spec: dict[str, Any]) -> list[str]:
    configured = _as_list(cfg.get("data", {}).get("id_columns"))
    if configured:
        return configured
    return _as_list(feature_spec.get("id_columns"))


def _features_for_inference(
    df,
    cfg: dict[str, Any],
    *,
    required_features: list[str] | None,
    id_columns: list[str],
) -> list[str]:
    data_cfg = cfg.get("data", {})
    if required_features is not None:
        return list(required_features)

    return select_features(
        df,
        target_column=data_cfg.get("target_column"),
        feature_columns=None,
        id_columns=id_columns,
    )


def _json_value(value: Any) -> str:
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True, default=str)
    if value is None:
        return ""
    return str(value)


def _schema_check_table(summary: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame([{"metric": key, "value": _json_value(value)} for key, value in summary.items()])


def _unseen_category_columns(df, preprocess_bundle: dict[str, Any]) -> list[str]:
    category_levels, fill_values = _category_metadata(preprocess_bundle)
    if category_levels is None:
        return []
    return [
        str(column)
        for column, levels in category_levels.items()
        if column in df.columns and _has_unseen_categories(df[column], levels, fill_values.get(column, "__missing__"))
    ]


def _category_metadata(preprocess_bundle: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    transformer = preprocess_bundle.get("transformer")
    category_levels = getattr(transformer, "category_levels", None)
    if not isinstance(category_levels, dict):
        return None, {}
    fill_values = getattr(transformer, "categorical_fill_values", {})
    return category_levels, fill_values if isinstance(fill_values, dict) else {}


def _has_unseen_categories(values: pd.Series, levels: Any, fill_value: Any) -> bool:
    known = {str(value) for value in levels}
    filled = values.fillna(str(fill_value)).astype(str)
    return any(value not in known for value in filled.unique().tolist())


def _schema_check_summary(
    df,
    *,
    feature_columns: list[str],
    id_columns: list[str],
    target_column: str | None,
    preprocess_bundle: dict[str, Any],
) -> dict[str, Any]:
    existing_id_columns, missing_id_columns = _id_column_status(df, id_columns)
    missing_features = _missing_columns(df, feature_columns)
    extra_columns = _extra_columns(df, feature_columns, existing_id_columns, target_column)
    unseen_columns = _unseen_category_columns(df, preprocess_bundle)
    return {
        "required_feature_count": len(feature_columns),
        "provided_feature_count": len([column for column in feature_columns if column in df.columns]),
        "missing_features": missing_features,
        "extra_columns": extra_columns,
        "id_columns": existing_id_columns,
        "missing_id_columns": missing_id_columns,
        "row_count": int(len(df)),
        "unknown_or_unseen_category_warning": bool(unseen_columns),
        "unseen_category_columns": unseen_columns,
        "status": _schema_status(missing_features, extra_columns, missing_id_columns, unseen_columns),
    }


def _id_column_status(df: pd.DataFrame, id_columns: list[str]) -> tuple[list[str], list[str]]:
    existing = [column for column in id_columns if column in df.columns]
    missing = [column for column in id_columns if column not in df.columns]
    return existing, missing


def _missing_columns(df: pd.DataFrame, columns: list[str]) -> list[str]:
    return [column for column in columns if column not in df.columns]


def _extra_columns(
    df: pd.DataFrame,
    feature_columns: list[str],
    existing_id_columns: list[str],
    target_column: str | None,
) -> list[str]:
    allowed = set(feature_columns)
    allowed.update(existing_id_columns)
    if target_column:
        allowed.add(target_column)
    return [column for column in df.columns if column not in allowed]


def _schema_status(
    missing_features: list[str],
    extra_columns: list[str],
    missing_id_columns: list[str],
    unseen_columns: list[str],
) -> str:
    if missing_features:
        return "error"
    if extra_columns or missing_id_columns or unseen_columns:
        return "warning"
    return "ok"


def _write_schema_check(summary: dict[str, Any], run_dir: Path) -> tuple[Path, Path]:
    summary_json = write_json(summary, run_dir / "schema_check_summary.json")
    summary_csv = write_table(_schema_check_table(summary), run_dir / "schema_check_summary.csv")
    return summary_json, summary_csv
