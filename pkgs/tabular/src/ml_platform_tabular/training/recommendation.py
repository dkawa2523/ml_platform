from __future__ import annotations

from typing import Any

from ml_platform_core.artifacts import utc_timestamp

from .artifacts import LEADERBOARD_REPORT_SCHEMA_VERSION, LEADERBOARD_TOP_K, _code_version
from .ranking import _selector_for_item
from .summary import _summary_row, _summary_source_task_id


def _recommendation_payload(
    *,
    best: dict[str, Any],
    best_single: dict[str, Any] | None,
    best_ensemble: dict[str, Any] | None,
    selection_metric: str,
    leaderboard_rows: list[dict[str, Any]],
    task_id: str | None,
) -> dict[str, Any]:
    selector = _selector_for_item(best)
    recommended = _summary_row("recommended", best, selection_metric)
    source_task_id = _summary_source_task_id(task_id)
    return {
        "report_schema_version": LEADERBOARD_REPORT_SCHEMA_VERSION,
        "created_at": utc_timestamp(),
        "code_version": _code_version(),
        "source_task_id": task_id,
        "source_task_hint": "Use this evaluate_models ClearML task id as Input/source_task_id when source_task_id is null.",
        "recommended_ref_kind": "clearml_task_artifact",
        "recommended_infer_key": "Input/source_task_id + Model/model_selector",
        "recommended_infer_value": selector,
        "recommended_assignment": {
            "Input/source_task_id": task_id or "<this evaluate_models task id>",
            "Model/model_selector": selector,
        },
        "recommended_model_selector": "best",
        "recommended_candidate_selector": selector,
        "recommended_inference_settings": {
            "Model/source_type": "task_id",
            "Model/source_task_id": source_task_id,
            "Model/model_selector": "best",
        },
        "recommended": recommended,
        "best_overall": _summary_row("best_overall", best, selection_metric),
        "best_single_model": _summary_row("best_single_model", best_single, selection_metric),
        "best_ensemble": _summary_row("best_ensemble", best_ensemble, selection_metric),
        "top_candidates": leaderboard_rows[:LEADERBOARD_TOP_K],
    }
