import json

import pytest
from clearml_test_utils import (
    load_clearml_pipeline_controller_module,
    load_clearml_pipeline_plan_module,
    load_clearml_pipeline_steps_module,
)
from ml_platform_core.contracts import DomainStepPlan

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
DEFAULT_ENSEMBLES = ["build_ensemble_mean_topk", "build_ensemble_weighted", "build_ensemble_median"]


def _default_step_names():
    return [
        "preprocess_features",
        *[f"train_{model}" for model in DEFAULT_MODELS],
        *DEFAULT_ENSEMBLES,
        "evaluate_models",
    ]


def _train_model_params(plan, model_name):
    step = next(step for step in plan["steps"] if step["name"] == f"train_{model_name}")
    return json.loads(step["parameter_override"]["Model/params"])


def test_clearml_pipeline_cli_candidate_override_is_not_replaced_by_defaults():
    pipeline_plan = load_clearml_pipeline_plan_module()

    plan = pipeline_plan.build_pipeline_plan(
        "config/tasks/tabular_pipeline.yaml",
        "config/profiles/clearml-dev.yaml",
        overrides=["model.candidates=[linear,ridge]", "model.ensemble.enabled=false"],
    )

    assert plan["candidate_models"] == ["linear", "ridge"]
    assert [step["name"] for step in plan["steps"]] == [
        "preprocess_features",
        "train_linear",
        "train_ridge",
        "evaluate_models",
    ]


def test_clearml_pipeline_cli_model_params_override_quality_defaults():
    pipeline_plan = load_clearml_pipeline_plan_module()

    plan = pipeline_plan.build_pipeline_plan(
        "config/tasks/tabular_pipeline.yaml",
        "config/profiles/clearml-dev.yaml",
        overrides=[
            "model.candidates=[ridge]",
            "model.params.ridge.alpha=9.0",
            "model.ensemble.enabled=false",
        ],
    )

    assert _train_model_params(plan, "ridge") == {"alpha": 9.0}


def test_clearml_training_pipeline_plan_is_stage_graph():
    pipeline_plan = load_clearml_pipeline_plan_module()
    plan = pipeline_plan.build_pipeline_plan("config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml")

    _assert_default_plan_metadata(plan)
    _assert_default_plan_steps(plan)
    _assert_default_plan_stage_overrides(plan)
    _assert_default_plan_ref_wiring(plan)


def test_clearml_pipeline_plan_reports_missing_domain_artifacts():
    pipeline_steps = load_clearml_pipeline_steps_module()
    step = DomainStepPlan(
        name="train_bad",
        stage_key="train_model",
        expected_artifacts=("model", "model_info", "metrics"),
        model_name="ridge",
    )

    with pytest.raises(ValueError, match=r"train_bad.*selection_predictions"):
        pipeline_steps._model_ref(step)


def _assert_default_plan_metadata(plan):
    assert plan["kind"] == "training"
    assert plan["project"] == "MLPlatform/Dev/Pipelines/Tabular"
    assert plan["stage_project"] == "MLPlatform/Dev/Runs/Tabular/Stages"
    assert plan["controller_queue"] == "controller"
    assert plan["stage_queue"] == "default"
    assert plan["queue"] == "default"
    assert plan["stage_projects"] == {
        "preprocess": "MLPlatform/Dev/Runs/Tabular/Preprocess",
        "train": "MLPlatform/Dev/Runs/Tabular/Train",
        "ensemble": "MLPlatform/Dev/Runs/Tabular/Ensemble",
        "evaluate": "MLPlatform/Dev/Runs/Tabular/Evaluate",
    }
    assert plan["name"] == "pipeline/tabular_train_pipeline/tabular_training_pipeline"
    assert plan["tags"] == ["domain:tabular", "run_type:pipeline", "user_facing:true"]


def _assert_default_plan_steps(plan):
    assert [step["name"] for step in plan["steps"]] == _default_step_names()
    assert all(step["base_task_project"] == "MLPlatform/Dev/Templates/Tabular" for step in plan["steps"])
    assert all(step["base_task_name"] == "internal/tabular_stage" for step in plan["steps"])
    assert plan["steps"][1]["parents"] == ["preprocess_features"]
    assert plan["steps"][-1]["parents"] == _default_step_names()[1:-1]


def _assert_default_plan_stage_overrides(plan):
    _assert_default_preprocess_step(plan["steps"][0])
    _assert_default_train_step(plan["steps"][1])
    _assert_default_ensemble_step(plan["steps"][-4])
    _assert_default_evaluate_step(plan["steps"][-1])


def _assert_default_preprocess_step(step):
    assert step["target_project"] == "MLPlatform/Dev/Runs/Tabular/Preprocess"
    assert step["execution_queue"] == "default"
    assert "Features/preset" in step["parameter_override"]


def _assert_default_train_step(step):
    assert step["target_project"] == "MLPlatform/Dev/Runs/Tabular/Train"
    assert step["execution_queue"] == "default"
    assert step["parameter_override"]["Run/stage"] == "train_model"
    assert step["parameter_override"]["Run/name"] == "stage/train_linear/tabular_training_pipeline"
    assert step["parameter_override"]["Model/evaluation_metrics"] == '["mae", "rmse", "r2"]'
    assert step["parameter_override"]["Output/upload_plots"] is True
    assert "Features/preset" not in step["parameter_override"]
    assert step["tags"] == [
        "domain:tabular",
        "run_type:stage",
        "internal:true",
        "stage:train_model",
        "model:linear",
    ]


def _assert_default_ensemble_step(step):
    assert step["name"] == "build_ensemble_mean_topk"
    assert step["target_project"] == "MLPlatform/Dev/Runs/Tabular/Ensemble"
    assert step["parameter_override"]["Run/stage"] == "build_ensemble"
    assert step["parameter_override"]["Run/name"] == "stage/build_ensemble_mean_topk/tabular_training_pipeline"
    assert step["parameter_override"]["Model/ensemble_methods"] == '["mean_topk"]'
    assert step["tags"] == [
        "domain:tabular",
        "run_type:stage",
        "internal:true",
        "stage:build_ensemble",
        "ensemble:mean_topk",
    ]


def _assert_default_evaluate_step(step):
    assert step["parameter_override"]["Run/stage"] == "evaluate_models"
    assert step["target_project"] == "MLPlatform/Dev/Runs/Tabular/Evaluate"
    assert step["parameter_override"]["Model/evaluation_metrics"] == '["mae", "rmse", "r2"]'
    assert step["parameter_override"]["Output/upload_plots"] is True


def _assert_default_plan_ref_wiring(plan):
    assert "${train_linear.artifacts.model.url}" in plan["steps"][-1]["parameter_override"]["Input/model_refs"]
    assert (
        "${build_ensemble_mean_topk.artifacts.model_mean_topk.url}"
        in plan["steps"][-1]["parameter_override"]["Input/ensemble_refs"]
    )
    assert (
        "${build_ensemble_weighted.artifacts.model_weighted.url}"
        in plan["steps"][-1]["parameter_override"]["Input/ensemble_refs"]
    )
    assert (
        "${build_ensemble_median.artifacts.model_median.url}"
        in plan["steps"][-1]["parameter_override"]["Input/ensemble_refs"]
    )


def test_clearml_add_plan_steps_uses_rendered_domain_plan_order():
    pipeline_plan = load_clearml_pipeline_plan_module()
    pipeline_controller = load_clearml_pipeline_controller_module()
    plan = pipeline_plan.build_pipeline_plan(
        "config/tasks/tabular_pipeline.yaml",
        "config/profiles/clearml-dev.yaml",
        runtime_params={
            "Basic/model_suite": "custom",
            "Model/candidates": '["linear","ridge"]',
            "Basic/use_ensemble": False,
        },
    )

    class FakePipeline:
        def __init__(self):
            self.default_queue = None
            self.steps = []

        def set_default_execution_queue(self, queue):
            self.default_queue = queue

        def add_step(self, **kwargs):
            self.steps.append(kwargs)

    pipe = FakePipeline()
    pipeline_controller._add_plan_steps(pipe, plan)

    assert pipe.default_queue == "default"
    assert [step["name"] for step in pipe.steps] == [
        "preprocess_features",
        "train_linear",
        "train_ridge",
        "evaluate_models",
    ]
    assert pipe.steps[1]["parents"] == ["preprocess_features"]
    assert pipe.steps[-1]["parents"] == ["train_linear", "train_ridge"]
    assert pipe.steps[1]["stage"] == "train_linear"
    assert pipe.steps[1]["parameter_override"]["Model/name"] == "linear"
    assert pipe.steps[-1]["parameter_override"]["Run/stage"] == "evaluate_models"


def test_clearml_training_pipeline_plan_applies_dataset_and_model_overrides():
    pipeline_plan = load_clearml_pipeline_plan_module()
    plan = pipeline_plan.build_pipeline_plan(
        "config/tasks/tabular_pipeline.yaml",
        "config/profiles/clearml-dev.yaml",
        runtime_params={
            "Input/clearml_dataset_id": "dataset-id",
            "Input/dataset_file": "train.csv",
            "Input/target_column": "target",
            "Input/id_columns": ["id"],
            "Split/method": "group",
            "Split/valid_size": 0.3,
            "Split/group_column": "customer_id",
            "Split/time_column": "event_time",
            "Split/valid_filter_column": "split_flag",
            "Split/valid_filter_value": "valid",
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
            "Output/upload_plots": False,
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
    _assert_override_preprocess_params(preprocess["parameter_override"])
    _assert_override_train_params(train_linear["parameter_override"])
    _assert_override_ensemble_step(build, method="mean_topk")
    _assert_override_ensemble_step(plan["steps"][4], method="weighted")
    assert build["parameter_override"]["Model/ensemble_top_k"] == 2


def _assert_override_preprocess_params(params):
    assert params["Input/clearml_dataset_id"] == "dataset-id"
    assert params["Input/dataset_file"] == "train.csv"
    assert params["Input/target_column"] == "target"
    assert params["Input/id_columns"] == ["id"]
    assert params["Split/method"] == "group"
    assert params["Split/valid_size"] == 0.3
    assert params["Split/group_column"] == "customer_id"
    assert params["Split/time_column"] == "event_time"
    assert params["Split/valid_filter_column"] == "split_flag"
    assert params["Split/valid_filter_value"] == "valid"
    assert params["Features/preset"] == "numeric_only"
    assert params["Features/numeric_impute_strategy"] == "mean"
    assert params["Features/categorical_impute_strategy"] == "mode"
    assert params["Features/categorical_encoder"] == "drop"
    assert params["Features/scaling"] == "none"
    assert params["Features/drop_columns"] == ["unused"]
    assert params["Features/passthrough_columns"] == ["raw_numeric"]


def _assert_override_train_params(params):
    assert params["Model/name"] == "linear"
    assert params["Run/name"] == "stage/train_linear/tabular_training_pipeline"
    assert params["Model/params"] == "{}"
    assert params["Model/selection_metric"] == "rmse"
    assert json.loads(params["Model/evaluation_metrics"]) == ["mae", "rmse"]
    assert "Features/preset" not in params
    assert params["Output/upload_plots"] is False
    assert params["Input/preprocess_bundle"] == "${preprocess_features.artifacts.preprocess_bundle.url}"


def _assert_override_ensemble_step(step, *, method):
    assert step["parameter_override"]["Model/ensemble_enabled"] is True
    assert step["parameter_override"]["Model/ensemble_methods"] == f'["{method}"]'
    assert step["parameter_override"]["Run/name"] == f"stage/build_ensemble_{method}/tabular_training_pipeline"
    assert step["tags"] == [
        "domain:tabular",
        "run_type:stage",
        "internal:true",
        "stage:build_ensemble",
        f"ensemble:{method}",
    ]
