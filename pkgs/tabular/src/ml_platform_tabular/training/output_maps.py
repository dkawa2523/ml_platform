from __future__ import annotations

from pathlib import Path

from .artifacts import CandidateResult, EvaluationResult, PreprocessResult, safe_name
from .best_model_artifacts import BestModelArtifacts
from .leaderboard_artifacts import LeaderboardArtifacts


def _add_optional_path(mapping: dict[str, Path], key: str, path: Path | None) -> None:
    if path is not None:
        mapping[key] = path


def training_pipeline_outputs(
    preprocess: PreprocessResult,
    model_results: list[CandidateResult],
    ensemble_result: CandidateResult | None,
    evaluation: EvaluationResult,
) -> tuple[dict[str, Path], dict[str, Path], dict[str, Path]]:
    artifacts: dict[str, Path] = {
        **preprocess.artifacts,
        **evaluation.artifacts,
    }
    tables: dict[str, Path] = {
        **preprocess.tables,
        **evaluation.tables,
    }
    plots: dict[str, Path] = {**evaluation.plots, **preprocess.plots}
    _add_model_outputs(artifacts, tables, plots, model_results)
    _add_ensemble_outputs(artifacts, tables, plots, ensemble_result)
    return artifacts, tables, plots


def evaluation_artifacts(
    best_outputs: BestModelArtifacts,
    metrics_path: Path,
) -> dict[str, Path]:
    return {**best_outputs.artifacts, "metrics": metrics_path}


def evaluation_tables(
    leaderboard_outputs: LeaderboardArtifacts,
    evaluation_predictions_path: Path | None,
) -> dict[str, Path]:
    tables = dict(leaderboard_outputs.tables)
    _add_optional_path(tables, "evaluation_predictions", evaluation_predictions_path)
    return tables


def _add_model_outputs(
    artifacts: dict[str, Path],
    tables: dict[str, Path],
    plots: dict[str, Path],
    model_results: list[CandidateResult],
) -> None:
    for item in model_results:
        key = safe_name(item.model_name)
        artifacts[f"model_{key}"] = item.artifacts["model"]
        artifacts[f"model_info_{key}"] = item.artifacts["model_info"]
        artifacts[f"metrics_{key}"] = item.artifacts["metrics"]
        tables[f"metrics_table_{key}"] = item.tables["metrics_table"]
        tables[f"validation_predictions_{key}"] = item.tables["validation_predictions"]
        for plot_name, plot_path in item.plots.items():
            plots[f"{plot_name}_{key}"] = plot_path


def _add_ensemble_outputs(
    artifacts: dict[str, Path],
    tables: dict[str, Path],
    plots: dict[str, Path],
    ensemble_result: CandidateResult | None,
) -> None:
    if ensemble_result is None:
        return
    artifacts["ensemble"] = ensemble_result.artifacts["model"]
    artifacts["ensemble_model_info"] = ensemble_result.artifacts["model_info"]
    artifacts["ensemble_refs"] = ensemble_result.artifacts["ensemble_refs"]
    for table_name, table_path in ensemble_result.tables.items():
        tables[table_name] = table_path
    for item in _ensemble_results(ensemble_result):
        method = item.ensemble_method
        artifacts[f"ensemble_{method}"] = item.artifacts["model"]
        artifacts[f"ensemble_model_info_{method}"] = item.artifacts["model_info"]
        artifacts[f"ensemble_metrics_{method}"] = item.artifacts["metrics"]
    for plot_name, plot_path in ensemble_result.plots.items():
        plots[plot_name] = plot_path


def _ensemble_results(ensemble_result: CandidateResult) -> list[CandidateResult]:
    return list(ensemble_result.ensemble_results)
