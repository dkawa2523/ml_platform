import importlib.util
import json
from pathlib import Path

import pytest

from ml_platform_core.config import load_run_config
from ml_platform_core.result import RunResult


def load_module(path: str, name: str):
    module_path = Path(path).resolve()
    spec = importlib.util.spec_from_file_location(name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_clearml_adapter_module():
    return load_module("clearml/adapter.py", "ml_platform_clearml_adapter_test")


def load_clearml_templates_module():
    return load_module("clearml/templates.py", "ml_platform_clearml_templates_test")


def load_clearml_pipelines_module():
    return load_module("clearml/pipelines.py", "ml_platform_clearml_pipelines_test")


def load_clearml_app_module():
    return load_module("clearml/app.py", "ml_platform_clearml_app_test")


def load_clearml_reports_module():
    return load_module("clearml/reports.py", "ml_platform_clearml_reports_test")


def write_compat_pipeline_config(tmp_path: Path) -> Path:
    path = tmp_path / "compat_pipeline.yaml"
    path.write_text(
        "\n".join(
            [
                "# Deprecated compatibility config; not a product Pipeline-tab entrypoint.",
                "task: tabular_pipeline",
                "run:",
                "  name: tabular_pipeline",
                "  seed: 42",
                "  " + "pipeline" + "_mode: auto",
                "train:",
                "  task_config: config/tasks/tabular_train.yaml",
                "eval:",
                "  task_config: config/tasks/tabular_eval.yaml",
                "infer:",
                "  task_config: config/tasks/tabular_infer.yaml",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_clearml_mapping_shape():
    cfg = load_run_config("config/tasks/tabular_train.yaml", "config/profiles/clearml-dev.yaml")
    assert cfg["runtime"]["use_clearml"] is True
    assert cfg["task"] == "tabular_train"
    assert "clearml" in cfg
    assert cfg["clearml"]["project_root"] == "MLPlatform/Dev"
    assert cfg["clearml"]["projects"] == {
        "templates": "MLPlatform/Dev/Templates/Tabular",
        "pipelines": "MLPlatform/Dev/Pipelines/Tabular",
        "preprocess": "MLPlatform/Dev/Runs/Tabular/Preprocess",
        "train": "MLPlatform/Dev/Runs/Tabular/Train",
        "ensemble": "MLPlatform/Dev/Runs/Tabular/Ensemble",
        "evaluate": "MLPlatform/Dev/Runs/Tabular/Evaluate",
        "infer": "MLPlatform/Dev/Runs/Tabular/Infer",
        "stages": "MLPlatform/Dev/Runs/Tabular/Stages",
        "tasks": "MLPlatform/Dev/Runs/Tabular/Tasks",
        "experiments": "MLPlatform/Dev/Experiments/Tabular",
    }


def test_clearml_project_layout_prefers_explicit_projects():
    adapter = load_clearml_adapter_module()

    assert adapter.clearml_projects(
        {
            "project_root": "Root",
            "projects": {
                "templates": "Custom/Templates",
                "pipelines": "Custom/Pipelines",
            },
        }
    ) == {
        "templates": "Custom/Templates",
        "pipelines": "Custom/Pipelines",
        "preprocess": "Root/Runs/Tabular/Preprocess",
        "train": "Root/Runs/Tabular/Train",
        "ensemble": "Root/Runs/Tabular/Ensemble",
        "evaluate": "Root/Runs/Tabular/Evaluate",
        "infer": "Root/Runs/Tabular/Infer",
        "stages": "Root/Runs/Tabular/Stages",
        "tasks": "Root/Runs/Tabular/Tasks",
        "experiments": "Root/Experiments/Tabular",
    }
    assert adapter.clearml_projects(
        {
            "project_root": "Root",
            "projects": {
                "stages": "Legacy/Stages",
                "tasks": "Legacy/Tasks",
            },
        }
    )["train"] == "Legacy/Stages"
    assert adapter.clearml_projects(
        {
            "project_root": "Root",
            "projects": {
                "stages": "Legacy/Stages",
                "tasks": "Legacy/Tasks",
            },
        }
    )["infer"] == "Legacy/Tasks"


def test_clearml_app_routes_primary_tasks_to_named_projects():
    app = load_clearml_app_module()
    base_clearml = {
        "projects": {
            "templates": "Templates",
            "pipelines": "Pipelines",
            "preprocess": "Preprocess",
            "train": "Train",
            "ensemble": "Ensemble",
            "evaluate": "Evaluate",
            "infer": "Infer",
            "experiments": "Experiments",
        }
    }

    infer_project, infer_name, infer_tags, _ = app._initial_clearml_target(
        {"task": "tabular_infer", "run": {"name": "score_run"}, "clearml": base_clearml}
    )
    assert infer_project == "Infer"
    assert infer_name == "task/tabular_infer/score_run"
    assert infer_tags == ["domain:tabular", "run_type:task", "user_facing:true"]

    stage_project, stage_name, stage_tags, _ = app._initial_clearml_target(
        {
            "task": "tabular_stage",
            "run": {"name": "train_run", "stage": "train_model"},
            "model": {"name": "ridge"},
            "clearml": base_clearml,
        }
    )
    assert stage_project == "Train"
    assert stage_name == "stage/train_ridge/train_run"
    assert stage_tags == [
        "domain:tabular",
        "run_type:stage",
        "internal:true",
        "stage:train_model",
        "model:ridge",
    ]
    ensemble_project, ensemble_name, ensemble_tags, _ = app._initial_clearml_target(
        {
            "task": "tabular_stage",
            "run": {"name": "ensemble_run", "stage": "build_ensemble"},
            "model": {"ensemble": {"methods": ["weighted"]}},
            "clearml": base_clearml,
        }
    )
    assert ensemble_project == "Ensemble"
    assert ensemble_name == "stage/build_ensemble_weighted/ensemble_run"
    assert ensemble_tags == [
        "domain:tabular",
        "run_type:stage",
        "internal:true",
        "stage:build_ensemble",
        "ensemble:weighted",
    ]


def test_clearml_ui_params_are_applied_to_nested_config():
    adapter = load_clearml_adapter_module()
    cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/clearml-dev.yaml")
    connected = {
        "Input/local_path": "data/other.csv",
        "Input/dataset_file": "train.csv",
        "Input/target_column": "y",
        "Run/seed": 7,
        "Model/source_type": "task_id",
        "Model/source_task_id": "train-task-id",
        "Model/model_selector": "best",
        "Model/model_artifact_url": "s3://bucket/model.joblib",
        "Model/clearml_model_id": "model-id",
        "Model/local_model_path": "outputs/latest_training_pipeline",
        "Model/artifact_path": "outputs/latest_train/model.joblib",
        "Model/info_path": "outputs/latest_train/model_info.json",
        "Output/prediction_name": "scored.csv",
        "Output/chunk_size": 500,
    }
    updated = adapter.apply_ui_params(cfg, connected)
    assert updated["data"]["local_path"] == "data/other.csv"
    assert updated["data"]["dataset_file"] == "train.csv"
    assert updated["data"]["target_column"] == "y"
    assert updated["run"]["seed"] == 7
    assert updated["model"]["source_type"] == "task_id"
    assert updated["model"]["source_task_id"] == "train-task-id"
    assert updated["model"]["model_selector"] == "best"
    assert updated["model"]["model_artifact_url"] == "s3://bucket/model.joblib"
    assert updated["model"]["clearml_model_id"] == "model-id"
    assert updated["model"]["local_model_path"] == "outputs/latest_training_pipeline"
    assert updated["model"]["artifact_path"] == "outputs/latest_train/model.joblib"
    assert updated["model"]["info_path"] == "outputs/latest_train/model_info.json"
    assert updated["output"]["prediction_name"] == "scored.csv"
    assert updated["output"]["chunk_size"] == 500


def test_clearml_compat_train_ui_params_include_feature_group():
    adapter = load_clearml_adapter_module()
    cfg = load_run_config("config/tasks/tabular_train.yaml", "config/profiles/clearml-dev.yaml")
    params = adapter.default_ui_params(cfg)

    assert "Input/dataset_file" in params
    assert params["Model/params"] == '{"alpha": 1.0}'
    assert params["Model/candidates"] == "[]"
    assert params["Model/selection_metric"] == "rmse"
    assert params["Model/ensemble_enabled"] is False
    assert params["Model/ensemble_method"] == "mean_topk"
    assert params["Model/ensemble_top_k"] == 3
    assert params["Features/preset"] == "basic"
    assert {key.split("/", 1)[0] for key in params} <= {"Input", "Run", "Split", "Model", "Features", "Output"}
    assert not [key for key in params if key.startswith("Output/")]


def test_clearml_flat_ensemble_params_apply_to_nested_config():
    adapter = load_clearml_adapter_module()
    cfg = load_run_config("config/tasks/tabular_train.yaml", "config/profiles/clearml-dev.yaml")

    updated = adapter.apply_ui_params(
        cfg,
        {
            "Model/ensemble_enabled": True,
            "Model/ensemble_methods": '["mean_topk","weighted","median"]',
            "Model/ensemble_method": "weighted",
            "Model/ensemble_top_k": 2,
        },
    )

    assert updated["model"]["ensemble"] == {
        "enabled": True,
        "methods": ["mean_topk", "weighted", "median"],
        "method": "weighted",
        "top_k": 2,
    }


def test_clearml_default_ui_params_cover_primary_and_compat_tasks():
    adapter = load_clearml_adapter_module()
    train = adapter.default_ui_params(load_run_config("config/tasks/tabular_train.yaml", "config/profiles/clearml-dev.yaml"))
    eval_cfg = adapter.default_ui_params(load_run_config("config/tasks/tabular_eval.yaml", "config/profiles/clearml-dev.yaml"))
    infer = adapter.default_ui_params(load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/clearml-dev.yaml"))
    pipeline = adapter.default_ui_params(load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml"))
    stage = adapter.default_ui_params(load_run_config("config/tasks/tabular_stage.yaml", "config/profiles/clearml-dev.yaml"))

    assert {
        "Model/name",
        "Model/params",
        "Model/candidates",
        "Model/selection_metric",
        "Model/ensemble_enabled",
        "Model/ensemble_method",
        "Model/ensemble_top_k",
        "Features/preset",
    }.issubset(train)
    assert "Model/name" not in eval_cfg
    assert "Model/params" not in eval_cfg
    assert "Output/prediction_name" in infer
    assert "Output/chunk_size" in infer
    assert {
        "Model/source_type",
        "Model/source_task_id",
        "Model/model_selector",
        "Model/local_model_path",
    }.issubset(infer)
    assert "Model/model_artifact_url" not in infer
    assert "Model/clearml_model_id" not in infer
    assert "Model/artifact_path" not in infer
    assert "Model/info_path" not in infer
    assert {
        "Run/task",
        "Run/name",
        "Run/seed",
        "Input/local_path",
        "Input/target_column",
        "Split/valid_size",
        "Features/preset",
        "Features/numeric_impute_strategy",
        "Features/categorical_impute_strategy",
        "Features/categorical_encoder",
        "Features/scaling",
        "Features/drop_columns",
        "Features/passthrough_columns",
        "Model/candidates",
        "Model/params",
        "Model/evaluation_metrics",
        "Model/ensemble_enabled",
        "Model/ensemble_methods",
        "Model/ensemble_method",
        "Model/ensemble_top_k",
        "Output/report_plots",
    }.issubset(pipeline)
    # default_ui_params is still used for compatibility/internal task surfaces.
    # The user-facing Pipeline New Run surface is asserted separately below.
    assert "Model/search_enabled" not in pipeline
    assert "Model/search_method" not in pipeline
    assert "Model/search_space" not in pipeline
    assert "Model/max_trials" not in pipeline
    assert "Output/prediction_name" not in pipeline
    assert "Run/stage" in stage
    assert "Input/preprocess_bundle" in stage
    assert "Input/model_refs" in stage


def test_clearml_pipeline_template_has_minimal_training_pipeline_overrides():
    pipelines = load_clearml_pipelines_module()
    params = pipelines.pipeline_ui_params("config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml")

    assert {key.split("/", 1)[0] for key in params} <= {"Input", "Run", "Split", "Features", "Model", "Output"}
    assert {
        "Run/name",
        "Split/valid_size",
        "Input/clearml_dataset_id",
        "Input/local_path",
        "Input/dataset_file",
        "Input/target_column",
        "Input/id_columns",
    }.issubset(params)
    assert {
        "Features/preset",
        "Features/numeric_impute_strategy",
        "Features/categorical_impute_strategy",
        "Features/categorical_encoder",
        "Features/scaling",
        "Features/drop_columns",
        "Features/passthrough_columns",
    }.issubset(params)
    assert {
        "Model/model_params_by_name",
        "Model/evaluation_metrics",
        "Model/candidates",
        "Model/selection_metric",
        "Model/ensemble_enabled",
        "Model/ensemble_methods",
        "Model/ensemble_top_k",
    }.issubset(params)
    assert "Run/task" not in params
    assert "Model/params" not in params
    assert "Model/ensemble_method" not in params
    assert "Model/feature_preset" not in params
    assert "Model/search_enabled" not in params
    assert "Model/search_method" not in params
    assert "Model/search_space" not in params
    assert "Model/max_trials" not in params
    assert "Run/" + "pipeline" + "_mode" not in params
    assert "Output/report_plots" in params
    assert params["Output/report_plots"] is True
    assert params["Input/local_path"] == ""
    assert params["Input/clearml_dataset_id"] == "b7afaea9d7aa42f084fb4fc06b0d4d41"
    assert params["Input/dataset_file"] == "sample_train.csv"
    assert params["Input/feature_columns"] == []
    assert params["Model/evaluation_metrics"] == '["mae", "rmse", "r2"]'
    assert params["Features/preset"] == "basic"
    assert params["Features/drop_columns"] == "[]"
    assert params["Model/ensemble_methods"] == '["mean_topk", "weighted", "median"]'
    assert json.loads(params["Model/candidates"]) == [
        "linear",
        "ridge",
        "lasso",
        "elasticnet",
        "random_forest",
        "extra_trees",
        "gradient_boosting",
        "lightgbm",
        "xgboost",
        "catboost",
    ]
    assert set(json.loads(params["Model/model_params_by_name"])) == {
        "linear",
        "ridge",
        "lasso",
        "elasticnet",
        "random_forest",
        "extra_trees",
        "gradient_boosting",
        "lightgbm",
        "xgboost",
        "catboost",
    }


def test_clearml_pipeline_new_run_args_are_mapped_to_ui_params():
    pipelines = load_clearml_pipelines_module()
    defaults = pipelines.pipeline_ui_params("config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml")
    task_params = {
        "Model/candidates": '["linear"]',
        "Args/Model/candidates": '["linear","ridge"]',
        "Args/Input/clearml_dataset_id": "dataset-id",
    }

    args_params = pipelines.pipeline_arg_params(defaults)
    connected = pipelines.pipeline_params_from_task(defaults, task_params)

    assert args_params["Args/Model/candidates"] == defaults["Model/candidates"]
    assert connected["Model/candidates"] == '["linear","ridge"]'
    assert connected["Input/clearml_dataset_id"] == "dataset-id"


def test_clearml_pipeline_params_map_model_metrics_and_output_options():
    adapter = load_clearml_adapter_module()
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml")

    updated = adapter.apply_ui_params(
        cfg,
        {
            "Model/model_params_by_name": '{"ridge":{"alpha":2.0}}',
            "Model/evaluation_metrics": '["mae","rmse"]',
            "Features/preset": "numeric_only",
            "Features/numeric_impute_strategy": "mean",
            "Features/categorical_encoder": "drop",
            "Features/drop_columns": '["unused"]',
            "Features/passthrough_columns": '["x1"]',
            "Split/valid_size": 0.25,
            "Output/report_plots": False,
        },
    )

    assert updated["model"]["params"] == {"ridge": {"alpha": 2.0}}
    assert updated["metrics"]["names"] == ["mae", "rmse"]
    assert updated["split"]["valid_size"] == 0.25
    assert updated["features"]["preset"] == "numeric_only"
    assert updated["features"]["numeric_impute_strategy"] == "mean"
    assert updated["features"]["categorical_encoder"] == "drop"
    assert updated["features"]["drop_columns"] == ["unused"]
    assert updated["features"]["passthrough_columns"] == ["x1"]
    assert updated["output"]["report_plots"] is False


def test_clearml_report_plots_false_skips_media_but_uploads_plot_artifact(tmp_path):
    reports = load_clearml_reports_module()
    plot = tmp_path / "plot.svg"
    plot.write_text("<svg />", encoding="utf-8")

    class FakeAdapter:
        def __init__(self):
            self.uploads = []
            self.media = []
            self.plots = []
            self.scalars = []
            self.tables = []

        def report_scalar(self, title, series, value, iteration=0):
            self.scalars.append((title, series, value, iteration))

        def upload_artifact(self, name, path):
            self.uploads.append((name, path))

        def report_table(self, title, series, path, iteration=0):
            self.tables.append((title, series, path, iteration))

        def report_media(self, title, series, path, iteration=0):
            self.media.append((title, series, path, iteration))

        def report_scatter(self, title, series, points, iteration=0):
            self.plots.append(("scatter", title, series, points, iteration))

        def report_histogram(self, title, series, values, iteration=0):
            self.plots.append(("histogram", title, series, values, iteration))

    adapter = FakeAdapter()
    result = RunResult(run_dir=tmp_path, metrics={"rmse": 1.0}, plots={"prediction_vs_actual": plot})

    reports.report_result(adapter, result, report_plots=False)

    assert ("metrics", "rmse", 1.0, 0) in adapter.scalars
    assert ("prediction_vs_actual", plot) in adapter.uploads
    assert adapter.media == []
    assert adapter.plots == []


def test_clearml_adapter_reports_prediction_scatter_as_markers():
    adapter_module = load_clearml_adapter_module()

    class FakeLogger:
        def __init__(self):
            self.scatter_calls = []

        def report_scatter2d(self, **kwargs):
            self.scatter_calls.append(kwargs)

    class FakeTask:
        def __init__(self):
            self.logger = FakeLogger()

        def get_logger(self):
            return self.logger

    task = FakeTask()
    adapter_module.ClearMLAdapter(task).report_scatter(
        "prediction_vs_actual",
        "validation_predictions",
        [(1.0, 0.9), (2.0, 2.1)],
        iteration=0,
    )

    assert task.logger.scatter_calls == [
        {
            "title": "prediction_vs_actual",
            "series": "validation_predictions",
            "scatter": [(1.0, 0.9), (2.0, 2.1)],
            "iteration": 0,
            "xaxis": "actual",
            "yaxis": "prediction",
            "mode": "markers",
        }
    ]


def test_clearml_adapter_reports_plotly_and_axis_named_histogram():
    adapter_module = load_clearml_adapter_module()

    class FakeLogger:
        def __init__(self):
            self.plotly_calls = []
            self.histogram_calls = []

        def report_plotly(self, **kwargs):
            self.plotly_calls.append(kwargs)

        def report_histogram(self, **kwargs):
            self.histogram_calls.append(kwargs)

    class FakeTask:
        def __init__(self):
            self.logger = FakeLogger()

        def get_logger(self):
            return self.logger

    task = FakeTask()
    adapter = adapter_module.ClearMLAdapter(task)
    adapter.report_plotly(
        "prediction_vs_actual",
        "validation_predictions",
        {"data": [{"type": "scatter"}], "layout": {"xaxis": {"title": "actual"}}},
        iteration=2,
    )
    adapter.report_histogram(
        "residual_histogram",
        "validation_predictions",
        [0.1, -0.2],
        iteration=3,
        xaxis="residual (actual - prediction)",
        yaxis="count",
    )

    assert task.logger.plotly_calls == [
        {
            "title": "prediction_vs_actual",
            "series": "validation_predictions",
            "figure": {"data": [{"type": "scatter"}], "layout": {"xaxis": {"title": "actual"}}},
            "iteration": 2,
        }
    ]
    assert task.logger.histogram_calls == [
        {
            "title": "residual_histogram",
            "series": "validation_predictions",
            "values": [0.1, -0.2],
            "iteration": 3,
            "xaxis": "residual (actual - prediction)",
            "yaxis": "count",
        }
    ]


def test_clearml_report_result_expands_model_metrics_and_tables(tmp_path):
    reports = load_clearml_reports_module()
    metrics = tmp_path / "metrics.json"
    metrics.write_text(
        json.dumps(
            {
                "rmse": 0.25,
                "mae": 0.18,
                "r2": 0.92,
                "best_model": {"model_name": "mean_topk", "metrics": {"rmse": 0.25, "mae": 0.18, "r2": 0.92}},
            }
        ),
        encoding="utf-8",
    )
    metrics_by_model = tmp_path / "metrics_by_model.json"
    metrics_by_model.write_text(
        json.dumps(
            {
                "metrics_by_model": {
                    "ridge": {
                        "artifact_kind": "model",
                        "metrics": {"rmse": 0.3, "mae": 0.2, "r2": 0.9},
                    },
                    "mean_topk": {
                        "artifact_kind": "ensemble",
                        "metrics": {"rmse": 0.25, "mae": 0.18, "r2": 0.92},
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    metrics_by_candidate = tmp_path / "metrics_by_candidate.json"
    metrics_by_candidate.write_text(
        json.dumps(
            {
                "metrics_by_candidate": {
                    "ridge": {
                        "artifact_kind": "model",
                        "metrics": {"rmse": 0.3, "mae": 0.2, "r2": 0.9},
                    },
                    "weighted": {
                        "artifact_kind": "ensemble",
                        "ensemble_method": "weighted",
                        "metrics": {"rmse": 0.24, "mae": 0.17, "r2": 0.93},
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    feature_summary = tmp_path / "feature_summary.json"
    feature_summary.write_text(
        json.dumps(
            {
                "input_rows": 100,
                "train_rows": 80,
                "valid_rows": 20,
                "feature_count": 4,
                "numeric_feature_count": 3,
                "categorical_feature_count": 1,
                "passthrough_feature_count": 0,
                "dropped_feature_count": 0,
                "transformed_feature_count": 5,
            }
        ),
        encoding="utf-8",
    )
    leaderboard = tmp_path / "leaderboard.csv"
    leaderboard.write_text(
        "rank,model_name,artifact_kind,ensemble_method,selection_metric,rmse,mae,r2,infer_target,ref_kind\n"
        "1,mean_topk,ensemble,mean_topk,rmse,0.25,0.18,0.92,ensemble:mean_topk,task_artifact\n"
        "2,ridge,model,,rmse,0.3,0.2,0.9,ridge,task_artifact\n",
        encoding="utf-8",
    )
    leaderboard_topk = tmp_path / "leaderboard_topk.csv"
    leaderboard_topk.write_text(
        "rank,model_name,artifact_kind,ensemble_method,selection_metric,rmse,mae,r2,infer_target,ref_kind\n"
        "1,mean_topk,ensemble,mean_topk,rmse,0.25,0.18,0.92,ensemble:mean_topk,task_artifact\n",
        encoding="utf-8",
    )
    feature_summary_table = tmp_path / "feature_summary_table.csv"
    feature_summary_table.write_text("metric,value\ninput_rows,100\n", encoding="utf-8")
    missing_rate_by_column = tmp_path / "missing_rate_by_column.csv"
    missing_rate_by_column.write_text("column,role,missing_count,missing_rate\nx,numeric,0,0.0\n", encoding="utf-8")
    feature_type_counts = tmp_path / "feature_type_counts.csv"
    feature_type_counts.write_text("feature_type,count\nnumeric,1\n", encoding="utf-8")
    feature_missingness = tmp_path / "missing_rate_by_column_alias.csv"
    feature_missingness.write_text("column,role,missing_count,missing_rate\nx,numeric,0,0.0\n", encoding="utf-8")
    feature_importance = tmp_path / "feature_importance_linear.csv"
    feature_importance.write_text("rank,feature,importance,raw_value,source\n1,x,0.5,0.5,coef_\n", encoding="utf-8")
    metrics_table = tmp_path / "metrics_table.csv"
    metrics_table.write_text("metric,value\nrmse,0.25\nmae,0.18\nr2,0.92\n", encoding="utf-8")
    evaluation_summary = tmp_path / "evaluation_summary.csv"
    evaluation_summary.write_text("summary,model_name,rmse\nbest_overall,ridge,0.3\n", encoding="utf-8")
    leaderboard_decision_summary = tmp_path / "leaderboard_decision_summary.csv"
    leaderboard_decision_summary.write_text(
        "summary,model_name,artifact_kind,ensemble_method,rmse,model_selector\n"
        "best_overall,ridge,model,,0.3,ridge\n"
        "best_single_model,ridge,model,,0.3,ridge\n"
        "best_ensemble,weighted,ensemble,weighted,0.24,ensemble:weighted\n",
        encoding="utf-8",
    )
    best_vs_ensemble_summary = tmp_path / "best_vs_ensemble_summary.csv"
    best_vs_ensemble_summary.write_text(
        "metric,best_single_model,best_single_value,best_ensemble_method,best_ensemble_value,ensemble_minus_single,ensemble_improved\n"
        "rmse,ridge,0.3,weighted,0.24,-0.06,true\n",
        encoding="utf-8",
    )
    validation_predictions = tmp_path / "validation_predictions.csv"
    validation_predictions.write_text("actual,prediction,residual,abs_error\n1,0.9,0.1,0.1\n", encoding="utf-8")
    aggregate_validation_predictions = tmp_path / "validation_predictions_linear.csv"
    aggregate_validation_predictions.write_text("actual,prediction,residual,abs_error\n1,0.9,0.1,0.1\n", encoding="utf-8")
    evaluation_predictions = tmp_path / "evaluation_predictions.csv"
    evaluation_predictions.write_text("actual,prediction,residual,abs_error\n1,1.1,-0.1,0.1\n", encoding="utf-8")
    predictions = tmp_path / "predictions.csv"
    predictions.write_text("prediction\n1.1\n", encoding="utf-8")
    prediction_summary = tmp_path / "prediction_summary.csv"
    prediction_summary.write_text("metric,value\nprediction_rows,1\n", encoding="utf-8")
    prediction_preview = tmp_path / "prediction_preview.csv"
    prediction_preview.write_text("prediction\n1.1\n", encoding="utf-8")
    source_summary = tmp_path / "source_summary.csv"
    source_summary.write_text("field,value\nmodel_selector,best\nartifact_kind,model\n", encoding="utf-8")
    ensemble_predictions = tmp_path / "ensemble_predictions_weighted.csv"
    ensemble_predictions.write_text("actual,prediction,residual,abs_error\n1,1.05,-0.05,0.05\n", encoding="utf-8")
    ensemble_predictions_alias = tmp_path / "ensemble_predictions.csv"
    ensemble_predictions_alias.write_text(
        "actual,prediction,residual,abs_error\n1,1.05,-0.05,0.05\n",
        encoding="utf-8",
    )
    candidate_predictions = tmp_path / "candidate_predictions.csv"
    candidate_predictions.write_text(
        "candidate_rank,candidate_name,artifact_kind,ensemble_method,actual,prediction,residual,abs_error\n"
        "1,ridge,model,,1,0.9,0.1,0.1\n"
        "2,weighted,ensemble,weighted,1,1.05,-0.05,0.05\n"
        "3,median,ensemble,median,1,1.02,-0.02,0.02\n"
        "4,linear,model,,1,0.8,0.2,0.2\n"
        "5,lasso,model,,1,0.85,0.15,0.15\n"
        "6,elasticnet,model,,1,0.75,0.25,0.25\n",
        encoding="utf-8",
    )
    ensemble_metrics_table = tmp_path / "ensemble_metrics_table.csv"
    ensemble_metrics_table.write_text("ensemble_method,rmse,mae,r2\nweighted,0.24,0.17,0.93\n", encoding="utf-8")
    ensemble_members = tmp_path / "ensemble_members_weighted.csv"
    ensemble_members.write_text("rank,model_name,weight\n1,ridge,1.0\n", encoding="utf-8")
    ensemble_weights = tmp_path / "ensemble_weights_weighted.csv"
    ensemble_weights.write_text("rank,model_name,weight\n1,ridge,1.0\n", encoding="utf-8")
    plot = tmp_path / "metrics_by_candidate_bar.png"
    plot.write_bytes(b"\x89PNG\r\n\x1a\n")

    class FakeAdapter:
        def __init__(self):
            self.uploads = []
            self.images = []
            self.media = []
            self.plots = []
            self.scalars = []
            self.tables = []

        def report_scalar(self, title, series, value, iteration=0):
            self.scalars.append((title, series, value, iteration))

        def upload_artifact(self, name, path):
            self.uploads.append((name, path))

        def report_table(self, title, series, path, iteration=0):
            self.tables.append((title, series, path, iteration))

        def report_image(self, title, series, path, iteration=0):
            self.images.append((title, series, path, iteration))

        def report_media(self, title, series, path, iteration=0):
            self.media.append((title, series, path, iteration))

        def report_plotly(self, title, series, figure, iteration=0):
            self.plots.append(("plotly", title, series, figure, iteration))

        def report_scatter(self, title, series, points, iteration=0):
            self.plots.append(("scatter", title, series, points, iteration))

        def report_histogram(self, title, series, values, iteration=0, **kwargs):
            self.plots.append(("histogram", title, series, values, iteration, kwargs))

    adapter = FakeAdapter()
    result = RunResult(
        run_dir=tmp_path,
        metrics={
            "rmse": 0.25,
            "best_model": {"model_name": "mean_topk", "metrics": {"rmse": 0.25, "mae": 0.18, "r2": 0.92}},
        },
        artifacts={
            "metrics": metrics,
            "feature_summary": feature_summary,
            "metrics_by_model": metrics_by_model,
            "metrics_by_candidate": metrics_by_candidate,
        },
        tables={
            "leaderboard": leaderboard,
            "leaderboard_topk": leaderboard_topk,
            "feature_summary_table": feature_summary_table,
            "feature_summary": feature_summary_table,
            "missing_rate_by_column": missing_rate_by_column,
            "feature_type_counts": feature_type_counts,
            "feature_missingness": feature_missingness,
            "feature_importance_linear": feature_importance,
            "metrics_table": metrics_table,
            "evaluation_summary": evaluation_summary,
            "leaderboard_decision_summary": leaderboard_decision_summary,
            "best_vs_ensemble_summary": best_vs_ensemble_summary,
            "validation_predictions": validation_predictions,
            "validation_predictions_linear": aggregate_validation_predictions,
            "evaluation_predictions": evaluation_predictions,
            "predictions": predictions,
            "prediction_summary": prediction_summary,
            "prediction_preview": prediction_preview,
            "source_summary": source_summary,
            "ensemble_metrics_table": ensemble_metrics_table,
            "ensemble_predictions": ensemble_predictions_alias,
            "ensemble_predictions_weighted": ensemble_predictions,
            "candidate_predictions": candidate_predictions,
            "ensemble_members_weighted": ensemble_members,
            "ensemble_weights_weighted": ensemble_weights,
        },
        plots={"metrics_by_candidate_bar": plot},
    )

    reports.report_result(adapter, result)

    assert ("metrics_by_model/rmse", "ridge", 0.3, 0) in adapter.scalars
    assert ("metrics_by_model/mae", "mean_topk", 0.18, 0) in adapter.scalars
    assert ("ensemble/rmse", "mean_topk", 0.25, 0) in adapter.scalars
    assert ("metrics_by_candidate/rmse", "ridge", 0.3, 0) in adapter.scalars
    assert ("metrics_by_candidate/mae", "weighted", 0.17, 0) in adapter.scalars
    assert ("ensemble/rmse", "weighted", 0.24, 0) in adapter.scalars
    assert ("best_model/r2", "mean_topk", 0.92, 0) in adapter.scalars
    assert ("best_model", "r2", 0.92, 0) in adapter.scalars
    assert ("features", "input_rows", 100.0, 0) in adapter.scalars
    assert ("features", "transformed_feature_count", 5.0, 0) in adapter.scalars
    assert ("metrics", "mae", 0.18, 0) in adapter.scalars
    assert ("metrics", "rmse", 0.25, 0) in adapter.scalars
    assert ("tables", "leaderboard_table", leaderboard, 0) in adapter.tables
    assert ("tables", "leaderboard_topk_table", leaderboard_topk, 0) in adapter.tables
    assert ("tables", "feature_summary_table", feature_summary_table, 0) in adapter.tables
    assert ("tables", "missing_rate_by_column", missing_rate_by_column, 0) in adapter.tables
    assert ("tables", "feature_type_counts", feature_type_counts, 0) in adapter.tables
    assert ("tables", "feature_importance_linear", feature_importance, 0) in adapter.tables
    assert ("tables", "metrics_table", metrics_table, 0) in adapter.tables
    assert ("tables", "evaluation_summary_table", evaluation_summary, 0) in adapter.tables
    assert ("tables", "leaderboard_decision_summary_table", leaderboard_decision_summary, 0) in adapter.tables
    assert ("tables", "best_vs_ensemble_summary_table", best_vs_ensemble_summary, 0) in adapter.tables
    assert ("tables", "validation_predictions", validation_predictions, 0) in adapter.tables
    assert ("tables", "evaluation_predictions", evaluation_predictions, 0) in adapter.tables
    assert ("tables", "predictions_table", predictions, 0) in adapter.tables
    assert ("tables", "prediction_summary_table", prediction_summary, 0) in adapter.tables
    assert ("tables", "prediction_preview_table", prediction_preview, 0) in adapter.tables
    assert ("tables", "source_summary_table", source_summary, 0) in adapter.tables
    assert ("tables", "ensemble_metrics_table", ensemble_metrics_table, 0) in adapter.tables
    assert ("tables", "ensemble_predictions_weighted", ensemble_predictions, 0) in adapter.tables
    assert ("tables", "candidate_predictions_table", candidate_predictions, 0) in adapter.tables
    assert ("tables", "ensemble_members_weighted", ensemble_members, 0) in adapter.tables
    assert ("tables", "ensemble_weights_weighted", ensemble_weights, 0) in adapter.tables
    assert ("tables", "feature_summary", feature_summary_table, 0) not in adapter.tables
    assert ("tables", "feature_missingness", feature_missingness, 0) not in adapter.tables
    assert ("tables", "ensemble_predictions", ensemble_predictions_alias, 0) not in adapter.tables
    assert ("tables", "validation_predictions_linear", aggregate_validation_predictions, 0) not in adapter.tables
    assert any(item[:3] == ("plotly", "prediction_vs_actual", "validation_predictions") for item in adapter.plots)
    assert any(item[:3] == ("plotly", "residual_histogram", "validation_predictions") for item in adapter.plots)
    assert any(item[:3] == ("plotly", "residual_vs_predicted", "validation_predictions") for item in adapter.plots)
    assert any(item[:3] == ("plotly", "leaderboard", "best_prediction_vs_actual") for item in adapter.plots)
    assert any(item[:3] == ("plotly", "leaderboard", "best_residual_histogram") for item in adapter.plots)
    assert any(item[:3] == ("plotly", "leaderboard", "best_residual_vs_predicted") for item in adapter.plots)
    assert any(item[:3] == ("plotly", "prediction_vs_actual", "ensemble_predictions_weighted") for item in adapter.plots)
    assert not any(item[:3] == ("plotly", "prediction_vs_actual", "ensemble_predictions") for item in adapter.plots)
    assert any(item[:3] == ("plotly", "leaderboard", "table") for item in adapter.plots)
    assert any(item[:3] == ("plotly", "leaderboard", "top_k_scores") for item in adapter.plots)
    assert any(item[:3] == ("plotly", "leaderboard", "metric_panel") for item in adapter.plots)
    assert any(item[:3] == ("plotly", "leaderboard", "pareto_rmse_r2") for item in adapter.plots)
    assert any(item[:3] == ("plotly", "leaderboard", "topk_prediction_vs_actual") for item in adapter.plots)
    assert any(item[:3] == ("plotly", "leaderboard", "topk_residual_histogram") for item in adapter.plots)
    assert any(item[:3] == ("plotly", "prediction_distribution_histogram", "predictions") for item in adapter.plots)
    prediction_fig = next(item[3] for item in adapter.plots if item[:3] == ("plotly", "prediction_vs_actual", "validation_predictions"))
    assert any(trace.get("name") == "y=x" for trace in prediction_fig["data"])
    assert prediction_fig["layout"]["xaxis"]["title"] == "actual"
    assert prediction_fig["layout"]["yaxis"]["title"] == "prediction"
    topk_fig = next(item[3] for item in adapter.plots if item[:3] == ("plotly", "leaderboard", "topk_prediction_vs_actual"))
    candidate_traces = [trace for trace in topk_fig["data"] if trace.get("name") != "y=x"]
    assert len(candidate_traces) <= 5
    assert all("rank " in trace.get("name", "") for trace in candidate_traces)
    leaderboard_table = next(item[3] for item in adapter.plots if item[:3] == ("plotly", "leaderboard", "table"))
    assert leaderboard_table["data"][0]["type"] == "table"
    top_scores = next(item[3] for item in adapter.plots if item[:3] == ("plotly", "leaderboard", "top_k_scores"))
    assert top_scores["data"][0]["type"] == "bar"
    metric_panel = next(item[3] for item in adapter.plots if item[:3] == ("plotly", "leaderboard", "metric_panel"))
    assert {trace["name"] for trace in metric_panel["data"]} == {"rmse", "mae", "r2"}
    pareto = next(item[3] for item in adapter.plots if item[:3] == ("plotly", "leaderboard", "pareto_rmse_r2"))
    assert pareto["layout"]["xaxis"]["title"] == "r2"
    assert pareto["layout"]["yaxis"]["title"] == "rmse"
    assert ("plots", "metrics_by_candidate_bar", plot, 0) in adapter.images
    assert adapter.media == []


def test_clearml_report_result_falls_back_to_media_when_image_api_is_unavailable(tmp_path):
    reports = load_clearml_reports_module()
    plot = tmp_path / "plot.png"
    plot.write_bytes(b"\x89PNG\r\n\x1a\n")

    class FakeAdapter:
        def __init__(self):
            self.uploads = []
            self.media = []

        def upload_artifact(self, name, path):
            self.uploads.append((name, path))

        def report_scalar(self, title, series, value, iteration=0):
            pass

        def report_media(self, title, series, path, iteration=0):
            self.media.append((title, series, path, iteration))

    adapter = FakeAdapter()
    reports.report_result(adapter, RunResult(run_dir=tmp_path, plots={"plot": plot}))

    assert ("plot", plot) in adapter.uploads
    assert ("plots", "plot", plot, 0) in adapter.media


def test_clearml_connect_params_uses_named_groups():
    adapter = load_clearml_adapter_module()

    class FakeTask:
        def __init__(self):
            self.calls = []

        def connect(self, values, name=None):
            self.calls.append((name, dict(values)))
            return values

    task = FakeTask()
    connected = adapter.ClearMLAdapter(task).connect_params(
        {
            "Run/task": "tabular_train",
            "Input/local_path": "data/sample_train.csv",
            "Model/name": "ridge",
        }
    )

    assert connected == {
        "Run/task": "tabular_train",
        "Input/local_path": "data/sample_train.csv",
        "Model/name": "ridge",
    }
    assert ("Run", {"task": "tabular_train"}) in task.calls
    assert ("Input", {"local_path": "data/sample_train.csv"}) in task.calls
    assert ("Model", {"name": "ridge"}) in task.calls


def test_clearml_apply_metadata_can_move_runtime_task_project():
    adapter = load_clearml_adapter_module()

    class FakeTaskForMetadata:
        def __init__(self):
            self.project = None
            self.name = None
            self.tags = []
            self.comment = None

        def move_to_project(self, new_project_name=None, **_kwargs):
            self.project = new_project_name

        def set_name(self, name):
            self.name = name

        def add_tags(self, tags):
            self.tags.extend(tags)

        def set_comment(self, comment):
            self.comment = comment

    task = FakeTaskForMetadata()
    adapter.ClearMLAdapter(task).apply_metadata(
        project_name="Runs/Tabular/Train",
        task_name="stage/train_ridge/run",
        tags=["domain:tabular", "run_type:stage", "model:ridge"],
        comment="stage task",
    )

    assert task.project == "Runs/Tabular/Train"
    assert task.name == "stage/train_ridge/run"
    assert task.tags == ["domain:tabular", "run_type:stage", "model:ridge"]
    assert task.comment == "stage task"


def test_clearml_apply_metadata_can_replace_stale_runtime_tags():
    adapter = load_clearml_adapter_module()

    class FakeTaskForMetadata:
        def __init__(self):
            self.tags = ["domain:tabular", "run_type:stage", "stage:preprocess_features"]

        def set_tags(self, tags):
            self.tags = list(tags)

    task = FakeTaskForMetadata()
    adapter.ClearMLAdapter(task).apply_metadata(
        tags=["domain:tabular", "run_type:stage", "stage:evaluate_models", "internal:true"],
        replace_tags=True,
    )

    assert "stage:evaluate_models" in task.tags
    assert "stage:preprocess_features" not in task.tags
    assert task.tags == sorted({"domain:tabular", "run_type:stage", "stage:evaluate_models", "internal:true"})


class FakeArtifact:
    def __init__(self, url):
        self.url = url


class FakeTask:
    def __init__(self, task_id, name, *, artifacts=None, params=None, parent=None):
        self.id = task_id
        self.name = name
        self.artifacts = artifacts or {}
        self._params = params or {}
        self.parent = parent

    def get_parameters(self, cast=False):
        return dict(self._params)


def _install_fake_task_api(adapter, tasks):
    by_id = {task.id: task for task in tasks}

    class FakeTaskApi:
        @staticmethod
        def get_task(task_id=None, **_kwargs):
            return by_id[task_id]

        @staticmethod
        def get_tasks(task_filter=None, **_kwargs):
            parent = (task_filter or {}).get("parent")
            return [task for task in tasks if task.parent == parent]

    def fake_import(symbol):
        if symbol == "Task":
            return FakeTaskApi
        raise AssertionError(symbol)

    adapter.import_clearml_symbol = fake_import


def test_clearml_resolves_infer_source_from_pipeline_controller_best_task():
    adapter = load_clearml_adapter_module()
    tasks = [
        FakeTask("pipe", "tabular_train_pipeline_template"),
        FakeTask(
            "preprocess",
            "preprocess_features",
            artifacts={
                "feature_spec": FakeArtifact("feature_spec.json"),
                "preprocess_bundle": FakeArtifact("preprocess_bundle.joblib"),
            },
            params={"Run/stage": "preprocess_features"},
            parent="pipe",
        ),
        FakeTask(
            "eval",
            "evaluate_models",
            artifacts={
                "best_model": FakeArtifact("best_model.joblib"),
                "best_model_json": FakeArtifact("best_model.json"),
            },
            params={"Run/stage": "evaluate_models"},
            parent="pipe",
        ),
    ]
    _install_fake_task_api(adapter, tasks)
    resolver = adapter.ClearMLAdapter(task=None)
    resolver.resolve_artifact_path = lambda value: str(value)

    cfg = {"task": "tabular_infer", "model": {"source_type": "task_id", "source_task_id": "pipe", "model_selector": "best"}}
    resolved = resolver.resolve_infer_model_source(cfg)

    assert resolved["model"]["artifact_path"] == "best_model.joblib"
    assert resolved["model"]["info_path"] == "best_model.json"
    assert resolved["model"]["feature_spec_path"] == "feature_spec.json"
    assert resolved["model"]["preprocess_bundle_path"] == "preprocess_bundle.joblib"
    assert resolved["model"]["resolved_source_task_name"] == "evaluate_models"
    assert resolved["model"]["resolved_source_artifact"] == "best_model"


def test_clearml_resolves_infer_source_from_pipeline_controller_ensemble_task():
    adapter = load_clearml_adapter_module()
    tasks = [
        FakeTask("pipe", "tabular_train_pipeline_template"),
        FakeTask(
            "build",
            "build_ensemble",
            artifacts={
                "model": FakeArtifact("ensemble.joblib"),
                "model_info": FakeArtifact("ensemble_model_info.json"),
                "ensemble_info": FakeArtifact("ensemble_info.json"),
            },
            params={"Run/stage": "build_ensemble"},
            parent="pipe",
        ),
    ]
    _install_fake_task_api(adapter, tasks)
    resolver = adapter.ClearMLAdapter(task=None)
    resolver.resolve_artifact_path = lambda value: str(value)

    cfg = {"task": "tabular_infer", "model": {"source_type": "task_id", "source_task_id": "pipe", "model_selector": "ensemble"}}
    resolved = resolver.resolve_infer_model_source(cfg)

    assert resolved["model"]["artifact_path"] == "ensemble.joblib"
    assert resolved["model"]["info_path"] == "ensemble_model_info.json"
    assert resolved["model"]["resolved_source_task_name"] == "build_ensemble"


def test_clearml_resolves_infer_source_from_pipeline_controller_ensemble_method_task():
    adapter = load_clearml_adapter_module()
    tasks = [
        FakeTask("pipe", "tabular_train_pipeline_template"),
        FakeTask(
            "build",
            "build_ensemble",
            artifacts={
                "model_weighted": FakeArtifact("ensemble_weighted.joblib"),
                "model_info_weighted": FakeArtifact("ensemble_weighted_model_info.json"),
                "ensemble_info_weighted": FakeArtifact("ensemble_weighted_info.json"),
            },
            params={"Run/stage": "build_ensemble"},
            parent="pipe",
        ),
    ]
    _install_fake_task_api(adapter, tasks)
    resolver = adapter.ClearMLAdapter(task=None)
    resolver.resolve_artifact_path = lambda value: str(value)

    cfg = {"task": "tabular_infer", "model": {"source_type": "task_id", "source_task_id": "pipe", "model_selector": "ensemble:weighted"}}
    resolved = resolver.resolve_infer_model_source(cfg)

    assert resolved["model"]["artifact_path"] == "ensemble_weighted.joblib"
    assert resolved["model"]["info_path"] == "ensemble_weighted_model_info.json"
    assert resolved["model"]["resolved_source_artifact"] == "model_weighted"


def test_clearml_resolves_infer_source_from_direct_train_stage_task():
    adapter = load_clearml_adapter_module()
    tasks = [
        FakeTask(
            "train-linear",
            "train_linear",
            artifacts={"model": FakeArtifact("linear.joblib"), "model_info": FakeArtifact("linear_model_info.json")},
            params={"Run/stage": "train_model", "Model/name": "linear"},
        )
    ]
    _install_fake_task_api(adapter, tasks)
    resolver = adapter.ClearMLAdapter(task=None)
    resolver.resolve_artifact_path = lambda value: str(value)

    cfg = {
        "task": "tabular_infer",
        "model": {"source_type": "task_id", "source_task_id": "train-linear", "model_selector": "linear"},
    }
    resolved = resolver.resolve_infer_model_source(cfg)

    assert resolved["model"]["artifact_path"] == "linear.joblib"
    assert resolved["model"]["info_path"] == "linear_model_info.json"


def test_clearml_infer_source_resolution_reports_available_tasks_on_failure():
    adapter = load_clearml_adapter_module()
    tasks = [FakeTask("pipe", "pipeline"), FakeTask("train-ridge", "train_ridge", params={"Run/stage": "train_model"}, parent="pipe")]
    _install_fake_task_api(adapter, tasks)
    resolver = adapter.ClearMLAdapter(task=None)

    cfg = {"task": "tabular_infer", "model": {"source_type": "task_id", "source_task_id": "pipe", "model_selector": "linear"}}
    with pytest.raises(ValueError, match="Discovered:"):
        resolver.resolve_infer_model_source(cfg)


def test_clearml_launch_targets_use_infer_stage_and_training_pipeline_drafts():
    templates = load_clearml_templates_module()
    assert [name for name, _, _ in templates.TEMPLATES] == [
        "tabular_infer_template",
        "tabular_stage_template",
        "tabular_train_pipeline_template",
    ]
    assert [name for name, _, _ in templates.TASK_TEMPLATES] == [
        "tabular_infer_template",
        "tabular_stage_template",
    ]
    assert [name for name, _, _ in templates.PIPELINE_TEMPLATES] == [
        "tabular_train_pipeline_template",
    ]
    assert templates.PIPELINE_TEMPLATES[0][1] == "config/tasks/tabular_pipeline.yaml"
    assert templates._entry_point("tabular_stage_template") == "clearml/app.py"
    assert templates._entry_point("tabular_train_pipeline_template") == "clearml/pipelines.py"
    assert templates.clearml_template_name("tabular_train_pipeline_template") == "template/tabular_train_pipeline"
    assert templates.clearml_template_name("tabular_infer_template") == "template/tabular_infer"
    assert templates.clearml_template_name("tabular_stage_template") == "internal/tabular_stage"
    assert templates._template_tags("tabular_train_pipeline_template") == [
        "domain:tabular",
        "run_type:template",
        "user_facing:true",
    ]
    assert templates._template_tags("tabular_stage_template") == [
        "domain:tabular",
        "run_type:template",
        "internal:true",
    ]


def test_clearml_training_pipeline_plan_is_stage_graph():
    pipelines = load_clearml_pipelines_module()
    plan = pipelines.build_pipeline_plan("config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml")

    assert plan["kind"] == "training"
    assert plan["project"] == "MLPlatform/Dev/Pipelines/Tabular"
    assert plan["stage_project"] == "MLPlatform/Dev/Runs/Tabular/Stages"
    assert plan["stage_projects"] == {
        "preprocess": "MLPlatform/Dev/Runs/Tabular/Preprocess",
        "train": "MLPlatform/Dev/Runs/Tabular/Train",
        "ensemble": "MLPlatform/Dev/Runs/Tabular/Ensemble",
        "evaluate": "MLPlatform/Dev/Runs/Tabular/Evaluate",
    }
    assert plan["name"] == "pipeline/tabular_train_pipeline/tabular_training_pipeline"
    assert plan["tags"] == ["domain:tabular", "run_type:pipeline", "user_facing:true"]
    assert [step["name"] for step in plan["steps"]] == [
        "preprocess_features",
        "train_linear",
        "train_ridge",
        "train_lasso",
        "train_elasticnet",
        "train_random_forest",
        "train_extra_trees",
        "train_gradient_boosting",
        "train_lightgbm",
        "train_xgboost",
        "train_catboost",
        "build_ensemble_mean_topk",
        "build_ensemble_weighted",
        "build_ensemble_median",
        "evaluate_models",
    ]
    assert all(step["base_task_project"] == "MLPlatform/Dev/Templates/Tabular" for step in plan["steps"])
    assert all(step["base_task_name"] == "internal/tabular_stage" for step in plan["steps"])
    assert plan["steps"][1]["parents"] == ["preprocess_features"]
    assert plan["steps"][-1]["parents"] == [
        "train_linear",
        "train_ridge",
        "train_lasso",
        "train_elasticnet",
        "train_random_forest",
        "train_extra_trees",
        "train_gradient_boosting",
        "train_lightgbm",
        "train_xgboost",
        "train_catboost",
        "build_ensemble_mean_topk",
        "build_ensemble_weighted",
        "build_ensemble_median",
    ]
    assert plan["steps"][0]["target_project"] == "MLPlatform/Dev/Runs/Tabular/Preprocess"
    assert plan["steps"][1]["target_project"] == "MLPlatform/Dev/Runs/Tabular/Train"
    assert plan["steps"][1]["parameter_override"]["Run/stage"] == "train_model"
    assert plan["steps"][1]["parameter_override"]["Run/name"] == "stage/train_linear/tabular_training_pipeline"
    assert plan["steps"][1]["parameter_override"]["Model/evaluation_metrics"] == '["mae", "rmse", "r2"]'
    assert plan["steps"][1]["parameter_override"]["Output/report_plots"] is True
    assert "Features/preset" in plan["steps"][0]["parameter_override"]
    assert "Model/feature_preset" not in plan["steps"][0]["parameter_override"]
    assert "Features/preset" not in plan["steps"][1]["parameter_override"]
    assert plan["steps"][-4]["name"] == "build_ensemble_mean_topk"
    assert plan["steps"][-4]["target_project"] == "MLPlatform/Dev/Runs/Tabular/Ensemble"
    assert plan["steps"][-4]["parameter_override"]["Run/stage"] == "build_ensemble"
    assert plan["steps"][-4]["parameter_override"]["Run/name"] == "stage/build_ensemble_mean_topk/tabular_training_pipeline"
    assert plan["steps"][-4]["parameter_override"]["Model/ensemble_methods"] == '["mean_topk"]'
    assert plan["steps"][-4]["tags"] == [
        "domain:tabular",
        "run_type:stage",
        "internal:true",
        "stage:build_ensemble",
        "ensemble:mean_topk",
    ]
    assert plan["steps"][-1]["parameter_override"]["Run/stage"] == "evaluate_models"
    assert plan["steps"][-1]["target_project"] == "MLPlatform/Dev/Runs/Tabular/Evaluate"
    assert plan["steps"][-1]["parameter_override"]["Model/evaluation_metrics"] == '["mae", "rmse", "r2"]'
    assert plan["steps"][-1]["parameter_override"]["Output/report_plots"] is True
    assert plan["steps"][1]["tags"] == [
        "domain:tabular",
        "run_type:stage",
        "internal:true",
        "stage:train_model",
        "model:linear",
    ]
    assert "${train_linear.artifacts.model.url}" in plan["steps"][-1]["parameter_override"]["Input/model_refs"]
    assert "${build_ensemble_mean_topk.artifacts.model_mean_topk.url}" in plan["steps"][-1]["parameter_override"]["Input/ensemble_refs"]
    assert "${build_ensemble_weighted.artifacts.model_weighted.url}" in plan["steps"][-1]["parameter_override"]["Input/ensemble_refs"]
    assert "${build_ensemble_median.artifacts.model_median.url}" in plan["steps"][-1]["parameter_override"]["Input/ensemble_refs"]


def test_clearml_deprecated_full_pipeline_templates_are_not_sync_targets():
    templates = load_clearml_templates_module()

    removed_names = {
        "tabular_train" + "_full" + "_pipeline_template",
        "tabular_train" + "_full" + "_ensemble_pipeline_template",
    }
    assert removed_names.isdisjoint({name for name, _, _ in templates.TEMPLATES})


def test_clearml_training_pipeline_rejects_search_primary_graph():
    pipelines = load_clearml_pipelines_module()

    with pytest.raises(ValueError, match="future/experimental"):
        pipelines.build_pipeline_plan(
            "config/tasks/tabular_pipeline.yaml",
            "config/profiles/clearml-dev.yaml",
            overrides=["model.search.enabled=true"],
        )


def test_clearml_legacy_full_run_plan_is_not_product_pipeline(tmp_path):
    pipelines = load_clearml_pipelines_module()
    task_path = write_compat_pipeline_config(tmp_path)

    with pytest.raises(ValueError, match="stage-based training pipeline"):
        pipelines.build_pipeline_plan(task_path, "config/profiles/clearml-dev.yaml")


def test_clearml_training_pipeline_plan_applies_dataset_and_model_overrides():
    pipelines = load_clearml_pipelines_module()
    plan = pipelines.build_pipeline_plan(
        "config/tasks/tabular_pipeline.yaml",
        "config/profiles/clearml-dev.yaml",
        ui_params={
            "Input/clearml_dataset_id": "dataset-id",
            "Input/dataset_file": "train.csv",
            "Input/target_column": "target",
            "Input/id_columns": ["id"],
            "Split/valid_size": 0.3,
            "Features/preset": "numeric_only",
            "Features/numeric_impute_strategy": "mean",
            "Features/categorical_impute_strategy": "mode",
            "Features/categorical_encoder": "drop",
            "Features/scaling": "none",
            "Features/drop_columns": '["unused"]',
            "Features/passthrough_columns": '["raw_numeric"]',
            "Model/params": "{}",
            "Model/candidates": '["linear","ridge"]',
            "Model/selection_metric": "rmse",
            "Model/evaluation_metrics": '["mae","rmse"]',
            "Model/ensemble_enabled": True,
            "Model/ensemble_methods": '["mean_topk","weighted"]',
            "Model/ensemble_top_k": 2,
            "Output/report_plots": False,
        },
    )

    assert [step["name"] for step in plan["steps"]] == [
        "preprocess_features",
        "train_linear",
        "train_ridge",
        "build_ensemble_mean_topk",
        "build_ensemble_weighted",
        "evaluate_models",
    ]
    preprocess = plan["steps"][0]
    train_linear = plan["steps"][1]
    build = plan["steps"][3]
    assert preprocess["parameter_override"]["Input/clearml_dataset_id"] == "dataset-id"
    assert preprocess["parameter_override"]["Input/dataset_file"] == "train.csv"
    assert preprocess["parameter_override"]["Input/target_column"] == "target"
    assert preprocess["parameter_override"]["Input/id_columns"] == ["id"]
    assert preprocess["parameter_override"]["Split/valid_size"] == 0.3
    assert preprocess["parameter_override"]["Features/preset"] == "numeric_only"
    assert preprocess["parameter_override"]["Features/numeric_impute_strategy"] == "mean"
    assert preprocess["parameter_override"]["Features/categorical_impute_strategy"] == "mode"
    assert preprocess["parameter_override"]["Features/categorical_encoder"] == "drop"
    assert preprocess["parameter_override"]["Features/scaling"] == "none"
    assert preprocess["parameter_override"]["Features/drop_columns"] == ["unused"]
    assert preprocess["parameter_override"]["Features/passthrough_columns"] == ["raw_numeric"]
    assert train_linear["parameter_override"]["Model/name"] == "linear"
    assert train_linear["parameter_override"]["Run/name"] == "stage/train_linear/tabular_training_pipeline"
    assert train_linear["parameter_override"]["Model/params"] == "{}"
    assert train_linear["parameter_override"]["Model/selection_metric"] == "rmse"
    assert train_linear["parameter_override"]["Model/evaluation_metrics"] == '["mae","rmse"]'
    assert "Features/preset" not in train_linear["parameter_override"]
    assert "Model/feature_preset" not in train_linear["parameter_override"]
    assert train_linear["parameter_override"]["Output/report_plots"] is False
    assert train_linear["parameter_override"]["Input/preprocess_bundle"] == "${preprocess_features.artifacts.preprocess_bundle.url}"
    assert build["parameter_override"]["Model/ensemble_enabled"] is True
    assert build["parameter_override"]["Model/ensemble_methods"] == '["mean_topk"]'
    assert build["parameter_override"]["Run/name"] == "stage/build_ensemble_mean_topk/tabular_training_pipeline"
    assert build["tags"] == [
        "domain:tabular",
        "run_type:stage",
        "internal:true",
        "stage:build_ensemble",
        "ensemble:mean_topk",
    ]
    weighted = plan["steps"][4]
    assert weighted["parameter_override"]["Model/ensemble_methods"] == '["weighted"]'
    assert weighted["parameter_override"]["Run/name"] == "stage/build_ensemble_weighted/tabular_training_pipeline"
    assert weighted["tags"] == [
        "domain:tabular",
        "run_type:stage",
        "internal:true",
        "stage:build_ensemble",
        "ensemble:weighted",
    ]
    assert build["parameter_override"]["Model/ensemble_top_k"] == 2
