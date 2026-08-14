from __future__ import annotations

import importlib
import importlib.util
from typing import cast

import pytest

from ml_platform_core.contracts import (
    ArtifactKind,
    ArtifactSpec,
    PackageManifest,
    ParameterSpec,
    ParameterValueType,
)
from ml_platform_tabular.domain_plan import build_tabular_domain_plan
from ml_platform_tabular.manifest import (
    TABULAR_PREPROCESS_STAGE,
    TABULAR_STAGE_TASK,
    get_tabular_manifest,
)
from ml_platform_tabular.policy import model_suite_candidates, quality_model_params


def _resolve_runner(path: str):
    module_name, attr_name = path.split(":", 1)
    module = importlib.import_module(module_name)
    return getattr(module, attr_name)


def test_tabular_manifest_loads_and_has_unique_keys():
    manifest = get_tabular_manifest()

    assert manifest.domain == "tabular"
    assert manifest.version
    assert "problem:regression" in manifest.tags
    assert len({stage.key for stage in manifest.stages}) == len(manifest.stages)
    assert len({task.key for task in manifest.tasks}) == len(manifest.tasks)
    assert len({pipeline.key for pipeline in manifest.pipelines}) == len(manifest.pipelines)
    assert manifest.pipeline("tabular_training_graph").stage_keys == (
        "preprocess_features",
        "train_model",
        "build_ensemble",
        "evaluate_models",
    )


def test_tabular_manifest_runner_paths_resolve_without_clearml():
    manifest = get_tabular_manifest()

    for stage in manifest.stages:
        assert callable(_resolve_runner(stage.runner_path))
    for task in manifest.tasks:
        assert callable(_resolve_runner(task.runner_path))


def test_tabular_manifest_declares_required_parameters_and_artifacts():
    manifest = get_tabular_manifest()
    preprocess = manifest.stage("preprocess_features")
    target = next(parameter for parameter in preprocess.parameters if parameter.name == "Input/target_column")
    source_manifest = next(
        parameter for parameter in preprocess.parameters if parameter.name == "Input/source_manifest"
    )
    train = manifest.stage("train_model")
    evaluate = manifest.stage("evaluate_models")
    infer = manifest.stage("infer")
    infer_target = next(parameter for parameter in infer.parameters if parameter.name == "Input/target_column")
    source_type = next(parameter for parameter in infer.parameters if parameter.name == "Model/source_type")

    assert target.required is False
    assert source_manifest.required is False
    assert infer_target.required is False
    assert source_type.choices == ("task_id", "local_path")
    assert {artifact.name for artifact in preprocess.output_artifacts} >= {
        "preprocess_bundle",
        "feature_spec",
        "processed_train",
        "processed_valid",
    }
    assert {artifact.name for artifact in train.output_artifacts} >= {
        "model",
        "model_info",
        "metrics",
        "validation_predictions",
    }
    assert {artifact.name for artifact in evaluate.output_artifacts} >= {
        "leaderboard",
        "best_model",
        "best_model_json",
        "metrics",
        "evaluation_predictions",
    }
    assert {artifact.name for artifact in infer.output_artifacts} >= {
        "predictions",
        "schema_check_summary",
        "prediction_summary",
        "prediction_preview",
        "prediction_distribution",
        "manifest",
    }
    assert "schema_check" not in {artifact.name for artifact in infer.output_artifacts}


def test_package_manifest_rejects_duplicate_stage_keys():
    with pytest.raises(ValueError, match="PackageManifest.stages"):
        PackageManifest(
            domain="duplicate",
            version="0.1.0",
            tasks=(TABULAR_STAGE_TASK,),
            stages=(TABULAR_PREPROCESS_STAGE, TABULAR_PREPROCESS_STAGE),
        )


def test_contract_specs_validate_supported_kinds():
    with pytest.raises(ValueError, match="ArtifactSpec.kind"):
        ArtifactSpec(name="bad", kind=cast(ArtifactKind, "unsupported"))
    with pytest.raises(ValueError, match="ParameterSpec.value_type"):
        ParameterSpec(name="bad", value_type=cast(ParameterValueType, "object"))
    with pytest.raises(ValueError, match="enum type but no choices"):
        ParameterSpec(name="mode", value_type="enum")


def test_runtime_contract_surface_stays_minimal():
    manifest = get_tabular_manifest()
    stage = manifest.stage("preprocess_features")
    task = manifest.task("tabular_pipeline")
    pipeline = manifest.pipeline("tabular_training_graph")
    plan = build_tabular_domain_plan(candidates=("ridge",), include_ensemble=False)

    assert importlib.util.find_spec("ml_platform_core.runtime_types") is None
    assert importlib.util.find_spec("ml_platform_tabular.infer") is None
    assert importlib.util.find_spec("ml_platform_tabular.pipeline") is None
    assert importlib.util.find_spec("ml_platform_tabular.plots") is None
    assert not hasattr(stage, "supports_local_run")
    assert not hasattr(stage, "supports_remote_run")
    assert not hasattr(task, "runtime_features")
    assert not hasattr(task, "user_facing")
    assert not hasattr(pipeline, "entry_stage_key")
    assert not hasattr(pipeline, "supports_partial_stage_run")
    assert not hasattr(plan, "tags")
    assert not hasattr(plan.steps[0], "tags")


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
    assert plan.run_name == "unit-test"
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
        run_name="unit-test",
        candidates=({"name": "ridge", "params": {"alpha": 2.0}},),
        ensemble_methods=("weighted",),
        selection_metric="mae",
        preprocess_overrides={"Input/target_column": "target"},
        stage_common_overrides={"Output/upload_plots": False},
        ensemble_top_k=2,
    )

    train = plan.steps[1]
    ensemble = plan.steps[2]
    evaluate = plan.steps[3]
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


def test_tabular_domain_plan_validates_models_and_ensemble_methods():
    with pytest.raises(ValueError, match="out of current product scope"):
        build_tabular_domain_plan(candidates=("knn",))
    with pytest.raises(ValueError, match="Unsupported ensemble methods"):
        build_tabular_domain_plan(ensemble_methods=("stacking",))
