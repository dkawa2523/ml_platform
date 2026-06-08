import numpy as np
import pandas as pd
import pytest

from ml_platform_core.config import load_run_config
from ml_platform_tabular import run_task


def _write_training_data(tmp_path, *, rows=60):
    rng = np.random.default_rng(12)
    df = pd.DataFrame(
        {
            "id": range(rows),
            "x1": rng.normal(size=rows),
            "x2": rng.normal(size=rows),
        }
    )
    df["target"] = 2.0 * df["x1"] - 0.25 * df["x2"] + rng.normal(scale=0.1, size=rows)
    path = tmp_path / "train.csv"
    df.to_csv(path, index=False)
    return path


def _stage_cfg(tmp_path, stage, train_path):
    cfg = load_run_config("config/tasks/tabular_stage.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["run"]["name"] = stage
    cfg["run"]["stage"] = stage
    cfg["data"]["local_path"] = str(train_path)
    return cfg


def _preprocess_refs(preprocess_result):
    return {
        "preprocess_bundle": str(preprocess_result.artifacts["preprocess_bundle"]),
        "feature_spec": str(preprocess_result.artifacts["feature_spec"]),
        "processed_train": str(preprocess_result.tables["processed_train"]),
        "processed_valid": str(preprocess_result.tables["processed_valid"]),
    }


def _model_ref(stage, result):
    return {
        "stage": stage,
        "model_name": stage.replace("train_", ""),
        "model": str(result.artifacts["model"]),
        "model_info": str(result.artifacts["model_info"]),
        "metrics": str(result.artifacts["metrics"]),
        "validation_predictions": str(result.tables["validation_predictions"]),
    }


def test_tabular_stage_runner_executes_training_graph_pieces(tmp_path):
    train_path = _write_training_data(tmp_path)

    preprocess_cfg = _stage_cfg(tmp_path, "preprocess_features", train_path)
    preprocess = run_task(preprocess_cfg)

    assert preprocess.artifacts["preprocess_bundle"].exists()
    assert preprocess.artifacts["feature_spec"].exists()
    assert preprocess.artifacts["feature_summary"].exists()
    assert preprocess.tables["processed_train"].exists()
    assert preprocess.tables["processed_valid"].exists()

    train_results = []
    for model_name in ["linear", "ridge"]:
        cfg = _stage_cfg(tmp_path, f"train_{model_name}", train_path)
        cfg["run"]["stage"] = "train_model"
        cfg["model"]["name"] = model_name
        cfg["model"]["params"] = {"alpha": 1.0} if model_name == "ridge" else {}
        cfg["stage_inputs"].update(_preprocess_refs(preprocess))
        train_results.append((f"train_{model_name}", run_task(cfg)))

    for _, result in train_results:
        assert result.artifacts["model"].exists()
        assert result.artifacts["model_info"].exists()
        assert result.artifacts["metrics"].exists()
        assert result.tables["validation_predictions"].exists()
        assert "prediction_vs_actual" in result.plots
        assert "residual_histogram" in result.plots

    model_refs = [_model_ref(stage, result) for stage, result in train_results]
    ensemble_cfg = _stage_cfg(tmp_path, "build_ensemble", train_path)
    ensemble_cfg["run"]["stage"] = "build_ensemble"
    ensemble_cfg["model"]["selection_metric"] = "rmse"
    ensemble_cfg["model"]["ensemble"] = {"enabled": True, "method": "mean_topk", "top_k": 2}
    ensemble_cfg["stage_inputs"].update(_preprocess_refs(preprocess))
    ensemble_cfg["stage_inputs"]["model_refs"] = model_refs
    ensemble = run_task(ensemble_cfg)

    assert ensemble.artifacts["model"].exists()
    assert ensemble.artifacts["ensemble_info"].exists()
    assert ensemble.tables["ensemble_predictions"].exists()

    eval_cfg = _stage_cfg(tmp_path, "evaluate_models", train_path)
    eval_cfg["run"]["stage"] = "evaluate_models"
    eval_cfg["model"]["selection_metric"] = "rmse"
    eval_cfg["stage_inputs"]["model_refs"] = model_refs
    eval_cfg["stage_inputs"]["ensemble_ref"] = {
        "stage": "build_ensemble",
        "model_name": "mean_topk",
        "model": str(ensemble.artifacts["model"]),
        "model_info": str(ensemble.artifacts["model_info"]),
        "ensemble_info": str(ensemble.artifacts["ensemble_info"]),
        "metrics": str(ensemble.artifacts["metrics"]),
        "ensemble_predictions": str(ensemble.tables["ensemble_predictions"]),
    }
    evaluation = run_task(eval_cfg)

    assert evaluation.tables["leaderboard"].exists()
    assert evaluation.tables["evaluation_predictions"].exists()
    assert evaluation.artifacts["model_refs"].exists()
    assert evaluation.artifacts["metrics_by_model"].exists()
    assert evaluation.artifacts["best_model"].exists()
    assert evaluation.artifacts["best_model_json"].exists()
    assert evaluation.artifacts["evaluation_report"].exists()
    assert evaluation.artifacts["manifest"].exists()
    assert "metrics_by_model_bar" in evaluation.plots
    assert "prediction_vs_actual" in evaluation.plots
    assert "residual_histogram" in evaluation.plots


def test_tabular_stage_runner_rejects_future_optimization_stages(tmp_path):
    train_path = _write_training_data(tmp_path, rows=50)

    search_cfg = _stage_cfg(tmp_path, "search_trials", train_path)
    search_cfg["run"]["stage"] = "search_trials"
    with pytest.raises(ValueError, match="future/experimental"):
        run_task(search_cfg)
