from __future__ import annotations

from typing import Any

import pandas as pd


HIGH_MISSING_WARNING_RATE = 0.2


def _existing_columns(columns: list[str] | str | None, df: pd.DataFrame) -> list[str]:
    if columns is None or columns == "":
        return []
    if isinstance(columns, str):
        values = [value.strip() for value in columns.split(",") if value.strip()]
    else:
        values = [str(value) for value in columns]
    return [column for column in values if column in df.columns]


def _column_missing_rows(df: pd.DataFrame, feature_columns: list[str]) -> list[dict[str, Any]]:
    row_count = len(df)
    rows = []
    for column in feature_columns:
        if column not in df.columns:
            continue
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


def _high_cardinality_rows(df: pd.DataFrame, categorical_columns: list[str]) -> list[dict[str, Any]]:
    rows = []
    for column in categorical_columns:
        if column not in df.columns:
            continue
        series = df[column]
        rows.append(
            {
                "column": str(column),
                "unique_count": int(series.nunique(dropna=True)),
                "non_missing_count": int(series.notna().sum()),
            }
        )
    return sorted(rows, key=lambda row: (-row["unique_count"], row["column"]))[:10]


def _warning_rows(summary: dict[str, Any], row_count: int) -> list[dict[str, Any]]:
    return [
        *_duplicate_warning_rows(summary),
        *_high_missing_warning_rows(summary),
        *_high_cardinality_warning_rows(summary, row_count),
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


def build_data_quality_report(
    df: pd.DataFrame,
    *,
    target_column: str | None,
    feature_columns: list[str],
    numeric_columns: list[str],
    categorical_columns: list[str],
    id_columns: list[str] | str | None = None,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Build a lightweight data-quality summary for tabular regression inputs."""
    row_count = int(len(df))
    existing_id_columns = _existing_columns(id_columns, df)
    summary: dict[str, Any] = {
        "row_count": row_count,
        "column_count": int(len(df.columns)),
        "target_column": target_column,
        "duplicate_row_count": int(df.duplicated(keep=False).sum()),
        "id_columns": existing_id_columns,
        "id_duplicate_count": _id_duplicate_count(df, existing_id_columns),
        "feature_count": int(len(feature_columns)),
        "numeric_feature_count": int(len(numeric_columns)),
        "categorical_feature_count": int(len(categorical_columns)),
        "high_missing_columns": _column_missing_rows(df, feature_columns),
        "high_cardinality_columns": _high_cardinality_rows(df, categorical_columns),
    }
    return summary, _warnings_table(summary, row_count)


def _id_duplicate_count(df: pd.DataFrame, existing_id_columns: list[str]) -> int:
    if not existing_id_columns:
        return 0
    return int(df.duplicated(subset=existing_id_columns, keep=False).sum())


def _warnings_table(summary: dict[str, Any], row_count: int) -> pd.DataFrame:
    return pd.DataFrame(
        _warning_rows(summary, row_count),
        columns=["warning_type", "column", "value", "message"],
    )
