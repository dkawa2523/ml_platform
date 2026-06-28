"""Compatibility facade for tabular training pipeline entrypoints."""

from __future__ import annotations

from .training import EvaluationResult, evaluate_model_candidates, run_pipeline
from .training.artifacts import (
    LEADERBOARD_METRICS,
    LEADERBOARD_REPORT_SCHEMA_VERSION,
    LEADERBOARD_TOP_K,
    SELECTION_METRICS,
    _code_version,
    _metric_name,
    _metric_names,
    _metrics_by_model_payload,
    _model_ref_payload,
    _path_map,
    _runtime_task_id,
    _safe_name,
)
from .training.candidate_training import _train_model, _train_model_candidates
from .training.ensemble import _build_ensemble
from .training.evaluation import (
    _evaluate_models,
    _prediction_table_path,
    _write_candidate_predictions,
    _write_evaluation_predictions,
)
from .training.orchestrator import _run_training_pipeline
from .training.preprocessing import (
    _preprocess_features,
    _transformed_columns,
    _write_feature_visibility_artifacts,
    _xy_frame,
)
from .training.ranking import (
    _leaderboard_rows,
    _ranked_results,
    _selection_sort_value,
    _selector_for_item,
)
from .training.recommendation import _recommendation_payload
from .training.summary import (
    _best_vs_ensemble_rows,
    _decision_summary_markdown,
    _decision_summary_payload,
    _metrics_for_summary,
    _selection_metric_improved,
    _summary_or_none,
    _summary_row,
    _summary_source_task_id,
)

__all__ = [
    "EvaluationResult",
    "LEADERBOARD_METRICS",
    "LEADERBOARD_REPORT_SCHEMA_VERSION",
    "LEADERBOARD_TOP_K",
    "SELECTION_METRICS",
    "evaluate_model_candidates",
    "run_pipeline",
    "_best_vs_ensemble_rows",
    "_build_ensemble",
    "_code_version",
    "_decision_summary_markdown",
    "_decision_summary_payload",
    "_evaluate_models",
    "_leaderboard_rows",
    "_metric_name",
    "_metric_names",
    "_metrics_by_model_payload",
    "_metrics_for_summary",
    "_model_ref_payload",
    "_path_map",
    "_prediction_table_path",
    "_preprocess_features",
    "_ranked_results",
    "_recommendation_payload",
    "_run_training_pipeline",
    "_runtime_task_id",
    "_safe_name",
    "_selection_metric_improved",
    "_selection_sort_value",
    "_selector_for_item",
    "_summary_or_none",
    "_summary_row",
    "_summary_source_task_id",
    "_train_model",
    "_train_model_candidates",
    "_transformed_columns",
    "_write_candidate_predictions",
    "_write_evaluation_predictions",
    "_write_feature_visibility_artifacts",
    "_xy_frame",
]
