import numpy as np
import pandas as pd
import pytest

from ml_platform_core.config import load_run_config
from ml_platform_core.io import read_json
from ml_platform_tabular.inference import run_infer
from ml_platform_tabular.models import DEPENDENCY_FREE_MODELS
from ml_platform_tabular.training import run_pipeline


def _write_training_data(tmp_path, *, rows=80):
    rng = np.random.default_rng(2)
    df = pd.DataFrame(
        {
            "id": range(rows),
            "x1": rng.normal(size=rows),
            "x2": rng.normal(size=rows),
        }
    )
    df["target"] = 1.5 * df["x1"] + 0.5 * df["x2"] + rng.normal(scale=0.1, size=rows)
    train_path = tmp_path / "train.csv"
    infer_path = tmp_path / "infer.csv"
    df.to_csv(train_path, index=False)
    df.drop(columns=["target"]).head(8).to_csv(infer_path, index=False)
    return train_path, infer_path


def test_local_training_pipeline_default_graph_and_artifacts(tmp_path):
    train_path, _ = _write_training_data(tmp_path)
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["model"]["candidates"] = list(DEPENDENCY_FREE_MODELS)

    result = run_pipeline(cfg)

    _assert_training_pipeline_shape(result, tmp_path)
    _assert_training_pipeline_outputs_exist(result)
    _assert_training_leaderboard_outputs(result)
    _assert_training_best_model_decision(result)
    _assert_training_reference_artifacts(result)
    _assert_training_feature_and_manifest_outputs(result, tmp_path)


def _assert_training_pipeline_shape(result, tmp_path):
    assert result.extra["pipeline_kind"] == "training"
    assert result.extra["stages"][0] == "preprocess_features"
    assert result.extra["stages"][-1] == "evaluate_models"
    assert "infer_predictions" not in result.tables
    assert all((result.run_dir / stage).is_dir() for stage in _expected_pipeline_stage_dirs())
    assert (tmp_path / "outputs" / "latest_training_pipeline" / "manifest.json").exists()
    assert not (tmp_path / "outputs" / "latest_train").exists()


def _assert_training_pipeline_outputs_exist(result):
    _assert_named_paths_exist(result.artifacts, _expected_training_artifacts())
    _assert_named_paths_exist(result.tables, _expected_training_tables())


def _assert_named_paths_exist(paths, names):
    assert set(names) <= set(paths)
    assert all(paths[name].exists() for name in names)


def _assert_training_leaderboard_outputs(result):
    leaderboard = pd.read_csv(result.tables["leaderboard"])
    assert set(_expected_training_candidates()) <= set(leaderboard["model_name"])
    assert {"artifact_kind", "ensemble_method", "ref_kind", "infer_selector", "infer_target"} <= set(
        leaderboard.columns
    )
    assert "ensemble:median" in set(leaderboard["infer_target"])
    assert list(leaderboard["rank"]) == list(range(1, len(leaderboard) + 1))
    validation_predictions = pd.read_csv(result.tables["validation_predictions_linear"])
    assert {"actual", "prediction", "residual", "abs_error", "model_name"} <= set(validation_predictions.columns)
    assert _expected_training_plots_present() <= set(result.plots)
    assert _expected_training_plots_absent().isdisjoint(result.plots)
    assert result.plots["feature_importance_bar_linear"].suffix == ".png"

    evaluation_predictions = pd.read_csv(result.tables["evaluation_predictions"])
    assert {"actual", "prediction", "residual", "abs_error", "model_name"} <= set(evaluation_predictions.columns)


def _assert_training_best_model_decision(result):
    best_model = read_json(result.artifacts["best_model_json"])
    assert best_model["model_selector"] == "best"
    assert best_model["candidate_selector"]
    assert best_model["recommended_inference_settings"] == {
        "Model/source_type": "task_id",
        "Model/source_task_id": "<training_or_evaluate_task_id>",
        "Model/model_selector": "best",
    }
    assert best_model["artifact_kind"] in {"model", "ensemble"}
    assert best_model["selection_metric"] == "rmse"
    assert {"rmse", "mae", "r2"} <= set(best_model["metrics"])
    assert "predictions" not in result.tables


def _assert_training_reference_artifacts(result):
    best_model = read_json(result.artifacts["best_model_json"])
    assert best_model["best_model_artifact"] == str(result.artifacts["best_model"])
    assert result.artifacts["best_model"].exists()
    assert result.extra["best_model"]["model_name"] == best_model["model_name"]


def _assert_training_feature_and_manifest_outputs(result, tmp_path):
    feature_spec = read_json(result.artifacts["feature_spec"])
    assert feature_spec["feature_config"]["preset"] == "basic"
    assert feature_spec["feature_config"]["numeric_impute_strategy"] == "median"
    assert feature_spec["drop_columns"] == []
    assert feature_spec["passthrough_columns"] == []
    assert feature_spec["split"]["method"] == "random"
    assert feature_spec["split"]["train_rows"] + feature_spec["split"]["valid_rows"] == 80
    feature_summary = read_json(result.artifacts["feature_summary"])
    assert feature_summary["feature_config"]["categorical_encoder"] == "onehot"
    assert feature_summary["passthrough_feature_count"] == 0
    data_quality_summary = read_json(result.artifacts["data_quality_summary"])
    assert data_quality_summary["row_count"] == 80
    assert data_quality_summary["target_column"] == "target"
    assert data_quality_summary["target_is_numeric"] is True
    assert data_quality_summary["split"]["method"] == "random"

    manifest = read_json(result.artifacts["manifest"])
    assert manifest["extra"]["pipeline_kind"] == "training"
    assert manifest["extra"]["report_schema_version"] == "leaderboard_dashboard_v2"
    assert "infer_predictions" not in manifest["tables"]
    assert "data_quality_summary_table" in manifest["tables"]
    assert "data_quality_warnings" in manifest["tables"]
    assert "leaderboard_metric_panel" in manifest["plots"]
    assert "best_prediction_vs_actual" in manifest["plots"]


def _expected_pipeline_stage_dirs():
    return [
        "preprocess_features",
        "train_linear",
        "train_ridge",
        "train_lasso",
        "train_elasticnet",
        "train_random_forest",
        "train_extra_trees",
        "train_gradient_boosting",
        "build_ensemble",
        "evaluate_models",
    ]


def _expected_training_artifacts():
    return [
        "preprocess_bundle",
        "feature_spec",
        "feature_summary",
        "data_quality_summary",
        "leaderboard",
        "best_model",
        "best_model_json",
        "evaluation_predictions",
        "metrics",
        "manifest",
        "config",
        "ensemble",
        "ensemble_info",
        "ensemble_refs",
        "ensemble_mean_topk",
        "ensemble_weighted",
        "ensemble_median",
    ]


def _expected_training_tables():
    return [
        "feature_summary_table",
        "missing_rate_by_column",
        "feature_type_counts",
        "data_quality_summary_table",
        "data_quality_warnings",
        "processed_train",
        "processed_valid",
        "train_features",
        "valid_features",
        "leaderboard",
        "evaluation_predictions",
        "metrics_table_linear",
        "validation_predictions_linear",
        "validation_predictions_ridge",
        "validation_predictions_lasso",
        "validation_predictions_elasticnet",
        "validation_predictions_random_forest",
        "validation_predictions_extra_trees",
        "validation_predictions_gradient_boosting",
        "feature_importance_linear",
        "feature_importance_ridge",
        "ensemble_predictions",
        "ensemble_metrics_table",
        "ensemble_predictions_mean_topk",
        "ensemble_predictions_weighted",
        "ensemble_predictions_median",
        "ensemble_members_mean_topk",
        "ensemble_members_weighted",
        "ensemble_members_median",
        "ensemble_weights_mean_topk",
        "ensemble_weights_weighted",
        "ensemble_weights_median",
    ]


def _expected_training_candidates():
    return [*DEPENDENCY_FREE_MODELS, "mean_topk", "weighted", "median"]


def _expected_training_plots_present():
    return {
        "validation_prediction_vs_actual_linear",
        "validation_residual_histogram_linear",
        "validation_residual_vs_predicted_linear",
        "leaderboard_metric_panel",
        "missing_rate_by_column_bar",
        "feature_importance_bar_linear",
        "ensemble_weights_mean_topk",
        "ensemble_weights_weighted",
        "ensemble_metrics_bar",
        "best_prediction_vs_actual",
        "best_residual_histogram",
        "best_residual_vs_predicted",
    }


def _expected_training_plots_absent():
    return {"prediction_vs_actual", "residual_histogram", "residual_vs_predicted"}


def test_local_training_pipeline_rejects_search_enabled_primary_flow(tmp_path):
    train_path, _ = _write_training_data(tmp_path, rows=40)
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["model"]["name"] = "ridge"
    cfg["model"]["params"] = {}
    cfg["model"]["candidates"] = []
    cfg["model"]["ensemble"]["enabled"] = False
    cfg["model"]["search"] = {
        "enabled": True,
        "method": "grid",
        "max_trials": 2,
        "search_space": {"alpha": [0.1, 1.0]},
    }

    with pytest.raises(ValueError, match="future/experimental"):
        run_pipeline(cfg)


def test_training_pipeline_feature_drop_passthrough_and_infer_alignment(tmp_path):
    rng = np.random.default_rng(8)
    rows = 50
    df = pd.DataFrame(
        {
            "id": range(rows),
            "x1": rng.normal(size=rows),
            "x2": rng.normal(size=rows),
            "raw_numeric": rng.normal(size=rows),
            "unused": rng.normal(size=rows),
            "segment": ["a", "b"] * (rows // 2),
        }
    )
    df["target"] = 1.2 * df["x1"] - 0.4 * df["x2"] + 0.2 * df["raw_numeric"] + rng.normal(scale=0.05, size=rows)
    train_path = tmp_path / "train.csv"
    infer_path = tmp_path / "infer.csv"
    df.to_csv(train_path, index=False)
    df.drop(columns=["target", "unused"]).head(6).to_csv(infer_path, index=False)

    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["features"]["drop_columns"] = ["unused"]
    cfg["features"]["passthrough_columns"] = ["raw_numeric"]
    cfg["model"]["candidates"] = ["linear", "ridge"]
    cfg["model"]["ensemble"]["enabled"] = False

    result = run_pipeline(cfg)
    feature_spec = read_json(result.artifacts["feature_spec"])

    assert "unused" not in feature_spec["feature_columns"]
    assert feature_spec["drop_columns"] == ["unused"]
    assert feature_spec["passthrough_columns"] == ["raw_numeric"]
    assert "raw_numeric" in feature_spec["transformed_columns"]

    infer_cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")
    infer_cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    infer_cfg["data"]["local_path"] = str(infer_path)
    infer_cfg["model"]["source_type"] = "local_path"
    infer_cfg["model"]["local_model_path"] = str(result.run_dir)
    infer_cfg["model"]["model_selector"] = "best"

    infer_result = run_infer(infer_cfg)
    assert infer_result.tables["predictions"].exists()
    assert infer_result.tables["schema_check_summary"].exists()
    assert infer_result.tables["prediction_summary"].exists()
    assert infer_result.tables["prediction_preview"].exists()
    assert infer_result.tables["source_summary"].exists()
    predictions = pd.read_csv(infer_result.tables["predictions"])
    assert {"row_index", "prediction", "model_name", "artifact_kind"} <= set(predictions.columns)
    assert "unused" not in predictions.columns
    assert "raw_numeric" not in predictions.columns
    schema_check = read_json(infer_result.artifacts["schema_check_summary"])
    assert schema_check["status"] == "ok"
    assert "prediction_distribution" in infer_result.plots
    assert "prediction_distribution_histogram" in infer_result.plots


def test_local_training_pipeline_without_ensemble(tmp_path):
    train_path, _ = _write_training_data(tmp_path, rows=50)
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["model"]["candidates"] = ["linear", "ridge"]
    cfg["model"]["params"] = {"ridge": {"alpha": 1.0}}
    cfg["model"]["ensemble"]["enabled"] = False

    result = run_pipeline(cfg)

    assert "build_ensemble" not in result.extra["stages"]
    assert "ensemble" not in result.artifacts
    leaderboard = pd.read_csv(result.tables["leaderboard"])
    assert set(leaderboard["model_name"]) == {"linear", "ridge"}
    best_model = read_json(result.artifacts["best_model_json"])
    assert best_model["artifact_kind"] == "model"
    assert best_model["candidate_selector"] in {"linear", "ridge"}
    assert best_model["recommended_inference_settings"]["Model/model_selector"] == "best"


def test_infer_can_reference_local_training_pipeline_best_and_ensemble(tmp_path):
    train_path, infer_path = _write_training_data(tmp_path, rows=60)
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["model"]["candidates"] = list(DEPENDENCY_FREE_MODELS)
    pipeline_result = run_pipeline(cfg)

    infer_cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")
    infer_cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    infer_cfg["data"]["local_path"] = str(infer_path)
    infer_cfg["model"]["source_type"] = "local_path"
    infer_cfg["model"]["local_model_path"] = str(pipeline_result.run_dir)
    infer_cfg["model"]["model_selector"] = "best"
    best_result = run_infer(infer_cfg)
    _assert_best_local_pipeline_inference(best_result)

    infer_cfg["model"]["model_selector"] = "ensemble"
    _assert_ensemble_local_pipeline_inference(run_infer(infer_cfg))

    infer_cfg["model"]["model_selector"] = "ensemble:median"
    _assert_median_local_pipeline_inference(run_infer(infer_cfg))


def _assert_best_local_pipeline_inference(best_result):
    best_manifest = read_json(best_result.artifacts["manifest"])
    assert best_manifest["extra"]["source_type"] == "local_path"
    assert best_manifest["extra"]["model_selector"] == "best"
    assert best_manifest["extra"]["feature_spec_path"]
    assert best_manifest["extra"]["preprocess_bundle_path"]
    assert best_manifest["extra"]["resolved_model_path"].endswith(
        "evaluate_models\\best_model.joblib"
    ) or best_manifest["extra"]["resolved_model_path"].endswith("evaluate_models/best_model.joblib")
    assert best_result.tables["predictions"].exists()
    assert best_result.tables["schema_check_summary"].exists()
    assert best_result.tables["prediction_summary"].exists()
    assert best_result.tables["prediction_preview"].exists()
    assert best_result.tables["source_summary"].exists()
    best_predictions = pd.read_csv(best_result.tables["predictions"])
    assert {"row_index", "id", "prediction"} <= set(best_predictions.columns)
    assert "x1" not in best_predictions.columns
    best_schema_check = read_json(best_result.artifacts["schema_check_summary"])
    assert best_schema_check["status"] == "ok"
    assert "prediction_distribution" in best_result.plots
    assert "prediction_distribution_histogram" in best_result.plots


def _assert_ensemble_local_pipeline_inference(ensemble_result):
    ensemble_manifest = read_json(ensemble_result.artifacts["manifest"])
    assert ensemble_manifest["extra"]["model_selector"] == "ensemble"
    assert ensemble_manifest["extra"]["artifact_kind"] == "ensemble"
    assert "build_ensemble" in ensemble_manifest["extra"]["resolved_model_path"]
    assert "model_" in ensemble_manifest["extra"]["resolved_model_path"]


def _assert_median_local_pipeline_inference(median_result):
    median_manifest = read_json(median_result.artifacts["manifest"])
    assert median_manifest["extra"]["model_selector"] == "ensemble:median"
    assert median_manifest["extra"]["ensemble_method"] == "median"
    assert median_manifest["extra"]["resolved_model_path"].endswith(
        "build_ensemble\\model_median.joblib"
    ) or median_manifest["extra"]["resolved_model_path"].endswith("build_ensemble/model_median.joblib")


def test_infer_rejects_unknown_local_training_pipeline_selector(tmp_path):
    train_path, infer_path = _write_training_data(tmp_path, rows=40)
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["model"]["candidates"] = list(DEPENDENCY_FREE_MODELS)
    pipeline_result = run_pipeline(cfg)

    infer_cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")
    infer_cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    infer_cfg["data"]["local_path"] = str(infer_path)
    infer_cfg["model"]["source_type"] = "local_path"
    infer_cfg["model"]["local_model_path"] = str(pipeline_result.run_dir)
    infer_cfg["model"]["model_selector"] = "does_not_exist"

    with pytest.raises(ValueError, match="Could not resolve model_selector"):
        run_infer(infer_cfg)
