from __future__ import annotations

import pytest
from ml_platform_tabular.domain_plan import build_tabular_domain_plan
from ml_platform_tabular.manifest import get_tabular_manifest
from ml_platform_tabular.policy import model_suite_candidates, quality_model_params


def test_tabular_manifest_exposes_runtime_parameters_and_artifacts():
    manifest = get_tabular_manifest()

    assert manifest.version
    assert {task.key for task in manifest.tasks} == {"tabular_pipeline", "tabular_stage", "tabular_infer"}
    assert {stage.key for stage in manifest.stages} == {
        "preprocess_features",
        "train_model",
        "build_ensemble",
        "evaluate_models",
        "infer",
    }
    assert {parameter.name for parameter in manifest.task("tabular_pipeline").parameters} >= {
        "Input/local_path",
        "Model/candidates",
        "Model/selection_metric",
    }
    assert {artifact.name for artifact in manifest.stage("infer").output_artifacts} == {
        "predictions",
        "schema_check_summary",
        "prediction_summary",
        "prediction_preview",
        "prediction_distribution",
        "manifest",
    }


def test_tabular_policy_presets_are_package_owned_and_copy_safe():
    assert model_suite_candidates("fast") == (
        "linear",
        "ridge",
        "lasso",
        "elasticnet",
        "random_forest",
        "extra_trees",
        "gradient_boosting",
    )
    assert model_suite_candidates("custom") == ()

    params = quality_model_params("fast")
    params["ridge"]["alpha"] = 99
    assert quality_model_params("fast")["ridge"]["alpha"] == 1.0
    with pytest.raises(ValueError, match="quality mode"):
        quality_model_params("unknown")


def test_tabular_domain_plan_builds_without_clearml():
    plan = build_tabular_domain_plan(
        run_name="unit-test",
        candidates=("ridge", "linear"),
        ensemble_methods=("mean_topk",),
    )

    assert plan.key == "tabular_training_graph"
    assert [step.name for step in plan.steps] == [
        "preprocess_features",
        "train_ridge",
        "train_linear",
        "build_ensemble_mean_topk",
        "evaluate_models",
    ]
    assert plan.steps[-1].parents == ("train_ridge", "train_linear", "build_ensemble_mean_topk")
    assert plan.steps[1].parameter_overrides == {"Model/name": "ridge", "Model/params": {}}
    assert "best_model_json" in plan.steps[-1].expected_artifacts


def test_tabular_domain_plan_carries_runtime_neutral_overrides():
    plan = build_tabular_domain_plan(
        candidates=({"name": "ridge", "params": {"alpha": 2.0}},),
        ensemble_methods=("weighted",),
        selection_metric="mae",
        preprocess_overrides={"Input/target_column": "target"},
        stage_common_overrides={"Output/upload_plots": False},
        ensemble_top_k=2,
    )

    train, ensemble, evaluate = plan.steps[1:]
    assert train.parameter_overrides == {
        "Output/upload_plots": False,
        "Model/name": "ridge",
        "Model/params": {"alpha": 2.0},
        "Model/selection_metric": "mae",
    }
    assert ensemble.parameter_overrides["Model/ensemble_methods"] == ["weighted"]
    assert ensemble.parameter_overrides["Model/ensemble_top_k"] == 2
    assert evaluate.parameter_overrides == {
        "Output/upload_plots": False,
        "Model/selection_metric": "mae",
    }


def test_tabular_domain_plan_rejects_unsupported_product_options():
    with pytest.raises(ValueError, match="out of current product scope"):
        build_tabular_domain_plan(candidates=("knn",))
    with pytest.raises(ValueError, match="Unsupported ensemble methods"):
        build_tabular_domain_plan(ensemble_methods=("stacking",))
