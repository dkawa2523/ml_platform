from __future__ import annotations

TABLE_REPORTS = {
    "leaderboard",
    "leaderboard_topk",
    "candidate_predictions",
    "validation_predictions",
    "evaluation_predictions",
    "evaluation_summary",
    "best_vs_ensemble_summary",
    "predictions",
    "schema_check_summary",
    "prediction_summary",
    "prediction_preview",
    "source_summary",
    "feature_summary_table",
    "missing_rate_by_column",
    "feature_type_counts",
    "data_quality_summary_table",
    "data_quality_warnings",
    "metrics_table",
    "metrics_by_candidate",
    "ensemble_metrics_table",
}
TABLE_SERIES_ALIASES = {
    "leaderboard": "leaderboard_table",
    "leaderboard_topk": "leaderboard_topk_table",
    "candidate_predictions": "candidate_predictions_table",
    "evaluation_summary": "evaluation_summary_table",
    "best_vs_ensemble_summary": "best_vs_ensemble_summary_table",
    "predictions": "predictions_table",
    "schema_check_summary": "schema_check_summary_table",
    "prediction_summary": "prediction_summary_table",
    "prediction_preview": "prediction_preview_table",
    "source_summary": "source_summary_table",
    "data_quality_summary_table": "data_quality_summary_table",
    "data_quality_warnings": "data_quality_warnings_table",
}
TABLE_REPORT_PREFIXES = (
    "feature_importance",
    "ensemble_members",
    "ensemble_weights",
    "metrics_table",
)
NON_REPORT_TABLES = {
    "ensemble_predictions",
}
NON_REPORT_PLOT_IMAGES = {
    # Generic aliases of best-entry plots; keep the artifacts, but avoid
    # duplicate image panels in ClearML PLOTS.
    "prediction_vs_actual",
    "residual_histogram",
    "residual_vs_predicted",
}


def should_report_table(name: str) -> bool:
    if name in NON_REPORT_TABLES:
        return False
    return (
        name in TABLE_REPORTS
        or name.startswith("ensemble_predictions_")
        or any(name.startswith(prefix) for prefix in TABLE_REPORT_PREFIXES)
    )


def table_series(name: str) -> str:
    return TABLE_SERIES_ALIASES.get(name, name)


def should_report_plot_image(name: str) -> bool:
    return name not in NON_REPORT_PLOT_IMAGES
