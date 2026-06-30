from pathlib import Path

from ml_platform_tabular.training.artifacts import CandidateResult
from ml_platform_tabular.training.summary import _best_vs_ensemble_rows, _decision_summary_payload


def _candidate(name, *, artifact_kind="model", rmse=1.0, mae=0.5, r2=0.8, ensemble_method=None):
    return CandidateResult(
        stage="evaluate_models",
        stage_dir=Path("evaluate_models"),
        model_name=name,
        model_params={},
        artifact_kind=artifact_kind,
        estimator=object(),
        predictions=None,
        metrics={"rmse": rmse, "mae": mae, "r2": r2},
        artifacts={},
        tables={},
        ensemble_method=ensemble_method,
    )


def _leaderboard_row(item):
    selector = f"ensemble:{item.ensemble_method}" if item.ensemble_method else item.model_name
    return {
        "model_name": item.model_name,
        "artifact_kind": item.artifact_kind,
        "ensemble_method": item.ensemble_method,
        "rmse": item.metrics["rmse"],
        "mae": item.metrics["mae"],
        "r2": item.metrics["r2"],
        "infer_target": selector,
    }


def _summary_for(best, best_single, best_ensemble, *, task_id=None):
    selection_metric = "rmse"
    leaderboard_rows = [_leaderboard_row(item) for item in [best, best_single, best_ensemble] if item is not None]
    best_vs_rows = _best_vs_ensemble_rows(best_single, best_ensemble)
    return _decision_summary_payload(
        best=best,
        best_single=best_single,
        best_ensemble=best_ensemble,
        selection_metric=selection_metric,
        leaderboard_rows=leaderboard_rows,
        best_vs_ensemble_rows=best_vs_rows,
        created_at="2026-06-30T00:00:00Z",
        task_id=task_id,
        code_version="test",
    )


def test_decision_summary_recommends_best_for_single_model_winner():
    best_single = _candidate("ridge", rmse=0.7)
    best_ensemble = _candidate("weighted", artifact_kind="ensemble", ensemble_method="weighted", rmse=0.8)

    summary = _summary_for(best_single, best_single, best_ensemble)

    assert summary["best_model_name"] == "ridge"
    assert summary["best_artifact_kind"] == "model"
    assert summary["recommended_model_selector"] == "best"
    assert summary["recommended_candidate_selector"] == "ridge"
    assert summary["recommended_inference_settings"] == {
        "Model/source_type": "task_id",
        "Model/source_task_id": "<training_or_evaluate_task_id>",
        "Model/model_selector": "best",
    }
    assert summary["ensemble_improved_over_best_single"] is False


def test_decision_summary_recommends_best_for_ensemble_winner():
    best_single = _candidate("ridge", rmse=0.9)
    best_ensemble = _candidate("weighted", artifact_kind="ensemble", ensemble_method="weighted", rmse=0.7)

    summary = _summary_for(best_ensemble, best_single, best_ensemble, task_id="task-123")

    assert summary["best_model_name"] == "weighted"
    assert summary["best_artifact_kind"] == "ensemble"
    assert summary["best_ensemble_method"] == "weighted"
    assert summary["recommended_model_selector"] == "best"
    assert summary["recommended_candidate_selector"] == "ensemble:weighted"
    assert summary["recommended_inference_settings"]["Model/source_task_id"] == "task-123"
    assert summary["ensemble_improved_over_best_single"] is True
