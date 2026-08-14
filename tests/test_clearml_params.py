import json

import pytest

from ml_platform_core.config import load_run_config
from ml_platform_core.contracts import ParameterSpec
from ml_platform_core.value_coercion import as_str_list
from ml_platform_tabular.manifest import get_tabular_manifest

from clearml_test_utils import (
    load_clearml_adapter_module,
    load_clearml_params_module,
    load_clearml_pipeline_plan_module,
)


def test_clearml_runtime_param_helpers_use_current_names():
    adapter = load_clearml_adapter_module()
    params = load_clearml_params_module()
    pipeline_plan = load_clearml_pipeline_plan_module()
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml")

    assert "Run/task" in params.build_default_connected_params(cfg)
    assert params.group_connected_params({"Run/name": "demo"}) == {"Run": {"name": "demo"}}
    assert params.apply_connected_params_to_config(cfg, {"Run/seed": 11})["run"]["seed"] == 11
    assert as_str_list('["a", 2]') == ["a", "2"]
    assert as_str_list("a,b") == ["a", "b"]
    assert not hasattr(adapter, "default_runtime_params")
    assert not hasattr(adapter, "apply_runtime_params")
    assert "Basic/model_suite" in pipeline_plan.pipeline_runtime_params(
        "config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml"
    )


def test_clearml_param_transport_coerces_current_keys():
    params = load_clearml_params_module()

    connected = params.coerce_connected_params(
        {
            "Run/seed": "13",
            "Model/name": "ridge",
            "Input/id_columns": '["id", 2]',
            "Features/drop_columns": "unused,debug",
            "Model/model_params_by_name": '{"ridge":{"alpha":2.0}}',
            "Output/upload_plots": "false",
            "Unknown/value": "kept for caller filtering",
        }
    )

    assert connected["Run/seed"] == 13
    assert connected["Model/name"] == "ridge"
    assert connected["Input/id_columns"] == ["id", "2"]
    assert connected["Features/drop_columns"] == ["unused", "debug"]
    assert connected["Model/model_params_by_name"] == {"ridge": {"alpha": 2.0}}
    assert connected["Output/upload_plots"] is False
    assert connected["Unknown/value"] == "kept for caller filtering"
    assert json.loads(params.normalize_clearml_param_value({"a": [1, 2]})) == {"a": [1, 2]}


def test_clearml_default_params_are_declared_by_manifest_bindings():
    params = load_clearml_params_module()
    manifest_keys = {parameter.name for task in get_tabular_manifest().tasks for parameter in task.parameters}

    for task_path in (
        "config/tasks/tabular_infer.yaml",
        "config/tasks/tabular_pipeline.yaml",
        "config/tasks/tabular_stage.yaml",
    ):
        cfg = load_run_config(task_path, "config/profiles/clearml-dev.yaml")
        defaults = params.build_default_connected_params(cfg)
        binding_keys = {binding.key for binding in params.bindings_for_config(cfg)}
        assert set(defaults) <= manifest_keys
        assert set(defaults) <= binding_keys


def test_clearml_runtime_bindings_reject_conflicting_duplicate_specs():
    params = load_clearml_params_module()
    base = ParameterSpec(name="Input/example", value_type="str")

    assert params.unique_specs(((base,), (ParameterSpec(name="Input/example", value_type="str", required=True),)))
    with pytest.raises(ValueError, match="Input/example"):
        params.unique_specs(((base,), (ParameterSpec(name="Input/example", value_type="int"),)))


def test_clearml_runtime_params_apply_current_keys_and_ignore_unknown_keys():
    params = load_clearml_params_module()
    cfg = load_run_config("config/tasks/tabular_stage.yaml", "config/profiles/clearml-dev.yaml")

    updated = params.apply_connected_params_to_config(
        cfg,
        {
            "Run/seed": "17",
            "Model/name": "lasso",
            "Unknown/value": "ignored",
        },
    )

    assert updated["run"]["seed"] == 17
    assert updated["model"]["name"] == "lasso"
    assert "Unknown" not in updated


def test_clearml_runtime_params_are_applied_to_nested_config():
    params = load_clearml_params_module()
    cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/clearml-dev.yaml")
    connected = {
        "Input/local_path": "data/other.csv",
        "Input/dataset_file": "train.csv",
        "Input/target_column": "y",
        "Run/seed": 7,
        "Model/source_type": "task_id",
        "Model/source_task_id": "train-task-id",
        "Model/model_selector": "best",
        "Model/local_model_path": "outputs/latest_training_pipeline",
        "Model/artifact_path": "outputs/latest_train/model.joblib",
        "Model/info_path": "outputs/latest_train/model_info.json",
        "Output/prediction_name": "scored.csv",
        "Output/chunk_size": 500,
    }
    updated = params.apply_connected_params_to_config(cfg, connected)
    assert updated["data"]["local_path"] == "data/other.csv"
    assert updated["data"]["dataset_file"] == "train.csv"
    assert updated["data"]["target_column"] == "y"
    assert updated["run"]["seed"] == 7
    assert updated["model"]["source_type"] == "task_id"
    assert updated["model"]["source_task_id"] == "train-task-id"
    assert updated["model"]["model_selector"] == "best"
    assert updated["model"]["local_model_path"] == "outputs/latest_training_pipeline"
    assert updated["model"]["artifact_path"] == "outputs/latest_train/model.joblib"
    assert updated["model"]["info_path"] == "outputs/latest_train/model_info.json"
    assert updated["output"]["prediction_name"] == "scored.csv"
    assert updated["output"]["chunk_size"] == 500


def test_clearml_stage_runtime_params_include_feature_group():
    params = load_clearml_params_module()
    cfg = load_run_config("config/tasks/tabular_stage.yaml", "config/profiles/clearml-dev.yaml")
    defaults = params.build_default_connected_params(cfg)

    assert "Input/dataset_file" in defaults
    assert defaults["Run/stage"] == "preprocess_features"
    assert defaults["Model/name"] == "ridge"
    assert defaults["Model/params"] == "{}"
    assert defaults["Model/candidates"] == "[]"
    assert defaults["Model/selection_metric"] == "rmse"
    assert defaults["Model/ensemble_enabled"] is False
    assert defaults["Model/ensemble_method"] == "mean_topk"
    assert defaults["Model/ensemble_top_k"] == 3
    assert defaults["Features/preset"] == "basic"
    assert {key.split("/", 1)[0] for key in defaults} <= {"Input", "Run", "Split", "Model", "Features", "Output"}
    assert defaults["Output/upload_plots"] is True


def test_clearml_flat_ensemble_params_apply_to_nested_config():
    params = load_clearml_params_module()
    cfg = load_run_config("config/tasks/tabular_stage.yaml", "config/profiles/clearml-dev.yaml")

    updated = params.apply_connected_params_to_config(
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


def test_clearml_default_runtime_params_cover_primary_and_internal_tasks():
    params = load_clearml_params_module()
    infer = params.build_default_connected_params(
        load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/clearml-dev.yaml")
    )
    pipeline = params.build_default_connected_params(
        load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml")
    )
    stage = params.build_default_connected_params(
        load_run_config("config/tasks/tabular_stage.yaml", "config/profiles/clearml-dev.yaml")
    )

    assert {
        "Model/name",
        "Model/params",
        "Model/candidates",
        "Model/selection_metric",
        "Model/ensemble_enabled",
        "Model/ensemble_method",
        "Model/ensemble_top_k",
        "Features/preset",
    }.issubset(stage)
    assert "Output/prediction_name" in infer
    assert "Output/chunk_size" in infer
    assert {
        "Model/source_type",
        "Model/source_task_id",
        "Model/model_selector",
        "Model/local_model_path",
    }.issubset(infer)
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
        "Output/upload_plots",
    }.issubset(pipeline)
    # The user-facing Pipeline New Run surface is asserted separately below.
    assert "Model/search_enabled" not in pipeline
    assert "Model/search_method" not in pipeline
    assert "Model/search_space" not in pipeline
    assert "Model/max_trials" not in pipeline
    assert "Output/prediction_name" not in pipeline
    assert "Run/stage" in stage
    assert "Input/preprocess_bundle" in stage
    assert "Input/model_refs" in stage


def test_clearml_pipeline_params_map_model_metrics_and_output_options():
    params = load_clearml_params_module()
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml")

    updated = params.apply_connected_params_to_config(
        cfg,
        {
            "Model/model_params_by_name": '{"ridge":{"alpha":2.0}}',
            "Model/evaluation_metrics": '["mae","rmse"]',
            "Features/preset": "numeric_only",
            "Features/numeric_impute_strategy": "mean",
            "Features/categorical_encoder": "drop",
            "Features/drop_columns": '["unused"]',
            "Features/passthrough_columns": '["x1"]',
            "Split/method": "group",
            "Split/valid_size": 0.25,
            "Split/group_column": "customer_id",
            "Split/time_column": "event_time",
            "Split/valid_filter_column": "split_flag",
            "Split/valid_filter_value": "valid",
            "Output/upload_plots": False,
        },
    )

    assert updated["model"]["params"] == {"ridge": {"alpha": 2.0}}
    assert updated["metrics"]["names"] == ["mae", "rmse"]
    assert updated["split"]["method"] == "group"
    assert updated["split"]["valid_size"] == 0.25
    assert updated["split"]["group_column"] == "customer_id"
    assert updated["split"]["time_column"] == "event_time"
    assert updated["split"]["valid_filter_column"] == "split_flag"
    assert updated["split"]["valid_filter_value"] == "valid"
    assert updated["features"]["preset"] == "numeric_only"
    assert updated["features"]["numeric_impute_strategy"] == "mean"
    assert updated["features"]["categorical_encoder"] == "drop"
    assert updated["features"]["drop_columns"] == ["unused"]
    assert updated["features"]["passthrough_columns"] == ["x1"]
    assert updated["output"]["upload_plots"] is False
