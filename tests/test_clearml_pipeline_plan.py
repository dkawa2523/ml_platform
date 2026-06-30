import json

import pytest

from clearml_test_utils import load_clearml_pipeline_controller_module, load_clearml_pipeline_plan_module


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
    pipeline_plan = load_clearml_pipeline_plan_module()
    params = pipeline_plan.pipeline_runtime_params(
        "config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml"
    )

    _assert_pipeline_template_param_surface(params)
    _assert_pipeline_template_defaults(params)


def _assert_pipeline_template_param_surface(params):
    assert {key.split("/", 1)[0] for key in params} <= {"Basic", "Input", "Run", "Split", "Features", "Model", "Output"}
    assert {
        "Basic/model_suite",
        "Basic/quality_mode",
        "Basic/use_ensemble",
        "Basic/notes",
    }.issubset(params)
    assert {
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
    assert "Model/search_enabled" not in params
    assert "Model/search_method" not in params
    assert "Model/search_space" not in params
    assert "Model/max_trials" not in params
    assert "Run/" + "pipeline" + "_mode" not in params
    assert "Output/upload_plots" in params


def _assert_pipeline_template_defaults(params):
    _assert_pipeline_template_basic_defaults(params)
    _assert_pipeline_template_split_defaults(params)
    _assert_pipeline_template_model_defaults(params)


def _assert_pipeline_template_basic_defaults(params):
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


def _assert_pipeline_template_split_defaults(params):
    assert params["Split/method"] == "random"
    assert params["Split/valid_size"] == 0.2
    assert params["Split/group_column"] is None
    assert params["Split/time_column"] is None
    assert params["Split/valid_filter_column"] is None
    assert params["Split/valid_filter_value"] is None


def _assert_pipeline_template_model_defaults(params):
    assert params["Model/ensemble_enabled"] == ""
    assert params["Model/evaluation_metrics"] == '["mae", "rmse", "r2"]'
    assert params["Model/ensemble_methods"] == '["mean_topk", "weighted", "median"]'
    assert json.loads(params["Model/candidates"]) == DEFAULT_MODELS
    assert set(json.loads(params["Model/model_params_by_name"])) == set(DEFAULT_MODELS)


def test_clearml_pipeline_new_run_args_are_mapped_to_runtime_params():
    pipeline_plan = load_clearml_pipeline_plan_module()
    defaults = pipeline_plan.pipeline_runtime_params(
        "config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml"
    )
    task_params = {
        "Model/candidates": '["linear"]',
        "Args/Model/candidates": '["linear","ridge"]',
        "Args/Input/clearml_dataset_id": "dataset-id",
    }

    args_params = pipeline_plan.pipeline_arg_params(defaults)
    connected = pipeline_plan.pipeline_params_from_task(defaults, task_params)

    assert args_params["Args/Basic/model_suite"] == defaults["Basic/model_suite"]
    assert args_params["Args/Model/candidates"] == defaults["Model/candidates"]
    assert connected["Model/candidates"] == ["linear", "ridge"]
    assert connected["Input/clearml_dataset_id"] == "dataset-id"


def test_clearml_training_pipeline_plan_is_stage_graph():
    pipeline_plan = load_clearml_pipeline_plan_module()
    plan = pipeline_plan.build_pipeline_plan("config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml")

    _assert_default_plan_metadata(plan)
    _assert_default_plan_steps(plan)
    _assert_default_plan_stage_overrides(plan)
    _assert_default_plan_ref_wiring(plan)


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


@pytest.mark.parametrize(
    ("suite", "expected"),
    [
        (
            "fast",
            ["linear", "ridge", "lasso", "elasticnet", "random_forest", "extra_trees", "gradient_boosting"],
        ),
        ("interpretable", ["linear", "ridge", "lasso", "elasticnet"]),
        ("tree", ["random_forest", "extra_trees", "gradient_boosting"]),
        ("gbm", ["lightgbm", "xgboost", "catboost"]),
    ],
)
def test_clearml_basic_model_suite_selects_candidate_models(suite, expected):
    pipeline_plan = load_clearml_pipeline_plan_module()

    plan = pipeline_plan.build_pipeline_plan(
        "config/tasks/tabular_pipeline.yaml",
        "config/profiles/clearml-dev.yaml",
        runtime_params={"Basic/model_suite": suite},
    )

    assert plan["model_suite"] == suite
    assert plan["candidate_models"] == expected
    assert [step["name"] for step in plan["steps"] if step["name"].startswith("train_")] == [
        f"train_{model_name}" for model_name in expected
    ]


def _train_model_params(plan, model_name):
    step = next(step for step in plan["steps"] if step["name"] == f"train_{model_name}")
    return json.loads(step["parameter_override"]["Model/params"])


def test_clearml_basic_quality_mode_fast_uses_lightweight_params():
    pipeline_plan = load_clearml_pipeline_plan_module()

    plan = pipeline_plan.build_pipeline_plan(
        "config/tasks/tabular_pipeline.yaml",
        "config/profiles/clearml-dev.yaml",
        runtime_params={"Basic/model_suite": "fast", "Basic/quality_mode": "fast"},
    )

    assert plan["candidate_models"] == [
        "linear",
        "ridge",
        "lasso",
        "elasticnet",
        "random_forest",
        "extra_trees",
        "gradient_boosting",
    ]
    assert _train_model_params(plan, "random_forest")["n_estimators"] == 10
    assert _train_model_params(plan, "extra_trees")["n_estimators"] == 10
    assert _train_model_params(plan, "gradient_boosting")["n_estimators"] == 10


def test_clearml_basic_quality_mode_standard_matches_current_defaults():
    pipeline_plan = load_clearml_pipeline_plan_module()

    plan = pipeline_plan.build_pipeline_plan(
        "config/tasks/tabular_pipeline.yaml",
        "config/profiles/clearml-dev.yaml",
        runtime_params={"Basic/model_suite": "default", "Basic/quality_mode": "standard"},
    )

    assert _train_model_params(plan, "random_forest")["n_estimators"] == 20
    assert _train_model_params(plan, "gradient_boosting")["n_estimators"] == 20
    assert _train_model_params(plan, "lightgbm")["n_estimators"] == 100
    assert _train_model_params(plan, "xgboost")["n_estimators"] == 100
    assert _train_model_params(plan, "catboost")["iterations"] == 100


def test_clearml_basic_quality_mode_quality_uses_larger_bounded_params():
    pipeline_plan = load_clearml_pipeline_plan_module()

    plan = pipeline_plan.build_pipeline_plan(
        "config/tasks/tabular_pipeline.yaml",
        "config/profiles/clearml-dev.yaml",
        runtime_params={"Basic/model_suite": "tree", "Basic/quality_mode": "quality"},
    )

    assert plan["candidate_models"] == ["random_forest", "extra_trees", "gradient_boosting"]
    assert _train_model_params(plan, "random_forest")["n_estimators"] == 60
    assert _train_model_params(plan, "extra_trees")["n_estimators"] == 60
    assert _train_model_params(plan, "gradient_boosting")["n_estimators"] == 60


def test_clearml_explicit_model_params_override_basic_quality_mode():
    pipeline_plan = load_clearml_pipeline_plan_module()

    plan = pipeline_plan.build_pipeline_plan(
        "config/tasks/tabular_pipeline.yaml",
        "config/profiles/clearml-dev.yaml",
        runtime_params={
            "Basic/model_suite": "tree",
            "Basic/quality_mode": "quality",
            "Model/model_params_by_name": '{"random_forest":{"n_estimators":7,"random_state":123}}',
        },
    )

    assert _train_model_params(plan, "random_forest") == {"n_estimators": 7, "random_state": 123}
    assert _train_model_params(plan, "extra_trees") == {}


def test_clearml_basic_custom_model_suite_uses_model_candidates():
    pipeline_plan = load_clearml_pipeline_plan_module()

    plan = pipeline_plan.build_pipeline_plan(
        "config/tasks/tabular_pipeline.yaml",
        "config/profiles/clearml-dev.yaml",
        runtime_params={
            "Basic/model_suite": "custom",
            "Model/candidates": '["linear","ridge"]',
        },
    )

    assert plan["model_suite"] == "custom"
    assert plan["candidate_models"] == ["linear", "ridge"]
    assert _train_model_params(plan, "ridge") == {"alpha": 1.0}


def test_clearml_custom_model_suite_respects_explicit_model_params():
    pipeline_plan = load_clearml_pipeline_plan_module()

    plan = pipeline_plan.build_pipeline_plan(
        "config/tasks/tabular_pipeline.yaml",
        "config/profiles/clearml-dev.yaml",
        runtime_params={
            "Basic/model_suite": "custom",
            "Basic/quality_mode": "quality",
            "Model/candidates": '["ridge"]',
            "Model/model_params_by_name": '{"ridge":{"alpha":2.5}}',
        },
    )

    assert plan["model_suite"] == "custom"
    assert plan["candidate_models"] == ["ridge"]
    assert _train_model_params(plan, "ridge") == {"alpha": 2.5}


def test_clearml_basic_use_ensemble_controls_pipeline_steps():
    pipeline_plan = load_clearml_pipeline_plan_module()

    plan = pipeline_plan.build_pipeline_plan(
        "config/tasks/tabular_pipeline.yaml",
        "config/profiles/clearml-dev.yaml",
        runtime_params={
            "Basic/model_suite": "custom",
            "Model/candidates": '["linear","ridge"]',
            "Basic/use_ensemble": False,
        },
    )

    assert plan["ensemble_enabled"] is False
    assert [step["name"] for step in plan["steps"]] == [
        "preprocess_features",
        "train_linear",
        "train_ridge",
        "evaluate_models",
    ]


def test_clearml_detailed_ensemble_enabled_overrides_basic_use_ensemble():
    pipeline_plan = load_clearml_pipeline_plan_module()

    plan = pipeline_plan.build_pipeline_plan(
        "config/tasks/tabular_pipeline.yaml",
        "config/profiles/clearml-dev.yaml",
        runtime_params={
            "Basic/model_suite": "custom",
            "Model/candidates": '["linear","ridge"]',
            "Basic/use_ensemble": False,
            "Model/ensemble_enabled": True,
            "Model/ensemble_methods": '["mean_topk"]',
        },
    )

    assert plan["ensemble_enabled"] is True
    assert "build_ensemble_mean_topk" in [step["name"] for step in plan["steps"]]


def test_clearml_training_pipeline_rejects_search_primary_graph():
    pipeline_plan = load_clearml_pipeline_plan_module()

    with pytest.raises(ValueError, match="future/experimental"):
        pipeline_plan.build_pipeline_plan(
            "config/tasks/tabular_pipeline.yaml",
            "config/profiles/clearml-dev.yaml",
            overrides=["model.search.enabled=true"],
        )


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
