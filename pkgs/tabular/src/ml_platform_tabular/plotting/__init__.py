from __future__ import annotations

from .candidate import (
    topk_candidate_predictions,
    write_candidate_prediction_vs_actual_plot,
    write_candidate_residual_histogram,
    write_candidate_residual_vs_predicted_plot,
    write_metrics_by_candidate_table,
)
from .common import write_histogram_plot, write_metrics_bar_plot
from .feature import (
    feature_role,
    transformed_columns_from_transformer,
    write_feature_importance_plot_if_available,
    write_feature_summary_tables,
)
from .leaderboard import (
    write_leaderboard_metric_panel,
    write_leaderboard_pareto_plot,
    write_leaderboard_table,
)
from .prediction import (
    write_prediction_vs_actual_plot,
    write_regression_plot_artifacts,
    write_residual_histogram,
    write_residual_vs_predicted_plot,
)
from .summary import write_prediction_summary_tables


__all__ = [
    "feature_role",
    "topk_candidate_predictions",
    "transformed_columns_from_transformer",
    "write_candidate_prediction_vs_actual_plot",
    "write_candidate_residual_histogram",
    "write_candidate_residual_vs_predicted_plot",
    "write_feature_importance_plot_if_available",
    "write_feature_summary_tables",
    "write_histogram_plot",
    "write_leaderboard_metric_panel",
    "write_leaderboard_pareto_plot",
    "write_leaderboard_table",
    "write_metrics_bar_plot",
    "write_metrics_by_candidate_table",
    "write_prediction_summary_tables",
    "write_prediction_vs_actual_plot",
    "write_regression_plot_artifacts",
    "write_residual_histogram",
    "write_residual_vs_predicted_plot",
]
