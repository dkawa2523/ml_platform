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
    rows: list[dict[str, Any]] = []
    if summary["target_missing_count"]:
        rows.append(
            {
                "warning_type": "target_missing",
                "column": summary["target_column"],
                "value": summary["target_missing_count"],
                "message": "Target column contains missing values.",
            }
        )
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
    for item in summary["high_missing_columns"]:
        if float(item["missing_rate"]) >= HIGH_MISSING_WARNING_RATE:
            rows.append(
                {
                    "warning_type": "high_missing",
                    "column": item["column"],
                    "value": item["missing_rate"],
                    "message": "Column has a high missing-value rate.",
                }
            )
    threshold = min(50, max(20, row_count * 0.5))
    for item in summary["high_cardinality_columns"]:
        if int(item["unique_count"]) >= threshold:
            rows.append(
                {
                    "warning_type": "high_cardinality",
                    "column": item["column"],
                    "value": item["unique_count"],
                    "message": "Categorical feature has high cardinality.",
                }
            )
    for column in summary["possible_leakage_columns"]:
        rows.append(
            {
                "warning_type": "possible_leakage",
                "column": column,
                "value": column,
                "message": "Feature name looks like a target or prediction-derived column.",
            }
        )
    return rows


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
    target_exists = bool(target_column and target_column in df.columns)
    target = df[target_column] if target_exists else pd.Series(dtype="object")
    target_missing_count = int(target.isna().sum()) if target_exists else 0
    target_missing_rate = float(target_missing_count / row_count) if row_count else 0.0
    numeric_features = [column for column in feature_columns if column in df.columns and _is_numeric_series(df[column])]
    categorical_features = [column for column in feature_columns if column in df.columns and column not in numeric_features]
    if existing_id_columns:
        id_duplicate_count = int(df.duplicated(subset=existing_id_columns, keep=False).sum())
    else:
        id_duplicate_count = 0
    summary: dict[str, Any] = {
        "row_count": row_count,
        "column_count": int(len(df.columns)),
        "target_column": target_column,
        "target_missing_count": target_missing_count,
        "target_missing_rate": target_missing_rate,
        "target_is_numeric": _is_numeric_series(target) if target_exists else False,
        "duplicate_row_count": int(df.duplicated(keep=False).sum()),
        "id_columns": existing_id_columns,
        "id_duplicate_count": id_duplicate_count,
        "feature_count": int(len(feature_columns)),
        "numeric_feature_count": int(len(numeric_features)),
        "categorical_feature_count": int(len(categorical_features)),
        "high_missing_columns": _column_missing_rows(df),
        "high_cardinality_columns": _high_cardinality_rows(df, feature_columns),
        "possible_leakage_columns": _possible_leakage_columns(feature_columns),
    }
    summary_table = pd.DataFrame(
        [{"metric": key, "value": _json_value(value)} for key, value in summary.items()]
    )
    warnings = pd.DataFrame(
        _warning_rows(summary, row_count),
        columns=["warning_type", "column", "value", "message"],
    )
    return summary, summary_table, warnings
