import numpy as np
import pandas as pd
import pytest

from ml_platform_core.config import load_run_config
from ml_platform_core.io import read_json
from ml_platform_tabular.infer import run_infer
from ml_platform_tabular.pipeline import run_pipeline


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


def _old_style_pipeline_cfg(tmp_path, train_path, infer_path):
    # Deprecated compatibility config only. This is not the product training pipeline.
    cfg = {
        "task": "tabular_pipeline",
        "runtime": {"output_dir": str(tmp_path / "outputs_compat"), "use_clearml": False},
        "run": {"name": "compat_pipeline", "seed": 42, "pipeline" + "_mode": "single"},
        "train": {
            "task_config": "config/tasks/tabular_train.yaml",
            "data": {"local_path": str(train_path), "target_column": "target", "feature_columns": None, "id_columns": ["id"]},
            "model": {"name": "ridge", "params": {"alpha": 1.0}},
        },
        "eval": {
            "task_config": "config/tasks/tabular_eval.yaml",
            "data": {"local_path": str(train_path), "target_column": "target", "feature_columns": None, "id_columns": ["id"]},
        },
        "infer": {
            "task_config": "config/tasks/tabular_infer.yaml",
            "data": {"local_path": str(infer_path), "target_column": None, "feature_columns": None, "id_columns": ["id"]},
        },
    }
    return cfg


def test_local_training_pipeline_default_graph_and_artifacts(tmp_path):
    train_path, _ = _write_training_data(tmp_path)
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)

    result = run_pipeline(cfg)

    assert result.extra["pipeline_kind"] == "training"
    assert result.extra["stages"][0] == "preprocess_features"
    assert result.extra["stages"][-1] == "evaluate_models"
    assert "infer_predictions" not in result.tables
    assert (result.run_dir / "preprocess_features").is_dir()
    assert (result.run_dir / "train_linear").is_dir()
    assert (result.run_dir / "train_ridge").is_dir()
    assert (result.run_dir / "train_lasso").is_dir()
    assert (result.run_dir / "train_elasticnet").is_dir()
    assert (result.run_dir / "train_random_forest").is_dir()
    assert (result.run_dir / "train_extra_trees").is_dir()
    assert (result.run_dir / "train_gradient_boosting").is_dir()
    assert (result.run_dir / "build_ensemble").is_dir()
    assert (result.run_dir / "evaluate_models").is_dir()

    for artifact in [
        "preprocess_bundle",
        "feature_spec",
        "feature_summary",
        "model_refs",
        "metrics_by_model",
        "metrics_by_candidate",
        "leaderboard",
        "best_model",
        "best_model_json",
        "evaluation_report",
        "evaluation_predictions",
        "metrics",
        "manifest",
        "config",
        "ensemble",
        "ensemble_info",
        "ensemble_refs",
        "ensemble_info_by_method",
        "ensemble_mean_topk",
        "ensemble_weighted",
        "ensemble_median",
    ]:
        assert result.artifacts[artifact].exists()
    for table in [
        "feature_summary_table",
        "feature_summary",
        "missing_rate_by_column",
        "feature_missingness",
        "feature_type_counts",
        "processed_train",
        "processed_valid",
        "train_features",
        "valid_features",
        "leaderboard",
        "metrics_by_candidate",
        "evaluation_summary",
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
    ]:
        assert result.tables[table].exists()

    leaderboard = pd.read_csv(result.tables["leaderboard"])
    assert {
        "linear",
        "ridge",
        "lasso",
        "elasticnet",
        "random_forest",
        "extra_trees",
        "gradient_boosting",
        "mean_topk",
        "weighted",
        "median",
    } <= set(leaderboard["model_name"])
    assert {"artifact_kind", "ensemble_method", "ref_kind", "infer_selector", "infer_target"} <= set(leaderboard.columns)
    assert "ensemble:median" in set(leaderboard["infer_target"])
    assert list(leaderboard["rank"]) == list(range(1, len(leaderboard) + 1))
    validation_predictions = pd.read_csv(result.tables["validation_predictions_linear"])
    assert {"actual", "prediction", "residual", "abs_error", "_target", "_prediction", "model_name"} <= set(
        validation_predictions.columns
    )
    assert "prediction_vs_actual_linear" in result.plots
    assert "residual_histogram_linear" in result.plots
    assert "residual_vs_predicted_linear" in result.plots
    assert "metrics_by_model_bar" in result.plots
    assert "metrics_by_candidate_bar" in result.plots
    assert result.plots["metrics_by_candidate_bar"].suffix == ".png"
    assert "leaderboard_topk_score_bar" in result.plots
    assert "leaderboard_metric_panel" in result.plots
    assert "leaderboard_pareto_rmse_r2" in result.plots
    assert "missing_rate_by_column_bar" in result.plots
    assert "feature_missingness_bar" in result.plots
    assert result.plots["feature_missingness_bar"].suffix == ".png"
    assert "feature_importance_bar_linear" in result.plots
    assert result.plots["feature_importance_bar_linear"].suffix == ".png"
    assert "ensemble_weights_mean_topk" in result.plots
    assert "ensemble_weights_weighted" in result.plots
    assert "ensemble_metrics_bar" in result.plots
    assert "prediction_vs_actual" in result.plots
    assert "residual_histogram" in result.plots
    assert "residual_vs_predicted" in result.plots
    assert "best_prediction_vs_actual" in result.plots
    assert "best_residual_histogram" in result.plots
    assert "best_residual_vs_predicted" in result.plots
    assert "candidate_predictions" in result.tables
    assert "topk_prediction_vs_actual" in result.plots
    assert "topk_residual_histogram" in result.plots
    assert "topk_residual_vs_predicted" in result.plots
    assert "leaderboard_topk" in result.tables
    assert "leaderboard_decision_summary" in result.tables
    assert "best_vs_ensemble_summary" in result.tables
    assert "recommendation" in result.artifacts
    assert "decision_summary" in result.artifacts
    assert "decision_summary_json" in result.artifacts
    evaluation_predictions = pd.read_csv(result.tables["evaluation_predictions"])
    assert {"actual", "prediction", "residual", "abs_error", "model_name"} <= set(evaluation_predictions.columns)
    candidate_predictions = pd.read_csv(result.tables["candidate_predictions"])
    assert {"candidate_name", "artifact_kind", "actual", "prediction", "residual", "abs_error"} <= set(
        candidate_predictions.columns
    )
    assert {"linear", "mean_topk", "weighted", "median"} <= set(candidate_predictions["candidate_name"])
    evaluation_summary = pd.read_csv(result.tables["evaluation_summary"])
    assert {"best_overall", "best_single_model", "best_ensemble"} <= set(evaluation_summary["summary"])
    decision_summary = pd.read_csv(result.tables["leaderboard_decision_summary"])
    assert {"best_overall", "best_single_model", "best_ensemble"} <= set(decision_summary["summary"])
    best_vs_ensemble = pd.read_csv(result.tables["best_vs_ensemble_summary"])
    assert set(best_vs_ensemble["metric"]) == {"rmse", "mae", "r2"}
    recommendation = read_json(result.artifacts["recommendation"])
    assert recommendation["report_schema_version"] == "leaderboard_dashboard_v2"
    assert recommendation["recommended_infer_key"] == "Input/source_task_id + Model/model_selector"
    assert recommendation["recommended_assignment"]["Model/model_selector"]
    assert "predictions" not in result.tables

    best_model = read_json(result.artifacts["best_model_json"])
    assert best_model["best_model_artifact"] == str(result.artifacts["best_model"])
    assert result.artifacts["best_model"].exists()
    assert result.extra["best_model"]["model_name"] == best_model["model_name"]
    model_refs = read_json(result.artifacts["model_refs"])
    assert model_refs["stage"] == "evaluate_models"
    assert {item["model_name"] for item in model_refs["models"]} == {
        "linear",
        "ridge",
        "lasso",
        "elasticnet",
        "random_forest",
        "extra_trees",
        "gradient_boosting",
    }
    assert {item["model_name"] for item in model_refs["ensembles"]} == {"mean_topk", "weighted", "median"}
    assert model_refs["ensemble"]["artifact_kind"] == "ensemble"
    metrics_by_model = read_json(result.artifacts["metrics_by_model"])
    metrics_by_candidate = read_json(result.artifacts["metrics_by_candidate"])
    assert {
        "linear",
        "ridge",
        "lasso",
        "elasticnet",
        "random_forest",
        "extra_trees",
        "gradient_boosting",
        "mean_topk",
        "weighted",
        "median",
    } <= set(metrics_by_model["metrics_by_model"])
    assert metrics_by_candidate["metrics_by_candidate"] == metrics_by_model["metrics_by_model"]
    feature_spec = read_json(result.artifacts["feature_spec"])
    assert feature_spec["feature_config"]["preset"] == "basic"
    assert feature_spec["feature_config"]["numeric_impute_strategy"] == "median"
    assert feature_spec["drop_columns"] == []
    assert feature_spec["passthrough_columns"] == []
    feature_summary = read_json(result.artifacts["feature_summary"])
    assert feature_summary["feature_config"]["categorical_encoder"] == "onehot"
    assert feature_summary["passthrough_feature_count"] == 0

    manifest = read_json(result.artifacts["manifest"])
    assert manifest["extra"]["pipeline_kind"] == "training"
    assert manifest["extra"]["report_schema_version"] == "leaderboard_dashboard_v2"
    assert "infer_predictions" not in manifest["tables"]
    assert (tmp_path / "outputs" / "latest_training_pipeline" / "manifest.json").exists()
    assert not (tmp_path / "outputs" / "latest_train").exists()


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
    assert infer_result.tables["prediction_summary"].exists()
    assert infer_result.tables["prediction_preview"].exists()
    assert infer_result.tables["source_summary"].exists()
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


def test_infer_can_reference_local_training_pipeline_best_and_ensemble(tmp_path):
    train_path, infer_path = _write_training_data(tmp_path, rows=60)
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    pipeline_result = run_pipeline(cfg)

    infer_cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")
    infer_cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    infer_cfg["data"]["local_path"] = str(infer_path)
    infer_cfg["model"]["source_type"] = "local_path"
    infer_cfg["model"]["local_model_path"] = str(pipeline_result.run_dir)
    infer_cfg["model"]["model_selector"] = "best"
    best_result = run_infer(infer_cfg)

    best_manifest = read_json(best_result.artifacts["manifest"])
    assert best_manifest["extra"]["source_type"] == "local_path"
    assert best_manifest["extra"]["model_selector"] == "best"
    assert best_manifest["extra"]["feature_spec_path"]
    assert best_manifest["extra"]["preprocess_bundle_path"]
    assert best_manifest["extra"]["resolved_model_path"].endswith("evaluate_models\\best_model.joblib") or best_manifest["extra"][
        "resolved_model_path"
    ].endswith("evaluate_models/best_model.joblib")
    assert best_result.tables["predictions"].exists()
    assert best_result.tables["prediction_summary"].exists()
    assert best_result.tables["prediction_preview"].exists()
    assert best_result.tables["source_summary"].exists()
    assert "prediction_distribution" in best_result.plots
    assert "prediction_distribution_histogram" in best_result.plots

    infer_cfg["model"]["model_selector"] = "ensemble"
    ensemble_result = run_infer(infer_cfg)
    ensemble_manifest = read_json(ensemble_result.artifacts["manifest"])
    assert ensemble_manifest["extra"]["model_selector"] == "ensemble"
    assert ensemble_manifest["extra"]["artifact_kind"] == "ensemble"
    assert "build_ensemble" in ensemble_manifest["extra"]["resolved_model_path"]
    assert "model_" in ensemble_manifest["extra"]["resolved_model_path"]

    infer_cfg["model"]["model_selector"] = "ensemble:median"
    median_result = run_infer(infer_cfg)
    median_manifest = read_json(median_result.artifacts["manifest"])
    assert median_manifest["extra"]["model_selector"] == "ensemble:median"
    assert median_manifest["extra"]["ensemble_method"] == "median"
    assert median_manifest["extra"]["resolved_model_path"].endswith("build_ensemble\\model_median.joblib") or median_manifest[
        "extra"
    ]["resolved_model_path"].endswith("build_ensemble/model_median.joblib")


def test_infer_rejects_unknown_local_training_pipeline_selector(tmp_path):
    train_path, infer_path = _write_training_data(tmp_path, rows=40)
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    pipeline_result = run_pipeline(cfg)

    infer_cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")
    infer_cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    infer_cfg["data"]["local_path"] = str(infer_path)
    infer_cfg["model"]["source_type"] = "local_path"
    infer_cfg["model"]["local_model_path"] = str(pipeline_result.run_dir)
    infer_cfg["model"]["model_selector"] = "does_not_exist"

    with pytest.raises(ValueError, match="Could not resolve model_selector"):
        run_infer(infer_cfg)


def test_deprecated_train_eval_infer_fallback_is_not_product_pipeline(tmp_path):
    train_path, infer_path = _write_training_data(tmp_path, rows=50)
    cfg = _old_style_pipeline_cfg(tmp_path, train_path, infer_path)

    with pytest.raises(ValueError, match="official training graph"):
        run_pipeline(cfg)
