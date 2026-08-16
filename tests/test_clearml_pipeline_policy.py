import json

import pytest
from clearml_test_utils import load_clearml_pipeline_plan_module


def _build_plan(runtime_params):
    return load_clearml_pipeline_plan_module().build_pipeline_plan(
        "config/tasks/tabular_pipeline.yaml",
        "config/profiles/clearml-dev.yaml",
        runtime_params=runtime_params,
    )


def _train_model_params(plan, model_name):
    step = next(step for step in plan["steps"] if step["name"] == f"train_{model_name}")
    return json.loads(step["parameter_override"]["Model/params"])


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
    plan = _build_plan({"Basic/model_suite": suite})

    assert plan["model_suite"] == suite
    assert plan["candidate_models"] == expected
    assert [step["name"] for step in plan["steps"] if step["name"].startswith("train_")] == [
        f"train_{model_name}" for model_name in expected
    ]


@pytest.mark.parametrize(
    ("suite", "quality", "expected_candidates", "expected_values"),
    [
        (
            "fast",
            "fast",
            ["linear", "ridge", "lasso", "elasticnet", "random_forest", "extra_trees", "gradient_boosting"],
            {
                "random_forest": {"n_estimators": 10},
                "extra_trees": {"n_estimators": 10},
                "gradient_boosting": {"n_estimators": 10},
            },
        ),
        (
            "default",
            "standard",
            None,
            {
                "random_forest": {"n_estimators": 20},
                "gradient_boosting": {"n_estimators": 20},
                "lightgbm": {"n_estimators": 100},
                "xgboost": {"n_estimators": 100},
                "catboost": {"iterations": 100},
            },
        ),
        (
            "tree",
            "quality",
            ["random_forest", "extra_trees", "gradient_boosting"],
            {
                "random_forest": {"n_estimators": 60},
                "extra_trees": {"n_estimators": 60},
                "gradient_boosting": {"n_estimators": 60},
            },
        ),
    ],
)
def test_clearml_basic_quality_mode_sets_bounded_params(suite, quality, expected_candidates, expected_values):
    plan = _build_plan({"Basic/model_suite": suite, "Basic/quality_mode": quality})

    if expected_candidates is not None:
        assert plan["candidate_models"] == expected_candidates
    for model_name, values in expected_values.items():
        model_params = _train_model_params(plan, model_name)
        for key, value in values.items():
            assert model_params[key] == value


def test_clearml_explicit_model_params_override_basic_quality_mode():
    plan = _build_plan(
        {
            "Basic/model_suite": "tree",
            "Basic/quality_mode": "quality",
            "Run/seed": 123,
            "Model/model_params_by_name": '{"random_forest":{"n_estimators":7,"random_state":999}}',
        }
    )

    assert _train_model_params(plan, "random_forest") == {"n_estimators": 7, "random_state": 123}
    assert _train_model_params(plan, "extra_trees") == {"random_state": 123}
    assert all(step["parameter_override"]["Run/seed"] == 123 for step in plan["steps"])


def test_clearml_basic_custom_model_suite_uses_model_candidates():
    plan = _build_plan(
        {
            "Basic/model_suite": "custom",
            "Model/candidates": '["linear","ridge"]',
        }
    )

    assert plan["model_suite"] == "custom"
    assert plan["candidate_models"] == ["linear", "ridge"]
    assert _train_model_params(plan, "ridge") == {"alpha": 1.0}


def test_clearml_custom_model_suite_respects_explicit_model_params():
    plan = _build_plan(
        {
            "Basic/model_suite": "custom",
            "Basic/quality_mode": "quality",
            "Model/candidates": '["ridge"]',
            "Model/model_params_by_name": '{"ridge":{"alpha":2.5}}',
        }
    )

    assert plan["model_suite"] == "custom"
    assert plan["candidate_models"] == ["ridge"]
    assert _train_model_params(plan, "ridge") == {"alpha": 2.5}


def test_clearml_basic_use_ensemble_controls_pipeline_steps():
    plan = _build_plan(
        {
            "Basic/model_suite": "custom",
            "Model/candidates": '["linear","ridge"]',
            "Basic/use_ensemble": False,
        }
    )

    assert plan["ensemble_enabled"] is False
    assert [step["name"] for step in plan["steps"]] == [
        "preprocess_features",
        "train_linear",
        "train_ridge",
        "evaluate_models",
    ]


def test_clearml_detailed_ensemble_enabled_overrides_basic_use_ensemble():
    plan = _build_plan(
        {
            "Basic/model_suite": "custom",
            "Model/candidates": '["linear","ridge"]',
            "Basic/use_ensemble": False,
            "Model/ensemble_enabled": True,
            "Model/ensemble_methods": '["mean_topk"]',
        }
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
