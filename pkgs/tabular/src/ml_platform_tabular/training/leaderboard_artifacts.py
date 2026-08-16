from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..plotting import (
    write_leaderboard_metric_panel,
    write_leaderboard_table,
)
from .artifacts import LEADERBOARD_METRICS, LEADERBOARD_TOP_K, CandidateResult, candidate_selector


@dataclass(frozen=True)
class LeaderboardArtifacts:
    tables: dict[str, Path]
    plots: dict[str, Path]


def build_leaderboard_rows(results: list[CandidateResult], selection_metric: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rank, item in enumerate(results, start=1):
        row: dict[str, Any] = {
            "rank": rank,
            "model_name": item.model_name,
            "artifact_kind": item.artifact_kind,
            "ensemble_method": item.ensemble_method,
            "stage": item.stage,
            "selection_metric": selection_metric,
            "metric_scope": "selection_holdout",
            "ref_kind": "task_artifact",
            "infer_selector": "Model/model_selector",
            "infer_target": candidate_selector(item),
            "model_params": json.dumps(item.model_params, sort_keys=True, default=str),
            "artifact_name": item.artifact_name,
            "artifact_path": str(item.artifacts["model"]),
        }
        for name in LEADERBOARD_METRICS:
            row[name] = item.metrics.get(name)
        if selection_metric not in LEADERBOARD_METRICS:
            row[selection_metric] = item.metrics.get(selection_metric)
        rows.append(row)
    return rows


def write_leaderboard_artifacts(
    *,
    leaderboard_rows: list[dict[str, Any]],
    stage_dir: Path,
) -> LeaderboardArtifacts:
    leaderboard_path = write_leaderboard_table(leaderboard_rows, stage_dir / "leaderboard.csv")
    leaderboard_metric_panel_path = write_leaderboard_metric_panel(
        leaderboard_rows,
        stage_dir / "leaderboard_metric_panel.png",
        top_k=LEADERBOARD_TOP_K,
    )
    return LeaderboardArtifacts(
        tables={
            "leaderboard": leaderboard_path,
        },
        plots={
            "leaderboard_metric_panel": leaderboard_metric_panel_path,
        },
    )
