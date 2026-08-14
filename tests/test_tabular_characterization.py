from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pandas as pd

from ml_platform_core.config import load_run_config
from ml_platform_core.io import read_json
from ml_platform_tabular.inference import run_infer
from ml_platform_tabular.plotting import (
    write_feature_importance_plot_if_available,
    write_leaderboard_metric_panel,
    write_leaderboard_table,
    write_prediction_summary_tables,
)
from ml_platform_tabular.training import run_pipeline


def _write_characterization_data(tmp_path: Path, *, rows: int = 36) -> tuple[pd.DataFrame, Path, Path]:
    rng = np.random.default_rng(42)
    df = pd.DataFrame(
        {
            "id": range(rows),
            "x1": rng.normal(size=rows),
            "x2": rng.normal(size=rows),
            "segment": ["a", "b", "a", "c"] * (rows // 4),
        }
    )
    df["target"] = 1.4 * df["x1"] - 0.3 * df["x2"] + rng.normal(scale=0.05, size=rows)
    train_path = tmp_path / "train.csv"
    infer_path = tmp_path / "infer.csv"
    df.to_csv(train_path, index=False)
    df.drop(columns=["target"]).head(5).to_csv(infer_path, index=False)
    return df, train_path, infer_path


def _run_characterized_training(tmp_path):
    _, train_path, infer_path = _write_characterization_data(tmp_path)
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["data"]["target_column"] = "target"
    cfg["data"]["id_columns"] = ["id"]
    cfg["model"]["candidates"] = ["linear", "ridge"]
    cfg["model"]["params"] = {"ridge": {"alpha": 1.0}}
    cfg["model"]["ensemble"]["enabled"] = False
    return run_pipeline(cfg), infer_path


def _assert_all_paths_exist(paths: Mapping[str, Path]) -> None:
    for key, path in paths.items():
        assert path.exists(), key


def test_tabular_pipeline_output_contract_before_module_split(tmp_path):
    result, _ = _run_characterized_training(tmp_path)

    _assert_characterized_training_keys(result)
    _assert_all_paths_exist(result.artifacts)
    _assert_all_paths_exist(result.tables)
    _assert_all_paths_exist(result.plots)
    _assert_characterized_training_extra(result)
    _assert_characterized_leaderboard(result)
    _assert_characterized_prediction_tables(result)
    _assert_characterized_decision_and_manifest(result)


def _assert_characterized_training_keys(result):
    assert sorted(result.artifacts) == [
        "best_model",
        "best_model_json",
        "config",
        "data_quality_summary",
        "feature_spec",
        "manifest",
        "metrics",
        "metrics_linear",
        "metrics_ridge",
        "model_info",
        "model_info_linear",
        "model_info_ridge",
        "model_linear",
        "model_ridge",
        "preprocess_bundle",
    ]
    assert sorted(result.tables) == [
        "data_quality_warnings",
        "evaluation_predictions",
        "feature_importance",
        "leaderboard",
        "metrics_table_linear",
        "metrics_table_ridge",
        "missing_rate_by_column",
        "processed_train",
        "processed_valid",
        "validation_predictions_linear",
        "validation_predictions_ridge",
    ]
    assert sorted(result.plots) == [
        "best_feature_importance",
        "best_prediction_vs_actual",
        "best_residual_histogram",
        "best_residual_vs_predicted",
        "leaderboard_metric_panel",
        "missing_rate_by_column_bar",
    ]
    assert sorted(result.metrics) == ["mae", "r2", "rmse"]


def _assert_characterized_training_extra(result):
    assert result.extra["pipeline_kind"] == "training"
    assert result.extra["stages"] == ["preprocess_features", "train_linear", "train_ridge", "evaluate_models"]
    assert result.extra["candidate_models"] == ["linear", "ridge"]
    assert result.extra["selection_metric"] == "rmse"
    assert result.extra["ensemble"] == {"enabled": False}


def _assert_characterized_leaderboard(result):
    leaderboard = pd.read_csv(result.tables["leaderboard"])
    assert leaderboard.columns.tolist() == [
        "rank",
        "model_name",
        "artifact_kind",
        "ensemble_method",
        "stage",
        "selection_metric",
        "ref_kind",
        "infer_selector",
        "infer_target",
        "model_params",
        "artifact_name",
        "artifact_path",
        "rmse",
        "mae",
        "r2",
    ]
    assert leaderboard["model_name"].tolist() == ["linear", "ridge"]
    assert leaderboard["rank"].tolist() == [1, 2]
    assert set(leaderboard["artifact_kind"]) == {"model"}
    assert leaderboard["infer_target"].tolist() == ["linear", "ridge"]


def _assert_characterized_prediction_tables(result):
    evaluation_predictions = pd.read_csv(result.tables["evaluation_predictions"])
    assert evaluation_predictions.columns.tolist() == [
        "x1",
        "x2",
        "segment",
        "actual",
        "prediction",
        "residual",
        "abs_error",
        "model_name",
    ]
    assert set(evaluation_predictions["model_name"]) == {"linear"}


def _assert_characterized_decision_and_manifest(result):
    best_model = read_json(result.artifacts["best_model_json"])
    assert sorted(best_model) == [
        "artifact_kind",
        "candidate_selector",
        "code_version",
        "ensemble_method",
        "metrics",
        "model_name",
        "model_params",
        "model_selector",
        "recommended_inference_settings",
        "report_schema_version",
        "selection_metric",
        "selection_value",
        "source_task_id",
        "stage",
    ]
    assert best_model["report_schema_version"] == "leaderboard_dashboard_v2"
    assert best_model["model_selector"] == "best"
    assert best_model["recommended_inference_settings"] == {
        "Model/source_type": "task_id",
        "Model/source_task_id": "<training_or_evaluate_task_id>",
        "Model/model_selector": "best",
    }
    assert best_model["artifact_kind"] == "model"
    assert best_model["candidate_selector"] == "linear"

    manifest = read_json(result.artifacts["manifest"])
    assert manifest["extra"]["pipeline_kind"] == "training"
    assert sorted(manifest["artifacts"]) == sorted(key for key in result.artifacts if key != "manifest")
    assert sorted(manifest["tables"]) == sorted(result.tables)
    assert sorted(manifest["plots"]) == sorted(result.plots)


def test_tabular_inference_output_contract_before_module_split(tmp_path):
    training_result, infer_path = _run_characterized_training(tmp_path)
    cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(infer_path)
    cfg["data"]["id_columns"] = ["id"]
    cfg["model"]["source_type"] = "local_path"
    cfg["model"]["local_model_path"] = str(training_result.run_dir)
    cfg["model"]["model_selector"] = "best"

    result = run_infer(cfg)

    _assert_characterized_inference_keys(result)
    _assert_all_paths_exist(result.artifacts)
    _assert_all_paths_exist(result.tables)
    _assert_all_paths_exist(result.plots)
    _assert_characterized_inference_predictions(result)
    _assert_characterized_inference_schema_and_summary(result)
    _assert_characterized_inference_manifest(result)


def _assert_characterized_inference_keys(result):
    assert sorted(result.artifacts) == [
        "config",
        "manifest",
        "model_info",
        "schema_check_summary",
    ]
    assert sorted(result.tables) == [
        "prediction_preview",
        "prediction_summary",
        "predictions",
    ]
    assert sorted(result.plots) == ["prediction_distribution"]
    assert result.metrics == {}


def _assert_characterized_inference_predictions(result):
    predictions = pd.read_csv(result.tables["predictions"])
    assert predictions.columns.tolist() == [
        "row_index",
        "id",
        "prediction",
    ]
    assert predictions["row_index"].tolist() == [0, 1, 2, 3, 4]
    assert predictions["id"].tolist() == [0, 1, 2, 3, 4]
    assert "x1" not in predictions.columns
    assert "x2" not in predictions.columns
    assert "segment" not in predictions.columns


def _assert_characterized_inference_schema_and_summary(result):
    schema_check = read_json(result.artifacts["schema_check_summary"])
    assert schema_check["status"] == "ok"
    assert schema_check["missing_features"] == []
    assert schema_check["extra_columns"] == []
    assert schema_check["id_columns"] == ["id"]

    prediction_summary = pd.read_csv(result.tables["prediction_summary"])
    assert prediction_summary["metric"].tolist() == [
        "prediction_rows",
        "prediction_mean",
        "prediction_std",
        "prediction_min",
        "prediction_p25",
        "prediction_median",
        "prediction_p75",
        "prediction_max",
    ]
    assert int(prediction_summary.loc[prediction_summary["metric"] == "prediction_rows", "value"].iloc[0]) == 5


def _assert_characterized_inference_manifest(result):
    manifest = read_json(result.artifacts["manifest"])
    assert sorted(manifest["extra"]) == [
        "artifact_kind",
        "ensemble_method",
        "model_artifact_id",
        "model_name",
        "model_selector",
        "prediction_rows",
        "prediction_schema_version",
        "schema_check_status",
        "source_task_id",
        "source_type",
    ]
    assert manifest["extra"]["prediction_schema_version"] == "v3"
    assert manifest["extra"]["prediction_rows"] == 5
    assert manifest["extra"]["model_selector"] == "best"
    assert manifest["extra"]["schema_check_status"] == "ok"


class _FeatureImportanceTransformer:
    numeric_cols = ["x1"]
    categorical_cols = ["segment"]
    category_levels = {"segment": ["a", "b"]}
    passthrough_cols = ["raw"]


class _FeatureImportanceModel:
    coef_ = np.asarray([1.0, -0.5, 0.25, 0.75])


class _FeatureImportanceEstimator:
    transformer = _FeatureImportanceTransformer()
    model = _FeatureImportanceModel()


def test_tabular_plot_writer_contracts_before_module_split(tmp_path):
    rows = [
        {
            "rank": 1,
            "model_name": "linear",
            "artifact_kind": "model",
            "ensemble_method": None,
            "selection_metric": "rmse",
            "selection_value": 0.1,
            "rmse": 0.1,
            "mae": 0.08,
            "r2": 0.99,
        },
        {
            "rank": 2,
            "model_name": "ridge",
            "artifact_kind": "model",
            "ensemble_method": None,
            "selection_metric": "rmse",
            "selection_value": 0.2,
            "rmse": 0.2,
            "mae": 0.14,
            "r2": 0.96,
        },
    ]

    leaderboard_path = write_leaderboard_table(rows, tmp_path / "leaderboard.csv")
    metric_panel_path = write_leaderboard_metric_panel(rows, tmp_path / "leaderboard_metric_panel.png")
    feature_table_path, feature_plot_path = write_feature_importance_plot_if_available(
        _FeatureImportanceEstimator(),
        tmp_path,
    )

    predictions_path = tmp_path / "predictions.csv"
    pd.DataFrame({"actual": [1.0, 2.0, 3.0], "prediction": [1.1, 1.9, 3.2]}).to_csv(
        predictions_path,
        index=False,
    )
    prediction_tables, prediction_plots = write_prediction_summary_tables(
        predictions_path,
        tmp_path,
    )

    assert feature_table_path is not None
    assert feature_plot_path is not None
    for path in [
        leaderboard_path,
        metric_panel_path,
        feature_table_path,
        feature_plot_path,
        *prediction_tables.values(),
        *prediction_plots.values(),
    ]:
        assert path.exists()
        assert path.stat().st_size > 0

    assert pd.read_csv(leaderboard_path).columns.tolist() == [
        "rank",
        "model_name",
        "artifact_kind",
        "ensemble_method",
        "selection_metric",
        "selection_value",
        "rmse",
        "mae",
        "r2",
    ]
    feature_importance = pd.read_csv(feature_table_path)
    assert feature_importance.columns.tolist() == ["rank", "feature", "importance", "raw_value", "source"]
    assert feature_importance["feature"].tolist() == ["x1", "raw", "segment=a", "segment=b"]
    assert feature_importance["source"].tolist() == ["coef_"] * 4
    assert sorted(prediction_tables) == ["prediction_preview", "prediction_summary"]
    assert sorted(prediction_plots) == ["prediction_distribution"]
