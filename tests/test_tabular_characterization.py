from __future__ import annotations

import numpy as np
import pandas as pd

from ml_platform_core.config import load_run_config
from ml_platform_core.io import read_json
from ml_platform_tabular.infer import run_infer
from ml_platform_tabular.pipeline import run_pipeline
from ml_platform_tabular.plotting import (
    write_feature_importance_plot_if_available,
    write_leaderboard_metric_panel,
    write_leaderboard_pareto_plot,
    write_leaderboard_table,
    write_metrics_by_candidate_table,
    write_prediction_summary_tables,
)


def _write_characterization_data(tmp_path, *, rows: int = 36) -> tuple[pd.DataFrame, object, object]:
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


def _assert_all_paths_exist(paths: dict[str, object]) -> None:
    for key, path in paths.items():
        assert path.exists(), key


def test_tabular_pipeline_output_contract_before_module_split(tmp_path):
    result, _ = _run_characterized_training(tmp_path)

    assert sorted(result.artifacts) == [
        "best_model",
        "best_model_json",
        "candidate_predictions",
        "config",
        "data_quality_summary",
        "decision_summary",
        "decision_summary_json",
        "evaluation_predictions",
        "evaluation_report",
        "feature_spec",
        "feature_summary",
        "leaderboard",
        "manifest",
        "metrics",
        "metrics_by_candidate",
        "metrics_by_model",
        "metrics_linear",
        "metrics_ridge",
        "model_info_linear",
        "model_info_ridge",
        "model_linear",
        "model_refs",
        "model_ridge",
        "preprocess_bundle",
        "recommendation",
    ]
    assert sorted(result.tables) == [
        "best_vs_ensemble_summary",
        "candidate_predictions",
        "data_quality_summary_table",
        "data_quality_warnings",
        "evaluation_predictions",
        "evaluation_summary",
        "feature_importance_linear",
        "feature_importance_ridge",
        "feature_missingness",
        "feature_summary",
        "feature_summary_table",
        "feature_type_counts",
        "leaderboard",
        "leaderboard_decision_summary",
        "leaderboard_topk",
        "metrics_by_candidate",
        "metrics_table_linear",
        "metrics_table_ridge",
        "missing_rate_by_column",
        "processed_train",
        "processed_valid",
        "train_features",
        "valid_features",
        "validation_predictions_linear",
        "validation_predictions_ridge",
    ]
    assert sorted(result.plots) == [
        "best_prediction_vs_actual",
        "best_residual_histogram",
        "best_residual_vs_predicted",
        "feature_importance_bar_linear",
        "feature_importance_bar_ridge",
        "feature_importance_linear",
        "feature_importance_ridge",
        "feature_missingness_bar",
        "leaderboard_metric_panel",
        "leaderboard_pareto_rmse_r2",
        "leaderboard_topk_score_bar",
        "metrics_by_candidate_bar",
        "missing_rate_by_column_bar",
        "topk_prediction_vs_actual",
        "topk_residual_histogram",
        "topk_residual_vs_predicted",
        "validation_prediction_vs_actual_linear",
        "validation_prediction_vs_actual_ridge",
        "validation_residual_histogram_linear",
        "validation_residual_histogram_ridge",
        "validation_residual_vs_predicted_linear",
        "validation_residual_vs_predicted_ridge",
    ]
    assert sorted(result.metrics) == [
        "best_ensemble",
        "best_model",
        "candidate_count",
        "ensemble_count",
        "ensemble_enabled",
        "mae",
        "r2",
        "report_schema_version",
        "rmse",
        "selection_metric",
    ]
    _assert_all_paths_exist(result.artifacts)
    _assert_all_paths_exist(result.tables)
    _assert_all_paths_exist(result.plots)

    assert result.extra["pipeline_kind"] == "training"
    assert result.extra["stages"] == ["preprocess_features", "train_linear", "train_ridge", "evaluate_models"]
    assert result.extra["candidate_models"] == ["linear", "ridge"]
    assert result.extra["selection_metric"] == "rmse"
    assert result.extra["ensemble"] == {"enabled": False}

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

    candidate_predictions = pd.read_csv(result.tables["candidate_predictions"])
    assert candidate_predictions.columns.tolist() == [
        "candidate_rank",
        "candidate_name",
        "artifact_kind",
        "ensemble_method",
        "source_stage",
        "x1",
        "x2",
        "segment",
        "actual",
        "prediction",
        "residual",
        "abs_error",
        "model_name",
    ]
    assert set(candidate_predictions["candidate_name"]) == {"linear", "ridge"}
    assert set(candidate_predictions["artifact_kind"]) == {"model"}

    evaluation_summary = pd.read_csv(result.tables["evaluation_summary"])
    assert evaluation_summary["summary"].tolist() == ["best_overall", "best_single_model", "best_ensemble"]
    assert evaluation_summary["model_name"].iloc[:2].tolist() == ["linear", "linear"]
    assert pd.isna(evaluation_summary["model_name"].iloc[2])

    decision_summary = read_json(result.artifacts["decision_summary_json"])
    assert sorted(decision_summary) == [
        "best_artifact_kind",
        "best_ensemble",
        "best_ensemble_method",
        "best_metrics",
        "best_model_name",
        "best_single_model",
        "best_vs_ensemble_summary",
        "code_version",
        "created_at",
        "ensemble_improved_over_best_single",
        "leaderboard_top5",
        "recommendation",
        "recommended_candidate_selector",
        "recommended_inference_settings",
        "recommended_model_selector",
        "report_schema_version",
        "selection_metric",
        "source_task_id",
    ]
    assert decision_summary["report_schema_version"] == "leaderboard_dashboard_v2"
    assert decision_summary["recommended_model_selector"] == "best"
    assert decision_summary["recommended_inference_settings"] == {
        "Model/source_type": "task_id",
        "Model/source_task_id": "<training_or_evaluate_task_id>",
        "Model/model_selector": "best",
    }
    assert decision_summary["best_artifact_kind"] == "model"
    assert decision_summary["best_ensemble"] is None
    assert decision_summary["ensemble_improved_over_best_single"] is None

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

    assert sorted(result.artifacts) == [
        "config",
        "feature_spec",
        "manifest",
        "model_info",
        "preprocess_bundle",
        "schema_check_summary",
    ]
    assert sorted(result.tables) == [
        "prediction_preview",
        "prediction_summary",
        "predictions",
        "schema_check_summary",
        "source_summary",
    ]
    assert sorted(result.plots) == ["prediction_distribution", "prediction_distribution_histogram"]
    assert result.metrics == {}
    _assert_all_paths_exist(result.artifacts)
    _assert_all_paths_exist(result.tables)
    _assert_all_paths_exist(result.plots)

    predictions = pd.read_csv(result.tables["predictions"])
    assert predictions.columns.tolist() == [
        "row_index",
        "id",
        "prediction",
        "model_name",
        "artifact_kind",
        "model_artifact_id",
        "prediction_run_id",
    ]
    assert predictions["row_index"].tolist() == [0, 1, 2, 3, 4]
    assert predictions["id"].tolist() == [0, 1, 2, 3, 4]
    assert set(predictions["model_name"]) == {"linear"}
    assert set(predictions["artifact_kind"]) == {"model"}
    assert "x1" not in predictions.columns
    assert "x2" not in predictions.columns
    assert "segment" not in predictions.columns

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

    source_summary = pd.read_csv(result.tables["source_summary"])
    assert source_summary["field"].tolist() == [
        "source_type",
        "source_task_id",
        "model_selector",
        "resolved_model_name",
        "artifact_kind",
        "model_name",
        "ensemble_method",
        "target_column",
        "feature_preset",
        "schema_check_status",
        "resolved_model_path",
        "model_artifact_id",
        "feature_spec_path",
        "preprocess_bundle_path",
    ]

    manifest = read_json(result.artifacts["manifest"])
    assert sorted(manifest["extra"]) == [
        "artifact_kind",
        "chunk_size",
        "ensemble_method",
        "feature_columns",
        "feature_preset",
        "feature_spec_path",
        "id_columns",
        "local_model_path",
        "model_artifact_id",
        "model_info_path",
        "model_name",
        "model_selector",
        "model_source",
        "prediction_file",
        "prediction_rows",
        "prediction_schema_version",
        "prediction_summary",
        "preprocess_bundle_path",
        "resolved_model_path",
        "schema_check_status",
        "schema_check_summary",
        "source_task_id",
        "source_type",
        "target_column",
    ]
    assert manifest["extra"]["prediction_schema_version"] == "v2.3"
    assert manifest["extra"]["prediction_file"] == "predictions.csv"
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
    metrics_path = write_metrics_by_candidate_table(
        {
            "linear": {
                "artifact_kind": "model",
                "selection_metric": "rmse",
                "selection_value": 0.1,
                "metrics": rows[0],
            },
            "ridge": {"artifact_kind": "model", "selection_metric": "rmse", "selection_value": 0.2, "metrics": rows[1]},
        },
        tmp_path / "metrics_by_candidate.csv",
    )
    metric_panel_path = write_leaderboard_metric_panel(rows, tmp_path / "leaderboard_metric_panel.png")
    pareto_path = write_leaderboard_pareto_plot(rows, tmp_path / "leaderboard_pareto_rmse_r2.png")
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
        target_column="actual",
    )

    for path in [
        leaderboard_path,
        metrics_path,
        metric_panel_path,
        pareto_path,
        feature_table_path,
        feature_plot_path,
        *prediction_tables.values(),
        *prediction_plots.values(),
    ]:
        assert path is not None
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
    assert pd.read_csv(metrics_path).columns.tolist() == [
        "model_name",
        "artifact_kind",
        "ensemble_method",
        "selection_metric",
        "selection_value",
        "rank",
        "rmse",
        "mae",
        "r2",
    ]
    feature_importance = pd.read_csv(feature_table_path)
    assert feature_importance.columns.tolist() == ["rank", "feature", "importance", "raw_value", "source"]
    assert feature_importance["feature"].tolist() == ["x1", "raw", "segment=a", "segment=b"]
    assert feature_importance["source"].tolist() == ["coef_"] * 4
    assert sorted(prediction_tables) == ["prediction_preview", "prediction_summary"]
    assert sorted(prediction_plots) == [
        "prediction_distribution_histogram",
        "prediction_vs_actual",
        "residual_histogram",
        "residual_vs_predicted",
    ]
