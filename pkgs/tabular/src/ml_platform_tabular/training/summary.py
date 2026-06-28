from __future__ import annotations

from typing import Any

from ..ensemble import metric_value
from .artifacts import LEADERBOARD_METRICS, LEADERBOARD_TOP_K, LEADERBOARD_REPORT_SCHEMA_VERSION
from .ranking import _selector_for_item


def _summary_row(summary: str, item: dict[str, Any] | None, selection_metric: str) -> dict[str, Any]:
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
        "model_name": item["model_name"],
        "artifact_kind": item["artifact_kind"],
        "ensemble_method": item.get("ensemble_method"),
        "selection_metric": selection_metric,
        "selection_value": metric_value(item["metrics"], selection_metric),
        "rmse": item["metrics"].get("rmse"),
        "mae": item["metrics"].get("mae"),
        "r2": item["metrics"].get("r2"),
        "model_selector": _selector_for_item(item),
        "infer_target": _selector_for_item(item),
    }


def _best_vs_ensemble_rows(
    best_single: dict[str, Any] | None,
    best_ensemble: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    def _optional_metric(item: dict[str, Any] | None, metric_name: str) -> float | None:
        if item is None:
            return None
        value = item.get("metrics", {}).get(metric_name)
        return float(value) if isinstance(value, (int, float)) else None

    rows: list[dict[str, Any]] = []
    for metric_name in LEADERBOARD_METRICS:
        single_value = _optional_metric(best_single, metric_name)
        ensemble_value = _optional_metric(best_ensemble, metric_name)
        delta = None
        improved = None
        if single_value is not None and ensemble_value is not None:
            delta = ensemble_value - single_value
            improved = delta > 0 if metric_name == "r2" else delta < 0
        rows.append(
            {
                "metric": metric_name,
                "best_single_model": best_single.get("model_name") if best_single else None,
                "best_single_value": single_value,
                "best_ensemble_method": best_ensemble.get("ensemble_method") if best_ensemble else None,
                "best_ensemble_value": ensemble_value,
                "ensemble_minus_single": delta,
                "ensemble_improved": improved,
            }
        )
    return rows


def _summary_or_none(summary: str, item: dict[str, Any] | None, selection_metric: str) -> dict[str, Any] | None:
    if item is None:
        return None
    return _summary_row(summary, item, selection_metric)


def _metrics_for_summary(item: dict[str, Any] | None) -> dict[str, Any] | None:
    if item is None:
        return None
    metrics = item.get("metrics", {})
    return {name: metrics.get(name) for name in LEADERBOARD_METRICS}


def _summary_source_task_id(task_id: str | None) -> str:
    return task_id or "<training_or_evaluate_task_id>"


def _selection_metric_improved(best_vs_rows: list[dict[str, Any]], selection_metric: str) -> bool | None:
    for row in best_vs_rows:
        if row.get("metric") == selection_metric:
            return row.get("ensemble_improved")
    return None


def _decision_summary_payload(
    *,
    best: dict[str, Any],
    best_single: dict[str, Any] | None,
    best_ensemble: dict[str, Any] | None,
    selection_metric: str,
    leaderboard_rows: list[dict[str, Any]],
    best_vs_ensemble_rows: list[dict[str, Any]],
    recommendation: dict[str, Any],
    task_id: str | None,
    code_version: str,
) -> dict[str, Any]:
    return {
        "report_schema_version": LEADERBOARD_REPORT_SCHEMA_VERSION,
        "created_at": recommendation["created_at"],
        "code_version": code_version,
        "source_task_id": task_id,
        "best_model_name": best["model_name"],
        "best_artifact_kind": best["artifact_kind"],
        "best_ensemble_method": best.get("ensemble_method"),
        "selection_metric": selection_metric,
        "best_metrics": _metrics_for_summary(best),
        "leaderboard_top5": leaderboard_rows[:LEADERBOARD_TOP_K],
        "best_single_model": _summary_or_none("best_single_model", best_single, selection_metric),
        "best_ensemble": _summary_or_none("best_ensemble", best_ensemble, selection_metric),
        "best_vs_ensemble_summary": best_vs_ensemble_rows,
        "ensemble_improved_over_best_single": _selection_metric_improved(best_vs_ensemble_rows, selection_metric),
        "recommended_model_selector": "best",
        "recommended_candidate_selector": _selector_for_item(best),
        "recommended_inference_settings": {
            "Model/source_type": "task_id",
            "Model/source_task_id": _summary_source_task_id(task_id),
            "Model/model_selector": "best",
        },
        "recommendation": recommendation,
    }


def _decision_summary_markdown(summary: dict[str, Any]) -> str:
    settings = summary.get("recommended_inference_settings") or {}
    top_rows = summary.get("leaderboard_top5") or []
    best_single = summary.get("best_single_model") or {}
    best_ensemble = summary.get("best_ensemble") or {}
    best_metrics = summary.get("best_metrics") or {}
    lines = [
        "# Leaderboard Decision Summary",
        "",
        "## Use These Inference Settings",
        f"- Model/source_type: {settings.get('Model/source_type')}",
        f"- Model/source_task_id: {settings.get('Model/source_task_id')}",
        f"- Model/model_selector: {settings.get('Model/model_selector')}",
        f"- explicit candidate selector: {summary.get('recommended_candidate_selector')}",
        "",
        "## Best Overall",
        f"- best_model_name: {summary.get('best_model_name')}",
        f"- best_artifact_kind: {summary.get('best_artifact_kind')}",
        f"- best_ensemble_method: {summary.get('best_ensemble_method')}",
        f"- selection_metric: {summary.get('selection_metric')}",
        f"- rmse: {best_metrics.get('rmse')}",
        f"- mae: {best_metrics.get('mae')}",
        f"- r2: {best_metrics.get('r2')}",
        "",
        "## Best Single vs Ensemble",
        f"- best_single_model: {best_single.get('model_name')}",
        f"- best_single_selector: {best_single.get('model_selector')}",
        f"- best_ensemble: {best_ensemble.get('model_name')}",
        f"- best_ensemble_selector: {best_ensemble.get('model_selector')}",
        f"- ensemble_improved_over_best_single: {summary.get('ensemble_improved_over_best_single')}",
        "",
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
    return "\n".join(lines) + "\n"
