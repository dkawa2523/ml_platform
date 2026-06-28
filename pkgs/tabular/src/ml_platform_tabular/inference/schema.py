from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ml_platform_core.io import write_json, write_table

from ..data import select_features


def _as_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


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
    transformer = preprocess_bundle.get("transformer")
    category_levels = getattr(transformer, "category_levels", None)
    if not isinstance(category_levels, dict):
        return []
    fill_values = getattr(transformer, "categorical_fill_values", {})
    unseen: list[str] = []
    for column, levels in category_levels.items():
        if column not in df.columns:
            continue
        known = {str(value) for value in levels}
        fill_value = str(fill_values.get(column, "__missing__")) if isinstance(fill_values, dict) else "__missing__"
        values = df[column].fillna(fill_value).astype(str)
        if any(value not in known for value in values.unique().tolist()):
            unseen.append(str(column))
    return unseen


def _schema_check_summary(
    df,
    *,
    feature_columns: list[str],
    id_columns: list[str],
    target_column: str | None,
    preprocess_bundle: dict[str, Any],
) -> dict[str, Any]:
    existing_id_columns = [column for column in id_columns if column in df.columns]
    missing_id_columns = [column for column in id_columns if column not in df.columns]
    missing_features = [column for column in feature_columns if column not in df.columns]
    allowed = set(feature_columns)
    allowed.update(existing_id_columns)
    if target_column:
        allowed.add(target_column)
    extra_columns = [column for column in df.columns if column not in allowed]
    unseen_columns = _unseen_category_columns(df, preprocess_bundle)
    status = "ok"
    if missing_features:
        status = "error"
    elif extra_columns or missing_id_columns or unseen_columns:
        status = "warning"
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
        "status": status,
    }


def _write_schema_check(summary: dict[str, Any], run_dir: Path) -> tuple[Path, Path]:
    summary_json = write_json(summary, run_dir / "schema_check_summary.json")
    summary_csv = write_table(_schema_check_table(summary), run_dir / "schema_check_summary.csv")
    return summary_json, summary_csv
