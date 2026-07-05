from __future__ import annotations

TABLE_SERIES_ALIASES = {
    "leaderboard": "leaderboard_table",
    "predictions": "predictions_table",
    "schema_check_summary": "schema_check_summary_table",
    "prediction_summary": "prediction_summary_table",
    "prediction_preview": "prediction_preview_table",
    "source_summary": "source_summary_table",
    "data_quality_summary_table": "data_quality_summary_table",
    "data_quality_warnings": "data_quality_warnings_table",
}
NON_REPORT_TABLES = {
    "ensemble_predictions",
    "processed_train",
    "processed_valid",
    "train_features",
    "valid_features",
}
NON_REPORT_TABLE_PREFIXES = ("validation_predictions_",)
NON_REPORT_PLOT_IMAGES = {
    # Generic aliases of best-entry plots; keep the artifacts, but avoid
    # duplicate image panels in ClearML PLOTS.
    "prediction_vs_actual",
    "residual_histogram",
    "residual_vs_predicted",
}


def should_report_table(name: str) -> bool:
    return name not in NON_REPORT_TABLES and not name.startswith(NON_REPORT_TABLE_PREFIXES)


def table_series(name: str) -> str:
    return TABLE_SERIES_ALIASES.get(name, name)


def should_report_plot_image(name: str) -> bool:
    return name not in NON_REPORT_PLOT_IMAGES
