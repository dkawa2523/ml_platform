from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from ml_platform_core.io import write_table

from ..plotting import (
    topk_candidate_predictions,
    write_candidate_prediction_vs_actual_plot,
    write_candidate_residual_histogram,
    write_candidate_residual_vs_predicted_plot,
    write_prediction_vs_actual_plot,
    write_residual_histogram,
    write_residual_vs_predicted_plot,
)
from .artifacts import CandidateResult, LEADERBOARD_TOP_K


PREDICTION_COLUMNS = {"actual", "prediction"}


def prediction_table_path(item: CandidateResult) -> Path | None:
    path = item.tables.get("validation_predictions") or item.tables.get("ensemble_predictions")
    return Path(path) if path else None


def _prediction_frame(item: CandidateResult) -> pd.DataFrame | None:
    source = prediction_table_path(item)
    if source is None or not source.exists():
        return None
    frame = pd.read_csv(source)
    if not PREDICTION_COLUMNS <= set(frame.columns):
        return None
    return frame


def write_evaluation_predictions(best: CandidateResult, stage_dir: Path) -> tuple[Path | None, dict[str, Path]]:
    source = prediction_table_path(best)
    if source is None or not source.exists():
        return None, {}
    frame = _prediction_frame(best)
    destination = stage_dir / "evaluation_predictions.csv"
    if source != destination:
        shutil.copy2(source, destination)
    return destination, _best_prediction_plots(frame, stage_dir) if frame is not None else {}


def _best_prediction_plots(frame: pd.DataFrame, stage_dir: Path) -> dict[str, Path]:
    scatter = write_prediction_vs_actual_plot(
        frame["actual"],
        frame["prediction"],
        stage_dir / "best_prediction_vs_actual.png",
        title="Best prediction vs actual",
    )
    residual = write_residual_histogram(
        frame["actual"],
        frame["prediction"],
        stage_dir / "best_residual_histogram.png",
        title="Best residual histogram",
    )
    residual_vs_predicted = write_residual_vs_predicted_plot(
        frame["actual"],
        frame["prediction"],
        stage_dir / "best_residual_vs_predicted.png",
        title="Best residuals vs predicted",
    )
    return {
        "best_prediction_vs_actual": scatter,
        "best_residual_histogram": residual,
        "best_residual_vs_predicted": residual_vs_predicted,
    }


def _candidate_prediction_frame(rank: int, item: CandidateResult) -> pd.DataFrame | None:
    frame = _prediction_frame(item)
    if frame is None:
        return None
    frame = frame.copy()
    frame.insert(0, "candidate_rank", rank)
    frame.insert(1, "candidate_name", item.model_name)
    frame.insert(2, "artifact_kind", item.artifact_kind)
    frame.insert(3, "ensemble_method", item.ensemble_method)
    frame.insert(4, "source_stage", item.stage)
    _ensure_error_columns(frame)
    return frame


def _ensure_error_columns(frame: pd.DataFrame) -> None:
    if "residual" not in frame.columns:
        frame["residual"] = pd.to_numeric(frame["actual"], errors="coerce") - pd.to_numeric(
            frame["prediction"], errors="coerce"
        )
    if "abs_error" not in frame.columns:
        frame["abs_error"] = frame["residual"].abs()


def write_candidate_predictions(
    candidates: list[CandidateResult], stage_dir: Path
) -> tuple[Path | None, dict[str, Path]]:
    frames = []
    for rank, item in enumerate(candidates, start=1):
        frame = _candidate_prediction_frame(rank, item)
        if frame is not None:
            frames.append(frame)
    if not frames:
        return None, {}
    combined = pd.concat(frames, ignore_index=True)
    predictions_path = write_table(combined, stage_dir / "candidate_predictions.csv")
    topk = topk_candidate_predictions(combined, top_k=LEADERBOARD_TOP_K)
    plots = {
        "topk_prediction_vs_actual": write_candidate_prediction_vs_actual_plot(
            topk,
            stage_dir / "topk_prediction_vs_actual.png",
            title=f"Top-{LEADERBOARD_TOP_K} prediction vs actual",
        ),
        "topk_residual_histogram": write_candidate_residual_histogram(
            topk,
            stage_dir / "topk_residual_histogram.png",
            title=f"Top-{LEADERBOARD_TOP_K} residual histogram",
        ),
        "topk_residual_vs_predicted": write_candidate_residual_vs_predicted_plot(
            topk,
            stage_dir / "topk_residual_vs_predicted.png",
            title=f"Top-{LEADERBOARD_TOP_K} residuals vs predicted",
        ),
    }
    return predictions_path, plots
