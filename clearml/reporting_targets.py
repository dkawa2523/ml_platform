from __future__ import annotations

TABLE_SERIES_ALIASES = {
    "leaderboard": "leaderboard_table",
    "predictions": "predictions_table",
    "prediction_summary": "prediction_summary_table",
    "prediction_preview": "prediction_preview_table",
    "data_quality_warnings": "data_quality_warnings_table",
}
NON_REPORT_TABLES = {
    "ensemble_predictions",
    "processed_train",
    "processed_valid",
}
NON_REPORT_TABLE_PREFIXES = ("validation_predictions_",)


def should_report_table(name: str) -> bool:
    return name not in NON_REPORT_TABLES and not name.startswith(NON_REPORT_TABLE_PREFIXES)


def table_series(name: str) -> str:
    return TABLE_SERIES_ALIASES.get(name, name)
