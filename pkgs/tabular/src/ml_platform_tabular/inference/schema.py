from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from ml_platform_core.io import write_json
from ml_platform_core.value_coercion import as_str_list

from ..data import select_features
from ..target_sources import SOURCE_ROW_COLUMN, TARGET_COLUMN
from .metadata import known_target_column


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


def required_feature_columns(
    cfg: dict[str, Any],
    *,
    estimator: Any,
    model_info: dict[str, Any],
) -> list[str] | None:
    learned = _learned_feature_columns(estimator, model_info)
    explicit = _as_list(cfg.get("data", {}).get("feature_columns"))
    if learned is not None and explicit and explicit != learned:
        raise ValueError(
            f"data.feature_columns must match the trained model schema exactly; expected {learned}, got {explicit}"
        )
    return learned or explicit or None


def _learned_feature_columns(estimator: Any, model_info: dict[str, Any]) -> list[str] | None:
    schemas = [
        _as_list(columns)
        for columns in (model_info.get("feature_columns"), _estimator_feature_columns(estimator))
        if columns
    ]
    if not schemas:
        return None
    learned = schemas[0]
    if any(schema != learned for schema in schemas[1:]):
        raise ValueError(f"Trained model schema artifacts disagree: {schemas}")
    return learned


def _effective_id_columns(cfg: dict[str, Any], model_info: dict[str, Any]) -> list[str]:
    configured = _as_list(cfg.get("data", {}).get("id_columns"))
    if configured:
        return configured
    return _as_list(model_info.get("id_columns"))


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


def _unseen_category_columns(df, preprocess_bundle: dict[str, Any]) -> list[str]:
    category_levels, fill_values = _category_metadata(preprocess_bundle)
    if category_levels is None:
        return []
    return [
        str(column)
        for column, levels in category_levels.items()
        if column in df.columns and _has_unseen_categories(df[column], levels, fill_values.get(column, "__missing__"))
    ]


def _invalid_numeric_columns(df: pd.DataFrame, preprocess_bundle: dict[str, Any]) -> list[str]:
    columns, passthrough_columns = _numeric_columns(preprocess_bundle)
    return [
        column
        for column in columns
        if column in df.columns
        and _has_invalid_numeric_values(df[column], require_complete=column in passthrough_columns)
    ]


def _numeric_columns(preprocess_bundle: dict[str, Any]) -> tuple[list[str], set[str]]:
    transformer = preprocess_bundle.get("transformer")
    numeric = [str(column) for column in (getattr(transformer, "numeric_cols", []) or [])]
    passthrough = {str(column) for column in (getattr(transformer, "passthrough_cols", []) or [])}
    return list(dict.fromkeys([*numeric, *passthrough])), passthrough


def _has_invalid_numeric_values(values: pd.Series, *, require_complete: bool) -> bool:
    numeric = pd.to_numeric(values, errors="coerce")
    conversion_failed = values.notna() & numeric.isna()
    non_finite = numeric.map(lambda value: bool(pd.notna(value)) and not np.isfinite(float(value)))
    return bool(conversion_failed.any() or non_finite.any() or (require_complete and numeric.isna().any()))


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


def schema_check_summary(
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
    invalid_numeric_columns = _invalid_numeric_columns(df, preprocess_bundle)
    return {
        "required_feature_count": len(feature_columns),
        "provided_feature_count": len([column for column in feature_columns if column in df.columns]),
        "missing_features": missing_features,
        "extra_columns": extra_columns,
        "id_columns": existing_id_columns,
        "missing_id_columns": missing_id_columns,
        "row_count": len(df),
        "unknown_or_unseen_category_warning": bool(unseen_columns),
        "unseen_category_columns": unseen_columns,
        "invalid_numeric_features": invalid_numeric_columns,
        "status": _schema_status(
            missing_features,
            extra_columns,
            missing_id_columns,
            unseen_columns,
            invalid_numeric_columns,
        ),
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
    allowed.update({TARGET_COLUMN, SOURCE_ROW_COLUMN})
    if target_column:
        allowed.add(target_column)
    return [column for column in df.columns if column not in allowed]


def _schema_status(
    missing_features: list[str],
    extra_columns: list[str],
    missing_id_columns: list[str],
    unseen_columns: list[str],
    invalid_numeric_columns: list[str],
) -> str:
    if missing_features or invalid_numeric_columns:
        return "error"
    if extra_columns or missing_id_columns or unseen_columns:
        return "warning"
    return "ok"


def check_inference_schema(
    cfg: dict[str, Any],
    df: pd.DataFrame,
    *,
    estimator: Any,
    model_info: dict[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    """Resolve the trained feature contract and validate one inference table."""
    id_columns = _effective_id_columns(cfg, model_info)
    required_features = required_feature_columns(
        cfg,
        estimator=estimator,
        model_info=model_info,
    )
    features = _features_for_inference(
        df,
        cfg,
        required_features=required_features,
        id_columns=id_columns,
    )
    summary = schema_check_summary(
        df,
        feature_columns=features,
        id_columns=id_columns,
        target_column=known_target_column(cfg, model_info),
        preprocess_bundle=_preprocess_bundle(estimator),
    )
    return features, summary


def _preprocess_bundle(estimator: Any) -> dict[str, Any]:
    transformer = getattr(estimator, "transformer", None)
    estimators = getattr(estimator, "estimators", None)
    if transformer is None and estimators:
        transformer = getattr(estimators[0], "transformer", None)
    return {"transformer": transformer} if transformer is not None else {}


def write_schema_check(summary: dict[str, Any], run_dir: Path) -> Path:
    return write_json(summary, run_dir / "schema_check_summary.json")
