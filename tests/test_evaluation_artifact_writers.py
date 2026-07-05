from __future__ import annotations

import pandas as pd

from ml_platform_core.io import read_json
from ml_platform_tabular.training.artifacts import CandidateResult
from ml_platform_tabular.training.best_model_artifacts import write_best_model_artifacts
from ml_platform_tabular.training.evaluation import evaluate_model_candidates


def _candidate(tmp_path, name: str, *, rmse: float, prediction_offset: float = 0.0) -> CandidateResult:
    source_dir = tmp_path / "source" / name
    source_dir.mkdir(parents=True, exist_ok=True)
    model_path = source_dir / "model.joblib"
    model_path.write_text(f"{name} model", encoding="utf-8")
    model_info_path = source_dir / "model_info.json"
    model_info_path.write_text("{}", encoding="utf-8")
    metrics_path = source_dir / "metrics.json"
    metrics_path.write_text("{}", encoding="utf-8")
    predictions_path = source_dir / "validation_predictions.csv"
    pd.DataFrame(
        {
            "actual": [1.0, 2.0, 3.0],
            "prediction": [1.0 + prediction_offset, 2.0 + prediction_offset, 3.0 + prediction_offset],
        }
    ).to_csv(predictions_path, index=False)
    return CandidateResult(
        stage=f"train_{name}",
        stage_dir=source_dir,
        model_name=name,
        artifact_kind="model",
        model_params={},
        estimator=object(),
        predictions=None,
        metrics={"rmse": rmse, "mae": rmse / 2, "r2": 0.9 - rmse},
        artifacts={
            "model": model_path,
            "model_info": model_info_path,
            "metrics": metrics_path,
        },
        tables={"validation_predictions": predictions_path},
    )


def test_best_model_writer_preserves_copy_and_json_contract(tmp_path):
    stage_dir = tmp_path / "evaluate_models"
    stage_dir.mkdir()
    best = _candidate(tmp_path, "ridge", rmse=0.2)

    outputs = write_best_model_artifacts(
        best=best,
        best_ensemble=None,
        selection_metric="rmse",
        stage_dir=stage_dir,
        task_id="task-123",
        code_version="abc123",
    )

    assert outputs.artifacts["best_model"] == stage_dir / "best_model.joblib"
    assert outputs.artifacts["best_model_json"] == stage_dir / "best_model.json"
    assert outputs.artifacts["best_model"].read_text(encoding="utf-8") == "ridge model"
    payload = read_json(outputs.artifacts["best_model_json"])
    assert payload["model_name"] == "ridge"
    assert payload["best_model_artifact"] == str(stage_dir / "best_model.joblib")
    assert payload["model_selector"] == "best"
    assert payload["candidate_selector"] == "ridge"
    assert payload["recommended_inference_settings"] == {
        "Model/source_type": "task_id",
        "Model/source_task_id": "task-123",
        "Model/model_selector": "best",
    }
    assert outputs.best_ensemble is None


def test_evaluate_model_candidates_preserves_public_artifact_names(tmp_path):
    linear = _candidate(tmp_path, "linear", rmse=0.3, prediction_offset=0.2)
    ridge = _candidate(tmp_path, "ridge", rmse=0.2, prediction_offset=0.1)

    result = evaluate_model_candidates(
        {"runtime": {"clearml_task_id": "task-123"}},
        [linear, ridge],
        None,
        tmp_path / "run",
        "rmse",
    )

    assert result.best.model_name == "ridge"
    assert {
        "best_model",
        "best_model_json",
        "evaluation_predictions",
        "metrics",
    } <= set(result.artifacts)
    assert {
        "evaluation_predictions",
        "leaderboard",
    } <= set(result.tables)
    assert {
        "best_prediction_vs_actual",
        "best_residual_histogram",
        "best_residual_vs_predicted",
        "leaderboard_metric_panel",
    } <= set(result.plots)
    best_model = read_json(result.artifacts["best_model_json"])
    assert best_model["recommended_inference_settings"]["Model/source_task_id"] == "task-123"
    assert result.metrics["source_task_id"] == "task-123"
