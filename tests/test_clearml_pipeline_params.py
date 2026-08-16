import json

from clearml_test_utils import load_clearml_pipeline_controller_module, load_clearml_pipeline_params_module
from ml_platform_tabular.manifest import get_tabular_manifest

DEFAULT_MODELS = [
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


def test_clearml_pipeline_template_has_minimal_training_pipeline_overrides():
    pipeline_params = load_clearml_pipeline_params_module()
    params = pipeline_params.pipeline_runtime_params(
        "config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml"
    )

    _assert_parameter_surface(params)
    _assert_defaults(params)


def test_clearml_pipeline_runtime_params_are_manifest_declared():
    pipeline_params = load_clearml_pipeline_params_module()
    params = pipeline_params.pipeline_runtime_params(
        "config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml"
    )
    manifest_keys = {parameter.name for parameter in get_tabular_manifest().task("tabular_pipeline").parameters}

    assert set(params) <= manifest_keys


def test_clearml_pipeline_new_run_args_are_mapped_to_runtime_params():
    pipeline_params = load_clearml_pipeline_params_module()
    pipeline_controller = load_clearml_pipeline_controller_module()
    defaults = pipeline_params.pipeline_runtime_params(
        "config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml"
    )
    connected = pipeline_params.pipeline_params_from_task(
        defaults,
        {
            "Args/Model/candidates": '["linear","ridge"]',
            "Args/Input/clearml_dataset_id": "dataset-id",
        },
    )

    assert connected["Model/candidates"] == ["linear", "ridge"]
    assert connected["Input/clearml_dataset_id"] == "dataset-id"
    assert pipeline_controller._pipeline_draft_params({"controller_queue": "controller", "stage_queue": "default"}) == {
        "pipeline/controller_queue": "controller",
        "pipeline/default_queue": "default",
    }


def _assert_parameter_surface(params):
    assert {key.split("/", 1)[0] for key in params} <= {
        "Basic",
        "Input",
        "Run",
        "Split",
        "Features",
        "Model",
        "Output",
    }
    expected = {
        "Basic/model_suite",
        "Basic/quality_mode",
        "Basic/use_ensemble",
        "Basic/notes",
        "Run/name",
        "Split/method",
        "Split/valid_size",
        "Split/group_column",
        "Split/time_column",
        "Split/valid_filter_column",
        "Split/valid_filter_value",
        "Input/clearml_dataset_id",
        "Input/local_path",
        "Input/dataset_file",
        "Input/target_column",
        "Input/id_columns",
        "Features/preset",
        "Features/numeric_impute_strategy",
        "Features/categorical_impute_strategy",
        "Features/categorical_encoder",
        "Features/scaling",
        "Features/drop_columns",
        "Features/passthrough_columns",
        "Model/model_params_by_name",
        "Model/evaluation_metrics",
        "Model/candidates",
        "Model/selection_metric",
        "Model/ensemble_methods",
        "Model/ensemble_top_k",
        "Output/upload_plots",
    }
    assert expected <= set(params)
    assert {
        "Run/task",
        "Model/params",
        "Model/ensemble_method",
        "Model/search_enabled",
        "Model/search_method",
        "Model/search_space",
        "Model/max_trials",
        "Run/pipeline_mode",
    }.isdisjoint(params)


def _assert_defaults(params):
    assert params["Output/upload_plots"] is True
    assert params["Input/local_path"] == ""
    assert params["Input/clearml_dataset_id"] == "b7afaea9d7aa42f084fb4fc06b0d4d41"
    assert params["Input/dataset_file"] == "sample_train.csv"
    assert params["Basic/model_suite"] == "default"
    assert params["Basic/quality_mode"] == "standard"
    assert params["Basic/use_ensemble"] is True
    assert params["Basic/notes"] == ""
    assert params["Input/feature_columns"] == []
    assert params["Features/preset"] == "basic"
    assert params["Features/drop_columns"] == "[]"
    assert params["Split/method"] == "random"
    assert params["Split/valid_size"] == 0.2
    assert params["Split/group_column"] is None
    assert params["Split/time_column"] is None
    assert params["Split/valid_filter_column"] is None
    assert params["Split/valid_filter_value"] is None
    assert params["Model/evaluation_metrics"] == '["mae", "rmse", "r2"]'
    assert params["Model/ensemble_methods"] == '["mean_topk", "weighted", "median"]'
    assert json.loads(params["Model/candidates"]) == DEFAULT_MODELS
    assert set(json.loads(params["Model/model_params_by_name"])) == set(DEFAULT_MODELS)
