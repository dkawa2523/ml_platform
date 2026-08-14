from __future__ import annotations

import json
from typing import Any

import pandas as pd


LEAKAGE_TOKENS = ("target", "label", "answer", "result", "score", "predict", "prediction")
HIGH_MISSING_WARNING_RATE = 0.2


def _existing_columns(columns: list[str] | str | None, df: pd.DataFrame) -> list[str]:
    if columns is None or columns == "":
        return []
    if isinstance(columns, str):
        values = [value.strip() for value in columns.split(",") if value.strip()]
    else:
        values = [str(value) for value in columns]
    return [column for column in values if column in df.columns]


def _json_value(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True)
    return value


def _is_numeric_series(series: pd.Series) -> bool:
    non_missing = series.dropna()
    if non_missing.empty:
        return False
    converted = pd.to_numeric(non_missing, errors="coerce")
    return bool(converted.notna().all())


def _column_missing_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    row_count = len(df)
    rows = []
    for column in df.columns:
        missing_count = int(df[column].isna().sum())
        if missing_count <= 0:
            continue
        rows.append(
            {
                "column": str(column),
                "missing_count": missing_count,
                "missing_rate": float(missing_count / row_count) if row_count else 0.0,
            }
        )
    return sorted(rows, key=lambda row: (-row["missing_rate"], -row["missing_count"], row["column"]))[:10]


def _high_cardinality_rows(df: pd.DataFrame, feature_columns: list[str]) -> list[dict[str, Any]]:
    rows = []
    for column in feature_columns:
        if column not in df.columns:
            continue
        series = df[column]
        if _is_numeric_series(series):
            continue
        rows.append(
            {
                "column": str(column),
                "unique_count": int(series.nunique(dropna=True)),
                "non_missing_count": int(series.notna().sum()),
            }
        )
    return sorted(rows, key=lambda row: (-row["unique_count"], row["column"]))[:10]


def _possible_leakage_columns(feature_columns: list[str]) -> list[str]:
    matches = []
    for column in feature_columns:
        text = column.lower()
        if any(token in text for token in LEAKAGE_TOKENS):
            matches.append(column)
    return matches


def _warning_rows(summary: dict[str, Any], row_count: int) -> list[dict[str, Any]]:
    return [
        *_target_warning_rows(summary),
        *_duplicate_warning_rows(summary),
        *_high_missing_warning_rows(summary),
        *_high_cardinality_warning_rows(summary, row_count),
        *_leakage_warning_rows(summary),
    ]


def _target_warning_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    if not summary["target_missing_count"]:
        return []
    return [
        {
            "warning_type": "target_missing",
            "column": summary["target_column"],
            "value": summary["target_missing_count"],
            "message": "Target column contains missing values.",
        }
    ]


def _duplicate_warning_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    if summary["duplicate_row_count"]:
        rows.append(
            {
                "warning_type": "duplicate_rows",
                "column": "",
                "value": summary["duplicate_row_count"],
                "message": "Dataset contains duplicate rows.",
            }
        )
    if summary["id_duplicate_count"]:
        rows.append(
            {
                "warning_type": "duplicate_ids",
                "column": ",".join(summary["id_columns"]),
                "value": summary["id_duplicate_count"],
                "message": "Configured id columns contain duplicate combinations.",
            }
        )
    return rows


def _high_missing_warning_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "warning_type": "high_missing",
            "column": item["column"],
            "value": item["missing_rate"],
            "message": "Column has a high missing-value rate.",
        }
        for item in summary["high_missing_columns"]
        if float(item["missing_rate"]) >= HIGH_MISSING_WARNING_RATE
    ]


def _high_cardinality_warning_rows(summary: dict[str, Any], row_count: int) -> list[dict[str, Any]]:
    threshold = min(50, max(20, row_count * 0.5))
    return [
        {
            "warning_type": "high_cardinality",
            "column": item["column"],
            "value": item["unique_count"],
            "message": "Categorical feature has high cardinality.",
        }
        for item in summary["high_cardinality_columns"]
        if int(item["unique_count"]) >= threshold
    ]


def _leakage_warning_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "warning_type": "possible_leakage",
            "column": column,
            "value": column,
            "message": "Feature name looks like a target or prediction-derived column.",
        }
        for column in summary["possible_leakage_columns"]
    ]


def build_data_quality_report(
    df: pd.DataFrame,
    *,
    target_column: str | None,
    feature_columns: list[str],
    id_columns: list[str] | str | None = None,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    """Build a lightweight data-quality summary for tabular regression inputs."""
    row_count = int(len(df))
    existing_id_columns = _existing_columns(id_columns, df)
    target = _target_stats(df, target_column, row_count)
    feature_counts = _feature_counts(df, feature_columns)
    summary: dict[str, Any] = {
        "row_count": row_count,
        "column_count": int(len(df.columns)),
        "target_column": target_column,
        **target,
        "duplicate_row_count": int(df.duplicated(keep=False).sum()),
        "id_columns": existing_id_columns,
        "id_duplicate_count": _id_duplicate_count(df, existing_id_columns),
        "feature_count": int(len(feature_columns)),
        **feature_counts,
        "high_missing_columns": _column_missing_rows(df),
        "high_cardinality_columns": _high_cardinality_rows(df, feature_columns),
        "possible_leakage_columns": _possible_leakage_columns(feature_columns),
    }
    return summary, _summary_table(summary), _warnings_table(summary, row_count)


def _target_stats(df: pd.DataFrame, target_column: str | None, row_count: int) -> dict[str, Any]:
    target_exists = bool(target_column and target_column in df.columns)
    target = df[target_column] if target_exists else pd.Series(dtype="object")
    missing_count = int(target.isna().sum()) if target_exists else 0
    return {
        "target_missing_count": missing_count,
        "target_missing_rate": float(missing_count / row_count) if row_count else 0.0,
        "target_is_numeric": _is_numeric_series(target) if target_exists else False,
    }


def _feature_counts(df: pd.DataFrame, feature_columns: list[str]) -> dict[str, int]:
    numeric_features = [column for column in feature_columns if column in df.columns and _is_numeric_series(df[column])]
    categorical_features = [
        column for column in feature_columns if column in df.columns and column not in numeric_features
    ]
    return {
        "numeric_feature_count": int(len(numeric_features)),
        "categorical_feature_count": int(len(categorical_features)),
    }


def _id_duplicate_count(df: pd.DataFrame, existing_id_columns: list[str]) -> int:
    if not existing_id_columns:
        return 0
    return int(df.duplicated(subset=existing_id_columns, keep=False).sum())


def _summary_table(summary: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame([{"metric": key, "value": _json_value(value)} for key, value in summary.items()])


def _warnings_table(summary: dict[str, Any], row_count: int) -> pd.DataFrame:
    return pd.DataFrame(
        _warning_rows(summary, row_count),
        columns=["warning_type", "column", "value", "message"],
    )
