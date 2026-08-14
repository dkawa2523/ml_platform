from __future__ import annotations

from ml_platform_core.contracts import (
    ArtifactKind,
    ArtifactSpec,
    PackageManifest,
    ParameterSpec,
    ParameterValueType,
    PipelineSpec,
    StageSpec,
    TaskSpec,
)

from .ensemble import SUPPORTED_ENSEMBLE_METHODS
from .models import SUPPORTED_MODELS
from .policy import model_suite_names, quality_mode_names

TABULAR_DOMAIN = "tabular"
TABULAR_MANIFEST_VERSION = "0.1.0"
TABULAR_STAGE_RUNNER = "ml_platform_tabular.stage:run_stage"
TABULAR_PIPELINE_RUNNER = "ml_platform_tabular.training:run_pipeline"
TABULAR_INFER_RUNNER = "ml_platform_tabular.inference:run_infer"

TRAINING_STAGE_KEYS = ("preprocess_features", "train_model", "build_ensemble", "evaluate_models")


def _artifact(name: str, kind: ArtifactKind, *, required: bool = True) -> ArtifactSpec:
    return ArtifactSpec(name=name, kind=kind, required=required)


def _param(
    name: str,
    value_type: ParameterValueType,
    *,
    required: bool = False,
    default: object | None = None,
    choices: tuple[str, ...] = (),
) -> ParameterSpec:
    return ParameterSpec(name=name, value_type=value_type, required=required, default=default, choices=choices)


def _params_by_name(*groups: tuple[ParameterSpec, ...]) -> tuple[ParameterSpec, ...]:
    params: dict[str, ParameterSpec] = {}
    for group in groups:
        for parameter in group:
            params.setdefault(parameter.name, parameter)
    return tuple(params.values())


def _select_params(parameters: tuple[ParameterSpec, ...], names: tuple[str, ...]) -> tuple[ParameterSpec, ...]:
    by_name = {parameter.name: parameter for parameter in parameters}
    return tuple(by_name[name] for name in names)


TABULAR_BASIC_PARAMETERS = (
    _param("Basic/model_suite", "enum", default="default", choices=model_suite_names()),
    _param("Basic/quality_mode", "enum", default="standard", choices=quality_mode_names()),
    _param("Basic/use_ensemble", "bool", default=True),
    _param("Basic/notes", "str"),
)
TABULAR_RUN_PARAMETERS = (
    _param("Run/task", "str"),
    _param("Run/name", "str"),
    _param("Run/seed", "int"),
)
TABULAR_STAGE_RUN_PARAMETERS = (
    *TABULAR_RUN_PARAMETERS,
    _param("Run/stage", "enum", choices=TRAINING_STAGE_KEYS),
)
TABULAR_DATA_PARAMETERS = (
    _param("Input/local_path", "str"),
    _param("Input/clearml_dataset_id", "str"),
    _param("Input/dataset_file", "str"),
    _param("Input/source_manifest", "str"),
    _param("Input/target_column", "str"),
    _param("Input/feature_columns", "list"),
    _param("Input/id_columns", "list"),
)
TABULAR_INFER_DATA_PARAMETERS = TABULAR_DATA_PARAMETERS
TABULAR_SPLIT_PARAMETERS = (
    _param("Split/method", "str", default="random"),
    _param("Split/valid_size", "float", default=0.2),
    _param("Split/group_column", "str"),
    _param("Split/time_column", "str"),
    _param("Split/valid_filter_column", "str"),
    _param("Split/valid_filter_value", "str"),
)
TABULAR_FEATURE_PARAMETERS = (
    _param("Features/preset", "str", default="basic"),
    _param("Features/numeric_impute_strategy", "str", default="median"),
    _param("Features/categorical_impute_strategy", "str", default="missing_token"),
    _param("Features/categorical_encoder", "str", default="onehot"),
    _param("Features/scaling", "str", default="standard"),
    _param("Features/drop_columns", "list", default=[]),
    _param("Features/passthrough_columns", "list", default=[]),
)
TABULAR_MODEL_PARAMETERS = (
    _param("Model/name", "enum", required=True, choices=tuple(SUPPORTED_MODELS)),
    _param("Model/model_params_by_name", "dict", default={}),
    _param("Model/params", "dict", default={}),
    _param("Model/candidates", "json", default=list(SUPPORTED_MODELS)),
    _param("Model/selection_metric", "str", default="rmse"),
    _param("Model/source_type", "enum", default="local_path", choices=("task_id", "local_path")),
    _param("Model/source_task_id", "str"),
    _param("Model/model_selector", "str", default="best"),
    _param("Model/local_model_path", "str"),
    _param("Model/evaluation_metrics", "list"),
    _param("Model/ensemble_enabled", "bool"),
    _param("Model/ensemble_methods", "list", default=["mean_topk"]),
    _param("Model/ensemble_method", "enum", default="mean_topk", choices=tuple(SUPPORTED_ENSEMBLE_METHODS)),
    _param("Model/ensemble_top_k", "int", default=3),
)
TABULAR_STAGE_INPUT_PARAMETERS = (
    _param("Input/preprocess_bundle", "json"),
    _param("Input/processed_train", "json"),
    _param("Input/processed_valid", "json"),
    _param("Input/model_refs", "json"),
    _param("Input/ensemble_refs", "json"),
)
TABULAR_OUTPUT_PARAMETERS = (
    _param("Output/prediction_name", "str"),
    _param("Output/upload_plots", "bool", default=True),
)
TABULAR_TRAIN_MODEL_PARAMETERS = _select_params(
    TABULAR_MODEL_PARAMETERS,
    ("Model/name", "Model/params", "Model/selection_metric"),
)
TABULAR_ENSEMBLE_MODEL_PARAMETERS = _select_params(
    TABULAR_MODEL_PARAMETERS,
    ("Model/ensemble_method", "Model/ensemble_top_k", "Model/selection_metric"),
)
TABULAR_EVALUATE_MODEL_PARAMETERS = _select_params(TABULAR_MODEL_PARAMETERS, ("Model/selection_metric",))
_INFER_MODEL_KEYS = (
    "Model/source_type",
    "Model/source_task_id",
    "Model/model_selector",
    "Model/local_model_path",
)
TABULAR_INFER_MODEL_PARAMETERS = _select_params(TABULAR_MODEL_PARAMETERS, _INFER_MODEL_KEYS)
_PIPELINE_MODEL_KEYS = (
    "Model/model_params_by_name",
    "Model/candidates",
    "Model/selection_metric",
    "Model/evaluation_metrics",
    "Model/ensemble_methods",
    "Model/ensemble_top_k",
)
_STAGE_MODEL_KEYS = (
    "Model/name",
    "Model/params",
    "Model/selection_metric",
    "Model/evaluation_metrics",
    "Model/ensemble_enabled",
    "Model/ensemble_methods",
    "Model/ensemble_method",
    "Model/ensemble_top_k",
)
TABULAR_STAGE_TASK_PARAMETERS = _params_by_name(
    TABULAR_STAGE_RUN_PARAMETERS,
    TABULAR_DATA_PARAMETERS,
    TABULAR_SPLIT_PARAMETERS,
    TABULAR_FEATURE_PARAMETERS,
    _select_params(TABULAR_MODEL_PARAMETERS, _STAGE_MODEL_KEYS),
    TABULAR_STAGE_INPUT_PARAMETERS,
    TABULAR_OUTPUT_PARAMETERS,
)
TABULAR_PIPELINE_PARAMETERS = _params_by_name(
    TABULAR_BASIC_PARAMETERS,
    TABULAR_RUN_PARAMETERS,
    TABULAR_DATA_PARAMETERS,
    TABULAR_SPLIT_PARAMETERS,
    TABULAR_FEATURE_PARAMETERS,
    _select_params(TABULAR_MODEL_PARAMETERS, _PIPELINE_MODEL_KEYS),
    _select_params(TABULAR_OUTPUT_PARAMETERS, ("Output/upload_plots",)),
)
TABULAR_INFER_PARAMETERS = _params_by_name(
    TABULAR_RUN_PARAMETERS,
    TABULAR_INFER_DATA_PARAMETERS,
    TABULAR_INFER_MODEL_PARAMETERS,
    _select_params(TABULAR_OUTPUT_PARAMETERS, ("Output/prediction_name",)),
)


TABULAR_PREPROCESS_STAGE = StageSpec(
    key="preprocess_features",
    kind="preprocess",
    display_name="Preprocess features",
    runner_path=TABULAR_STAGE_RUNNER,
    parameters=_params_by_name(TABULAR_DATA_PARAMETERS, TABULAR_SPLIT_PARAMETERS, TABULAR_FEATURE_PARAMETERS),
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
    parameters=TABULAR_TRAIN_MODEL_PARAMETERS,
    input_artifacts=(
        _artifact("preprocess_bundle", "file"),
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
        *TABULAR_ENSEMBLE_MODEL_PARAMETERS,
    ),
    input_artifacts=(
        _artifact("preprocess_bundle", "file"),
        _artifact("processed_train", "table"),
        _artifact("processed_valid", "table"),
    ),
    output_artifacts=(
        _artifact("model", "model"),
        _artifact("model_info", "json"),
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
        *TABULAR_EVALUATE_MODEL_PARAMETERS,
    ),
    input_artifacts=(),
    output_artifacts=(
        _artifact("leaderboard", "table"),
        _artifact("best_model", "model", required=False),
        _artifact("model_info", "json", required=False),
        _artifact("best_model_json", "json", required=False),
        _artifact("metrics", "json"),
        _artifact("evaluation_predictions", "table", required=False),
    ),
)
TABULAR_INFER_STAGE = StageSpec(
    key="infer",
    kind="infer",
    display_name="Tabular inference",
    runner_path=TABULAR_INFER_RUNNER,
    parameters=TABULAR_INFER_PARAMETERS,
    output_artifacts=(
        _artifact("predictions", "table"),
        _artifact("schema_check_summary", "json"),
        _artifact("prediction_summary", "table"),
        _artifact("prediction_preview", "table"),
        _artifact("prediction_distribution", "plot", required=False),
        _artifact("manifest", "json"),
    ),
)

TABULAR_STAGES = (
    TABULAR_PREPROCESS_STAGE,
    TABULAR_TRAIN_STAGE,
    TABULAR_ENSEMBLE_STAGE,
    TABULAR_EVALUATE_STAGE,
    TABULAR_INFER_STAGE,
)
TABULAR_PIPELINE_ARTIFACTS = (
    _artifact("leaderboard", "table"),
    _artifact("best_model", "model", required=False),
    _artifact("best_model_json", "json", required=False),
    _artifact("metrics", "json"),
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
    parameters=TABULAR_STAGE_TASK_PARAMETERS,
    stage_keys=TRAINING_STAGE_KEYS,
)
TABULAR_INFER_TASK = TaskSpec(
    key="tabular_infer",
    display_name="Tabular inference",
    runner_path=TABULAR_INFER_RUNNER,
    kind="task",
    parameters=TABULAR_INFER_PARAMETERS,
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
    tags=("problem:regression", "domain:tabular"),
)


def get_tabular_manifest() -> PackageManifest:
    return TABULAR_MANIFEST
