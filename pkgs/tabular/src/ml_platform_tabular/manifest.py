from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ml_platform_core.contracts import (
    ArtifactSpec,
    DomainPipelinePlan,
    DomainStepPlan,
    PackageManifest,
    ParameterSpec,
    PipelineSpec,
    StageSpec,
    TaskSpec,
)

from .ensemble import SUPPORTED_ENSEMBLE_METHODS
from .models import SUPPORTED_MODELS, validate_model_name
from .policy import model_suite_names, quality_mode_names

TABULAR_DOMAIN = "tabular"
TABULAR_MANIFEST_VERSION = "0.1.0"
TABULAR_STAGE_RUNNER = "ml_platform_tabular.stage:run_stage"
TABULAR_PIPELINE_RUNNER = "ml_platform_tabular.pipeline:run_pipeline"
TABULAR_INFER_RUNNER = "ml_platform_tabular.infer:run_infer"

TRAINING_STAGE_KEYS = ("preprocess_features", "train_model", "build_ensemble", "evaluate_models")


def _artifact(name: str, kind: str, *, required: bool = True) -> ArtifactSpec:
    return ArtifactSpec(name=name, kind=kind, required=required)


def _param(
    name: str,
    value_type: str,
    *,
    required: bool = False,
    default: object | None = None,
    choices: tuple[str, ...] = (),
) -> ParameterSpec:
    return ParameterSpec(
        name=name,
        value_type=value_type,
        required=required,
        default=default,
        choices=choices,
    )


TABULAR_PREPROCESS_STAGE = StageSpec(
    key="preprocess_features",
    kind="preprocess",
    display_name="Preprocess features",
    runner_path=TABULAR_STAGE_RUNNER,
    parameters=(
        _param("Input/local_path", "str"),
        _param("Input/clearml_dataset_id", "str"),
        _param("Input/dataset_file", "str"),
        _param("Input/target_column", "str", required=True),
        _param("Input/feature_columns", "list"),
        _param("Input/id_columns", "list"),
        _param("Split/method", "str", default="random"),
        _param("Split/valid_size", "float", default=0.2),
        _param("Features/preset", "str", default="basic"),
    ),
    output_artifacts=(
        _artifact("preprocess_bundle", "file"),
        _artifact("feature_spec", "json"),
        _artifact("processed_train", "table"),
        _artifact("processed_valid", "table"),
    ),
)
TABULAR_TRAIN_STAGE = StageSpec(
    key="train_model",
    kind="train",
    display_name="Train model",
    runner_path=TABULAR_STAGE_RUNNER,
    parameters=(
        _param("Model/name", "enum", required=True, choices=tuple(SUPPORTED_MODELS)),
        _param("Model/params", "json", default={}),
        _param("Model/selection_metric", "str", default="rmse"),
    ),
    input_artifacts=(
        _artifact("preprocess_bundle", "file"),
        _artifact("feature_spec", "json"),
        _artifact("processed_train", "table"),
        _artifact("processed_valid", "table"),
    ),
    output_artifacts=(
        _artifact("model", "model"),
        _artifact("model_info", "json"),
        _artifact("metrics", "json"),
        _artifact("validation_predictions", "table"),
    ),
)
TABULAR_ENSEMBLE_STAGE = StageSpec(
    key="build_ensemble",
    kind="ensemble",
    display_name="Build ensemble",
    runner_path=TABULAR_STAGE_RUNNER,
    parameters=(
        _param("Input/model_refs", "json", required=True),
        _param("Model/ensemble_method", "enum", default="mean_topk", choices=tuple(SUPPORTED_ENSEMBLE_METHODS)),
        _param("Model/ensemble_top_k", "int", default=3),
        _param("Model/selection_metric", "str", default="rmse"),
    ),
    input_artifacts=(
        _artifact("preprocess_bundle", "file"),
        _artifact("feature_spec", "json"),
    ),
    output_artifacts=(
        _artifact("model", "model"),
        _artifact("model_info", "json"),
        _artifact("ensemble_info", "json"),
        _artifact("metrics", "json"),
        _artifact("ensemble_predictions", "table"),
    ),
)
TABULAR_EVALUATE_STAGE = StageSpec(
    key="evaluate_models",
    kind="evaluate",
    display_name="Evaluate models",
    runner_path=TABULAR_STAGE_RUNNER,
    parameters=(
        _param("Input/model_refs", "json", required=True),
        _param("Input/ensemble_refs", "json"),
        _param("Model/selection_metric", "str", default="rmse"),
    ),
    input_artifacts=(
        _artifact("preprocess_bundle", "file"),
        _artifact("feature_spec", "json"),
    ),
    output_artifacts=(
        _artifact("decision_summary", "file"),
        _artifact("leaderboard", "table"),
        _artifact("metrics", "json"),
    ),
)
TABULAR_INFER_STAGE = StageSpec(
    key="infer",
    kind="infer",
    display_name="Tabular inference",
    runner_path=TABULAR_INFER_RUNNER,
    parameters=(
        _param("Model/source_type", "enum", default="local_path", choices=("pipeline_task", "task", "local_path")),
        _param("Model/source_task_id", "str"),
        _param("Model/model_selector", "str", default="best"),
        _param("Model/local_model_path", "str"),
        _param("Input/local_path", "str", required=True),
    ),
    output_artifacts=(
        _artifact("predictions", "table"),
        _artifact("schema_check", "json"),
    ),
)

TABULAR_STAGES = (
    TABULAR_PREPROCESS_STAGE,
    TABULAR_TRAIN_STAGE,
    TABULAR_ENSEMBLE_STAGE,
    TABULAR_EVALUATE_STAGE,
    TABULAR_INFER_STAGE,
)
TABULAR_PIPELINE_PARAMETERS = (
    _param("Basic/model_suite", "enum", default="default", choices=model_suite_names()),
    _param("Basic/quality_mode", "enum", default="standard", choices=quality_mode_names()),
    _param("Basic/use_ensemble", "bool", default=True),
    _param("Basic/notes", "str"),
    _param("Run/name", "str"),
    _param("Run/seed", "int"),
    _param("Input/local_path", "str"),
    _param("Input/clearml_dataset_id", "str"),
    _param("Input/dataset_file", "str"),
    _param("Input/target_column", "str", required=True),
    _param("Input/feature_columns", "list"),
    _param("Input/id_columns", "list"),
    _param("Model/candidates", "json", default=list(SUPPORTED_MODELS)),
    _param("Model/model_params_by_name", "json", default={}),
    _param("Model/selection_metric", "str", default="rmse"),
    _param("Model/ensemble_enabled", "bool"),
    _param("Model/ensemble_methods", "json", default=["mean_topk"]),
    _param("Model/ensemble_top_k", "int", default=3),
    _param("Output/report_plots", "bool", default=True),
)
TABULAR_PIPELINE_ARTIFACTS = (
    _artifact("decision_summary", "file"),
    _artifact("leaderboard", "table"),
    _artifact("best_model", "model", required=False),
)

TABULAR_PIPELINE_TASK = TaskSpec(
    key="tabular_pipeline",
    display_name="Tabular training pipeline",
    runner_path=TABULAR_PIPELINE_RUNNER,
    kind="pipeline",
    parameters=TABULAR_PIPELINE_PARAMETERS,
    artifacts=TABULAR_PIPELINE_ARTIFACTS,
    stage_keys=TRAINING_STAGE_KEYS,
)
TABULAR_STAGE_TASK = TaskSpec(
    key="tabular_stage",
    display_name="Tabular stage task",
    runner_path=TABULAR_STAGE_RUNNER,
    kind="stage",
    stage_keys=TRAINING_STAGE_KEYS,
)
TABULAR_INFER_TASK = TaskSpec(
    key="tabular_infer",
    display_name="Tabular inference",
    runner_path=TABULAR_INFER_RUNNER,
    kind="task",
    parameters=TABULAR_INFER_STAGE.parameters,
    artifacts=TABULAR_INFER_STAGE.output_artifacts,
    stage_keys=("infer",),
)
TABULAR_TRAINING_PIPELINE_SPEC = PipelineSpec(
    key="tabular_training_graph",
    display_name="Tabular stage-based training graph",
    stage_keys=TRAINING_STAGE_KEYS,
)
TABULAR_MANIFEST = PackageManifest(
    domain=TABULAR_DOMAIN,
    version=TABULAR_MANIFEST_VERSION,
    tasks=(TABULAR_PIPELINE_TASK, TABULAR_STAGE_TASK, TABULAR_INFER_TASK),
    stages=TABULAR_STAGES,
    pipelines=(TABULAR_TRAINING_PIPELINE_SPEC,),
    tags=("problem:scalar_regression", "domain:tabular"),
)


def get_tabular_manifest() -> PackageManifest:
    return TABULAR_MANIFEST


def _safe_step_suffix(value: str) -> str:
    text = "".join(char if char.isalnum() else "_" for char in value.strip().lower())
    return text.strip("_") or "unnamed"


def _normalize_candidates(candidates: Sequence[str | Mapping[str, Any]] | None) -> tuple[dict[str, Any], ...]:
    raw_values = tuple(candidates or ("ridge",))
    values: list[dict[str, Any]] = []
    for index, item in enumerate(raw_values):
        if isinstance(item, str):
            values.append({"name": item, "params": {}})
        elif isinstance(item, Mapping):
            name = item.get("name")
            if not isinstance(name, str) or not name:
                raise ValueError(f"Domain plan candidate[{index}].name is required.")
            params = item.get("params") or {}
            if not isinstance(params, dict):
                raise ValueError(f"Domain plan candidate[{index}].params must be a mapping.")
            values.append({"name": name, "params": dict(params)})
        else:
            raise ValueError(f"Domain plan candidate[{index}] must be a model name or mapping.")
    if not values:
        raise ValueError("Domain plan requires at least one model candidate.")
    for value in values:
        validate_model_name(value["name"])
    return tuple(values)


def _normalize_ensemble_methods(methods: Sequence[str] | None) -> tuple[str, ...]:
    values = tuple(methods or ("mean_topk",))
    invalid = [value for value in values if value not in SUPPORTED_ENSEMBLE_METHODS]
    if invalid:
        choices = ", ".join(SUPPORTED_ENSEMBLE_METHODS)
        raise ValueError(f"Unsupported ensemble methods: {invalid}. Available: {choices}.")
    return values


def build_tabular_domain_plan(
    *,
    run_name: str = "tabular_training_pipeline",
    candidates: Sequence[str | Mapping[str, Any]] | None = None,
    ensemble_methods: Sequence[str] | None = None,
    include_ensemble: bool = True,
    selection_metric: str | None = None,
    preprocess_overrides: Mapping[str, object] | None = None,
    stage_common_overrides: Mapping[str, object] | None = None,
    ensemble_top_k: int = 3,
) -> DomainPipelinePlan:
    model_candidates = _normalize_candidates(candidates)
    methods = _normalize_ensemble_methods(ensemble_methods) if include_ensemble else ()
    preprocess_params = {
        **dict(preprocess_overrides or {}),
        **dict(stage_common_overrides or {}),
    }
    steps: list[DomainStepPlan] = [
        DomainStepPlan(
            name="preprocess_features",
            stage_key="preprocess_features",
            parameter_overrides=preprocess_params,
            expected_artifacts=tuple(artifact.name for artifact in TABULAR_PREPROCESS_STAGE.output_artifacts),
        )
    ]

    train_step_names: list[str] = []
    for candidate in model_candidates:
        model_name = candidate["name"]
        step_name = f"train_{_safe_step_suffix(model_name)}"
        train_step_names.append(step_name)
        train_params: dict[str, object] = {
            **dict(stage_common_overrides or {}),
            "Model/name": model_name,
            "Model/params": candidate.get("params") or {},
        }
        if selection_metric is not None:
            train_params["Model/selection_metric"] = selection_metric
        steps.append(
            DomainStepPlan(
                name=step_name,
                stage_key="train_model",
                parents=("preprocess_features",),
                parameter_overrides=train_params,
                expected_artifacts=tuple(artifact.name for artifact in TABULAR_TRAIN_STAGE.output_artifacts),
                model_name=model_name,
            )
        )

    evaluate_parents = list(train_step_names)
    for method in methods:
        step_name = f"build_ensemble_{_safe_step_suffix(method)}"
        evaluate_parents.append(step_name)
        ensemble_params: dict[str, object] = {
            **dict(stage_common_overrides or {}),
            "Model/ensemble_enabled": True,
            "Model/ensemble_methods": [method],
            "Model/ensemble_method": method,
            "Model/ensemble_top_k": ensemble_top_k,
        }
        if selection_metric is not None:
            ensemble_params["Model/selection_metric"] = selection_metric
        steps.append(
            DomainStepPlan(
                name=step_name,
                stage_key="build_ensemble",
                parents=tuple(train_step_names),
                parameter_overrides=ensemble_params,
                expected_artifacts=tuple(artifact.name for artifact in TABULAR_ENSEMBLE_STAGE.output_artifacts),
                ensemble_method=method,
            )
        )

    evaluate_params: dict[str, object] = dict(stage_common_overrides or {})
    if selection_metric is not None:
        evaluate_params["Model/selection_metric"] = selection_metric
    steps.append(
        DomainStepPlan(
            name="evaluate_models",
            stage_key="evaluate_models",
            parents=tuple(evaluate_parents),
            parameter_overrides=evaluate_params,
            expected_artifacts=tuple(artifact.name for artifact in TABULAR_EVALUATE_STAGE.output_artifacts),
        )
    )
    return DomainPipelinePlan(
        key=TABULAR_TRAINING_PIPELINE_SPEC.key,
        version=TABULAR_MANIFEST.version,
        run_name=run_name,
        steps=tuple(steps),
    )
