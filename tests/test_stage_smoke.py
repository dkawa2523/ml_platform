import numpy as np
import pandas as pd
import pytest

from ml_platform_core.config import load_run_config
from ml_platform_core.io import read_json
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
    assert preprocess.artifacts["data_quality_summary"].exists()
    assert preprocess.tables["feature_summary_table"].exists()
    assert preprocess.tables["feature_summary"].exists()
    assert preprocess.tables["missing_rate_by_column"].exists()
    assert preprocess.tables["feature_missingness"].exists()
    assert preprocess.tables["feature_type_counts"].exists()
    assert preprocess.tables["data_quality_summary_table"].exists()
    assert preprocess.tables["data_quality_warnings"].exists()
    assert preprocess.tables["processed_train"].exists()
    assert preprocess.tables["processed_valid"].exists()
    assert "missing_rate_by_column_bar" in preprocess.plots
    assert "feature_missingness_bar" in preprocess.plots

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
        assert result.tables["metrics_table"].exists()
        assert result.tables["validation_predictions"].exists()
        assert result.tables["feature_importance"].exists()
        assert "validation_prediction_vs_actual" in result.plots
        assert "validation_residual_histogram" in result.plots
        assert "validation_residual_vs_predicted" in result.plots
        assert "feature_importance" in result.plots
        assert "feature_importance_bar" in result.plots

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
    assert ensemble.tables["ensemble_metrics_table"].exists()
    assert ensemble.tables["ensemble_predictions"].exists()
    assert ensemble.tables["ensemble_members_mean_topk"].exists()
    assert ensemble.tables["ensemble_weights_mean_topk"].exists()
    assert "ensemble_metrics_bar" in ensemble.plots

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
    assert evaluation.tables["leaderboard_topk"].exists()
    assert evaluation.tables["metrics_by_candidate"].exists()
    assert evaluation.tables["evaluation_summary"].exists()
    assert evaluation.tables["leaderboard_decision_summary"].exists()
    assert evaluation.tables["best_vs_ensemble_summary"].exists()
    assert evaluation.tables["evaluation_predictions"].exists()
    assert evaluation.tables["candidate_predictions"].exists()
    assert evaluation.artifacts["model_refs"].exists()
    assert evaluation.artifacts["metrics_by_model"].exists()
    assert evaluation.artifacts["metrics_by_candidate"].exists()
    assert evaluation.artifacts["best_model"].exists()
    assert evaluation.artifacts["best_model_json"].exists()
    assert evaluation.artifacts["evaluation_report"].exists()
    assert evaluation.artifacts["recommendation"].exists()
    assert evaluation.artifacts["decision_summary"].exists()
    assert evaluation.artifacts["decision_summary_json"].exists()
    assert evaluation.artifacts["manifest"].exists()
    decision_summary = read_json(evaluation.artifacts["decision_summary_json"])
    assert decision_summary["recommended_inference_settings"]["Model/source_type"] == "task_id"
    assert decision_summary["recommended_inference_settings"]["Model/model_selector"] == "best"
    assert decision_summary["recommended_candidate_selector"]
    assert decision_summary["leaderboard_top5"]
    assert decision_summary["best_single_model"]["artifact_kind"] == "model"
    assert decision_summary["best_ensemble"]["artifact_kind"] == "ensemble"
    assert evaluation.extra["report_schema_version"] == "leaderboard_dashboard_v2"
    assert "metrics_by_candidate_bar" in evaluation.plots
    assert "leaderboard_topk_score_bar" in evaluation.plots
    assert "leaderboard_metric_panel" in evaluation.plots
    assert "leaderboard_pareto_rmse_r2" in evaluation.plots
    assert "best_prediction_vs_actual" in evaluation.plots
    assert "best_residual_histogram" in evaluation.plots
    assert "best_residual_vs_predicted" in evaluation.plots
    assert "prediction_vs_actual" not in evaluation.plots
    assert "residual_histogram" not in evaluation.plots
    assert "residual_vs_predicted" not in evaluation.plots
    assert "topk_prediction_vs_actual" in evaluation.plots
    assert "topk_residual_histogram" in evaluation.plots
    assert "topk_residual_vs_predicted" in evaluation.plots
    evaluation_manifest = read_json(evaluation.artifacts["manifest"])
    assert "leaderboard_topk_score_bar" in evaluation_manifest["plots"]
    assert "best_prediction_vs_actual" in evaluation_manifest["plots"]


def test_tabular_stage_runner_rejects_unsupported_stages(tmp_path):
    train_path = _write_training_data(tmp_path, rows=50)

    search_cfg = _stage_cfg(tmp_path, "unknown_stage", train_path)
    search_cfg["run"]["stage"] = "unknown_stage"
    with pytest.raises(ValueError, match="Unsupported tabular stage"):
        run_task(search_cfg)
