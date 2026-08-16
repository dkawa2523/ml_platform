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
        "selection_predictions": str(result.tables["selection_predictions"]),
    }


def test_tabular_stage_runner_executes_training_graph_pieces(tmp_path):
    train_path = _write_training_data(tmp_path)

    preprocess_cfg = _stage_cfg(tmp_path, "preprocess_features", train_path)
    preprocess = run_task(preprocess_cfg)

    _assert_preprocess_stage_outputs(preprocess)

    train_results = []
    for model_name in ["linear", "ridge"]:
        cfg = _stage_cfg(tmp_path, f"train_{model_name}", train_path)
        cfg["run"]["stage"] = "train_model"
        cfg["model"]["name"] = model_name
        cfg["model"]["params"] = {"alpha": 1.0} if model_name == "ridge" else {}
        cfg["stage_inputs"].update(_preprocess_refs(preprocess))
        train_results.append((f"train_{model_name}", run_task(cfg)))

    for _, result in train_results:
        _assert_train_stage_outputs(result)

    model_refs = [_model_ref(stage, result) for stage, result in train_results]
    ensemble_cfg = _stage_cfg(tmp_path, "build_ensemble", train_path)
    ensemble_cfg["run"]["stage"] = "build_ensemble"
    ensemble_cfg["model"]["selection_metric"] = "rmse"
    ensemble_cfg["model"]["ensemble"] = {"enabled": True, "method": "mean_topk", "top_k": 2}
    ensemble_cfg["stage_inputs"].update(_preprocess_refs(preprocess))
    ensemble_cfg["stage_inputs"]["model_refs"] = model_refs
    ensemble = run_task(ensemble_cfg)

    _assert_ensemble_stage_outputs(ensemble)

    eval_cfg = _stage_cfg(tmp_path, "evaluate_models", train_path)
    eval_cfg["run"]["stage"] = "evaluate_models"
    eval_cfg["model"]["selection_metric"] = "rmse"
    eval_cfg["stage_inputs"].update(_preprocess_refs(preprocess))
    eval_cfg["stage_inputs"]["model_refs"] = model_refs
    eval_cfg["stage_inputs"]["ensemble_refs"] = [
        {
            "stage": "build_ensemble",
            "model_name": "mean_topk",
            "model": str(ensemble.artifacts["model"]),
            "model_info": str(ensemble.artifacts["model_info"]),
            "metrics": str(ensemble.artifacts["metrics"]),
            "selection_predictions": str(ensemble.tables["selection_predictions"]),
        }
    ]
    evaluation = run_task(eval_cfg)

    _assert_evaluation_stage_outputs(evaluation)


def _assert_preprocess_stage_outputs(result):
    _assert_stage_paths(
        result.artifacts,
        ["preprocess_bundle", "feature_spec", "data_quality_summary"],
    )
    _assert_stage_paths(
        result.tables,
        [
            "missing_rate_by_column",
            "data_quality_warnings",
            "processed_train",
            "processed_valid",
        ],
    )
    assert "missing_rate_by_column_bar" in result.plots


def _assert_train_stage_outputs(result):
    _assert_stage_paths(result.artifacts, ["model", "model_info", "metrics"])
    _assert_stage_paths(result.tables, ["metrics_table", "selection_predictions"])
    assert result.plots == {}


def _assert_ensemble_stage_outputs(result):
    _assert_stage_paths(result.artifacts, ["model", "model_info"])
    _assert_stage_paths(
        result.tables,
        [
            "ensemble_metrics_table",
            "selection_predictions",
            "ensemble_members_mean_topk",
        ],
    )
    assert result.plots == {}


def _assert_evaluation_stage_outputs(evaluation):
    _assert_evaluation_stage_tables(evaluation)
    _assert_evaluation_stage_artifacts(evaluation)
    _assert_evaluation_best_model(evaluation)
    _assert_evaluation_plots(evaluation)


def _assert_evaluation_stage_tables(evaluation):
    _assert_stage_paths(
        evaluation.tables,
        [
            "leaderboard",
            "evaluation_predictions",
        ],
    )


def _assert_evaluation_stage_artifacts(evaluation):
    _assert_stage_paths(
        evaluation.artifacts,
        [
            "best_model",
            "best_model_json",
            "metrics",
            "manifest",
        ],
    )


def _assert_evaluation_best_model(evaluation):
    best_model = read_json(evaluation.artifacts["best_model_json"])
    assert best_model["recommended_inference_settings"]["Model/source_type"] == "task_id"
    assert best_model["recommended_inference_settings"]["Model/model_selector"] == "best"
    assert best_model["candidate_selector"]
    assert evaluation.extra["report_schema_version"] == "leaderboard_dashboard_v2"


def _assert_evaluation_plots(evaluation):
    assert "leaderboard_metric_panel" in evaluation.plots
    assert "best_prediction_vs_actual" in evaluation.plots
    assert "best_residual_histogram" in evaluation.plots
    assert "best_residual_vs_predicted" in evaluation.plots
    assert "best_feature_importance" in evaluation.plots
    assert "feature_importance" in evaluation.tables
    assert "prediction_vs_actual" not in evaluation.plots
    assert "residual_histogram" not in evaluation.plots
    assert "residual_vs_predicted" not in evaluation.plots
    evaluation_manifest = read_json(evaluation.artifacts["manifest"])
    assert "leaderboard_metric_panel" in evaluation_manifest["plots"]
    assert "best_prediction_vs_actual" in evaluation_manifest["plots"]


def _assert_stage_paths(paths, names):
    assert set(names) <= set(paths)
    assert all(paths[name].exists() for name in names)


def test_tabular_stage_runner_rejects_unsupported_stages(tmp_path):
    train_path = _write_training_data(tmp_path, rows=50)

    search_cfg = _stage_cfg(tmp_path, "unknown_stage", train_path)
    search_cfg["run"]["stage"] = "unknown_stage"
    with pytest.raises(ValueError, match="Unsupported tabular stage"):
        run_task(search_cfg)
