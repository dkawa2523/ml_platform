from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from ..plotting import (
    write_leaderboard_metric_panel,
    write_leaderboard_pareto_plot,
    write_leaderboard_table,
    write_metrics_bar_plot,
    write_metrics_by_candidate_table,
)
from .artifacts import CandidateResult, LEADERBOARD_METRICS, LEADERBOARD_TOP_K, candidate_selector


@dataclass(frozen=True)
class LeaderboardArtifacts:
    tables: dict[str, Path]
    plots: dict[str, Path]


def build_leaderboard_rows(results: list[CandidateResult], selection_metric: str) -> list[dict[str, Any]]:
    rows = []
    for rank, item in enumerate(results, start=1):
        row = {
            "rank": rank,
            "model_name": item.model_name,
            "artifact_kind": item.artifact_kind,
            "ensemble_method": item.ensemble_method,
            "stage": item.stage,
            "selection_metric": selection_metric,
            "ref_kind": "task_artifact",
            "infer_selector": "Model/model_selector",
            "infer_target": candidate_selector(item),
            "model_params": json.dumps(item.model_params, sort_keys=True, default=str),
            "artifact_name": item.artifact_name,
            "artifact_path": str(item.artifacts["model"]),
        }
        for name in LEADERBOARD_METRICS:
            row[name] = item.metrics.get(name)
        rows.append(row)
    return rows


def _metric_bar_items(
    metrics_by_candidate: dict[str, dict[str, Any]], selection_metric: str
) -> list[tuple[str, float]]:
    items = []
    for candidate_name, payload in metrics_by_candidate.items():
        metrics = payload.get("metrics", {})
        if isinstance(metrics, dict) and isinstance(metrics.get(selection_metric), (int, float)):
            items.append((candidate_name, float(metrics[selection_metric])))
    return items


def write_leaderboard_artifacts(
    *,
    leaderboard_rows: list[dict[str, Any]],
    metrics_by_candidate: dict[str, dict[str, Any]],
    selection_metric: str,
    stage_dir: Path,
) -> LeaderboardArtifacts:
    leaderboard_path = write_leaderboard_table(leaderboard_rows, stage_dir / "leaderboard.csv")
    leaderboard_topk_path = write_leaderboard_table(
        leaderboard_rows[:LEADERBOARD_TOP_K],
        stage_dir / "leaderboard_topk.csv",
    )
    metrics_by_candidate_table_path = write_metrics_by_candidate_table(
        metrics_by_candidate,
        stage_dir / "metrics_by_candidate.csv",
    )
    metrics_by_candidate_bar_path = write_metrics_bar_plot(
        _metric_bar_items(metrics_by_candidate, selection_metric),
        stage_dir / "metrics_by_candidate_bar.png",
        title=f"Metrics by candidate ({selection_metric})",
        value_label=selection_metric,
        sort="value_desc" if selection_metric == "r2" else "value_asc",
    )
    leaderboard_topk_score_bar_path = write_metrics_bar_plot(
        [(row["model_name"], row.get(selection_metric)) for row in leaderboard_rows],
        stage_dir / "leaderboard_topk_score_bar.png",
        title=f"Leaderboard top-{LEADERBOARD_TOP_K} ({selection_metric})",
        value_label=selection_metric,
        top_n=LEADERBOARD_TOP_K,
        sort="input",
    )
    leaderboard_metric_panel_path = write_leaderboard_metric_panel(
        leaderboard_rows,
        stage_dir / "leaderboard_metric_panel.png",
        top_k=LEADERBOARD_TOP_K,
    )
    leaderboard_pareto_path = write_leaderboard_pareto_plot(
        leaderboard_rows,
        stage_dir / "leaderboard_pareto_rmse_r2.png",
        top_k=max(LEADERBOARD_TOP_K, 10),
    )
    return LeaderboardArtifacts(
        tables={
            "leaderboard": leaderboard_path,
            "leaderboard_topk": leaderboard_topk_path,
            "metrics_by_candidate": metrics_by_candidate_table_path,
        },
        plots={
            "metrics_by_candidate_bar": metrics_by_candidate_bar_path,
            "leaderboard_topk_score_bar": leaderboard_topk_score_bar_path,
            "leaderboard_metric_panel": leaderboard_metric_panel_path,
            "leaderboard_pareto_rmse_r2": leaderboard_pareto_path,
        },
    )
