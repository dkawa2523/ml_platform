from __future__ import annotations

from typing import Any

from ..ensemble import metric_value
from .artifacts import (
    CandidateResult,
    LEADERBOARD_METRICS,
    LEADERBOARD_REPORT_SCHEMA_VERSION,
    LEADERBOARD_TOP_K,
    candidate_selector,
)


def _summary_row(summary: str, item: CandidateResult | None, selection_metric: str) -> dict[str, Any]:
    if item is None:
        return {
            "summary": summary,
            "model_name": None,
            "artifact_kind": None,
            "ensemble_method": None,
            "selection_metric": selection_metric,
            "selection_value": None,
            "rmse": None,
            "mae": None,
            "r2": None,
            "model_selector": None,
            "infer_target": None,
        }
    return {
        "summary": summary,
        "model_name": item.model_name,
        "artifact_kind": item.artifact_kind,
        "ensemble_method": item.ensemble_method,
        "selection_metric": selection_metric,
        "selection_value": metric_value(item.metrics, selection_metric),
        "rmse": item.metrics.get("rmse"),
        "mae": item.metrics.get("mae"),
        "r2": item.metrics.get("r2"),
        "model_selector": candidate_selector(item),
        "infer_target": candidate_selector(item),
    }


def _best_vs_ensemble_rows(
    best_single: CandidateResult | None,
    best_ensemble: CandidateResult | None,
) -> list[dict[str, Any]]:
    return [_best_vs_ensemble_row(metric_name, best_single, best_ensemble) for metric_name in LEADERBOARD_METRICS]


def _optional_metric(item: CandidateResult | None, metric_name: str) -> float | None:
    if item is None:
        return None
    value = item.metrics.get(metric_name)
    return float(value) if isinstance(value, (int, float)) else None


def _metric_delta(
    metric_name: str, single_value: float | None, ensemble_value: float | None
) -> tuple[float | None, bool | None]:
    if single_value is None or ensemble_value is None:
        return None, None
    delta = ensemble_value - single_value
    return delta, delta > 0 if metric_name == "r2" else delta < 0


def _best_vs_ensemble_row(
    metric_name: str,
    best_single: CandidateResult | None,
    best_ensemble: CandidateResult | None,
) -> dict[str, Any]:
    single_value = _optional_metric(best_single, metric_name)
    ensemble_value = _optional_metric(best_ensemble, metric_name)
    delta, improved = _metric_delta(metric_name, single_value, ensemble_value)
    return {
        "metric": metric_name,
        "best_single_model": best_single.model_name if best_single else None,
        "best_single_value": single_value,
        "best_ensemble_method": best_ensemble.ensemble_method if best_ensemble else None,
        "best_ensemble_value": ensemble_value,
        "ensemble_minus_single": delta,
        "ensemble_improved": improved,
    }


def _summary_or_none(summary: str, item: CandidateResult | None, selection_metric: str) -> dict[str, Any] | None:
    if item is None:
        return None
    return _summary_row(summary, item, selection_metric)


def _metrics_for_summary(item: CandidateResult | None) -> dict[str, Any] | None:
    if item is None:
        return None
    return {name: item.metrics.get(name) for name in LEADERBOARD_METRICS}


def _summary_source_task_id(task_id: str | None) -> str:
    return task_id or "<training_or_evaluate_task_id>"


def _selection_metric_improved(best_vs_rows: list[dict[str, Any]], selection_metric: str) -> bool | None:
    for row in best_vs_rows:
        if row.get("metric") == selection_metric:
            return row.get("ensemble_improved")
    return None


def _decision_summary_payload(
    *,
    best: CandidateResult,
    best_single: CandidateResult | None,
    best_ensemble: CandidateResult | None,
    selection_metric: str,
    leaderboard_rows: list[dict[str, Any]],
    best_vs_ensemble_rows: list[dict[str, Any]],
    created_at: str,
    task_id: str | None,
    code_version: str,
) -> dict[str, Any]:
    return {
        "report_schema_version": LEADERBOARD_REPORT_SCHEMA_VERSION,
        "created_at": created_at,
        "code_version": code_version,
        "source_task_id": task_id,
        "best_model_name": best.model_name,
        "best_artifact_kind": best.artifact_kind,
        "best_ensemble_method": best.ensemble_method,
        "selection_metric": selection_metric,
        "best_metrics": _metrics_for_summary(best),
        "leaderboard_top5": leaderboard_rows[:LEADERBOARD_TOP_K],
        "best_single_model": _summary_or_none("best_single_model", best_single, selection_metric),
        "best_ensemble": _summary_or_none("best_ensemble", best_ensemble, selection_metric),
        "best_vs_ensemble_summary": best_vs_ensemble_rows,
        "ensemble_improved_over_best_single": _selection_metric_improved(best_vs_ensemble_rows, selection_metric),
        "recommended_model_selector": "best",
        "recommended_candidate_selector": candidate_selector(best),
        "recommended_inference_settings": {
            "Model/source_type": "task_id",
            "Model/source_task_id": _summary_source_task_id(task_id),
            "Model/model_selector": "best",
        },
    }


def _decision_summary_markdown(summary: dict[str, Any]) -> str:
    return "\n".join(_decision_summary_lines(summary)) + "\n"


def _decision_summary_lines(summary: dict[str, Any]) -> list[str]:
    lines = ["# Leaderboard Decision Summary", ""]
    lines.extend(_inference_settings_lines(_summary_mapping(summary, "recommended_inference_settings"), summary))
    lines.extend(_best_overall_lines(summary, _summary_mapping(summary, "best_metrics")))
    lines.extend(
        _best_comparison_lines(
            summary,
            _summary_mapping(summary, "best_single_model"),
            _summary_mapping(summary, "best_ensemble"),
        )
    )
    lines.extend(_leaderboard_table_lines(_summary_list(summary, "leaderboard_top5")))
    return lines


def _summary_mapping(summary: dict[str, Any], key: str) -> dict[str, Any]:
    value = summary.get(key)
    return value if isinstance(value, dict) else {}


def _summary_list(summary: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = summary.get(key)
    return value if isinstance(value, list) else []


def _inference_settings_lines(settings: dict[str, Any], summary: dict[str, Any]) -> list[str]:
    return [
        "## Use These Inference Settings",
        f"- Model/source_type: {settings.get('Model/source_type')}",
        f"- Model/source_task_id: {settings.get('Model/source_task_id')}",
        f"- Model/model_selector: {settings.get('Model/model_selector')}",
        f"- explicit candidate selector: {summary.get('recommended_candidate_selector')}",
        "",
    ]


def _best_overall_lines(summary: dict[str, Any], best_metrics: dict[str, Any]) -> list[str]:
    return [
        "## Best Overall",
        f"- best_model_name: {summary.get('best_model_name')}",
        f"- best_artifact_kind: {summary.get('best_artifact_kind')}",
        f"- best_ensemble_method: {summary.get('best_ensemble_method')}",
        f"- selection_metric: {summary.get('selection_metric')}",
        f"- rmse: {best_metrics.get('rmse')}",
        f"- mae: {best_metrics.get('mae')}",
        f"- r2: {best_metrics.get('r2')}",
        "",
    ]


def _best_comparison_lines(
    summary: dict[str, Any],
    best_single: dict[str, Any],
    best_ensemble: dict[str, Any],
) -> list[str]:
    return [
        "## Best Single vs Ensemble",
        f"- best_single_model: {best_single.get('model_name')}",
        f"- best_single_selector: {best_single.get('model_selector')}",
        f"- best_ensemble: {best_ensemble.get('model_name')}",
        f"- best_ensemble_selector: {best_ensemble.get('model_selector')}",
        f"- ensemble_improved_over_best_single: {summary.get('ensemble_improved_over_best_single')}",
        "",
    ]


def _leaderboard_table_lines(top_rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## Top 5 Leaderboard",
        "| rank | model_name | artifact_kind | ensemble_method | rmse | mae | r2 | model_selector |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in top_rows:
        lines.append(
            "| {rank} | {model_name} | {artifact_kind} | {ensemble_method} | {rmse} | {mae} | {r2} | {infer_target} |".format(
                rank=row.get("rank"),
                model_name=row.get("model_name"),
                artifact_kind=row.get("artifact_kind"),
                ensemble_method=row.get("ensemble_method") or "",
                rmse=row.get("rmse"),
                mae=row.get("mae"),
                r2=row.get("r2"),
                infer_target=row.get("infer_target"),
            )
        )
    return lines
