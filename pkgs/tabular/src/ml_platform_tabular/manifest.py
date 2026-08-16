from __future__ import annotations

from ml_platform_core.contracts import (
    ArtifactSpec,
    PackageManifest,
    ParameterSpec,
    ParameterValueType,
    StageSpec,
    TaskSpec,
)

TABULAR_MANIFEST_VERSION = "0.1.0"
_CONFIG_SECTIONS = {
    "Input": "data",
    "Split": "split",
    "Features": "features",
    "Model": "model",
    "Output": "output",
    "Run": "run",
}


def _artifact(name: str) -> ArtifactSpec:
    return ArtifactSpec(name=name)


def _param(
    name: str,
    value_type: ParameterValueType,
    *,
    config_path: tuple[str, ...] | None = None,
) -> ParameterSpec:
    if config_path is None:
        section, leaf = name.split("/", 1)
        config_section = _CONFIG_SECTIONS.get(section)
        config_path = (config_section, leaf) if config_section else ()
    return ParameterSpec(name=name, value_type=value_type, config_path=config_path)


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
    _param("Basic/model_suite", "enum"),
    _param("Basic/quality_mode", "enum"),
    _param("Basic/use_ensemble", "bool"),
    _param("Basic/notes", "str"),
)
TABULAR_RUN_PARAMETERS = (
    _param("Run/task", "str", config_path=("task",)),
    _param("Run/name", "str"),
    _param("Run/seed", "int"),
)
TABULAR_STAGE_RUN_PARAMETERS = (
    *TABULAR_RUN_PARAMETERS,
    _param("Run/stage", "enum"),
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
    _param("Split/method", "str"),
    _param("Split/valid_size", "float"),
    _param("Split/selection_size", "float"),
    _param("Split/group_column", "str"),
    _param("Split/time_column", "str"),
    _param("Split/valid_filter_column", "str"),
    _param("Split/valid_filter_value", "str"),
)
TABULAR_FEATURE_PARAMETERS = (
    _param("Features/preset", "str"),
    _param("Features/numeric_impute_strategy", "str"),
    _param("Features/categorical_impute_strategy", "str"),
    _param("Features/categorical_encoder", "str"),
    _param("Features/scaling", "str"),
    _param("Features/drop_columns", "list"),
    _param("Features/passthrough_columns", "list"),
    _param("Features/max_dense_cells", "int"),
)
TABULAR_MODEL_PARAMETERS = (
    _param("Model/name", "enum"),
    _param("Model/model_params_by_name", "dict", config_path=("model", "params")),
    _param("Model/params", "dict"),
    _param("Model/candidates", "json"),
    _param("Model/selection_metric", "str"),
    _param("Model/source_type", "enum"),
    _param("Model/source_task_id", "str"),
    _param("Model/model_selector", "str"),
    _param("Model/local_model_path", "str"),
    _param("Model/evaluation_metrics", "list", config_path=("metrics", "names")),
    _param("Model/ensemble_enabled", "bool", config_path=("model", "ensemble", "enabled")),
    _param("Model/ensemble_methods", "list", config_path=("model", "ensemble", "methods")),
    _param("Model/ensemble_method", "enum", config_path=("model", "ensemble", "method")),
    _param("Model/ensemble_top_k", "int", config_path=("model", "ensemble", "top_k")),
)
TABULAR_STAGE_INPUT_PARAMETERS = (
    _param("Input/preprocess_bundle", "json", config_path=("stage_inputs", "preprocess_bundle")),
    _param("Input/processed_train", "json", config_path=("stage_inputs", "processed_train")),
    _param("Input/processed_valid", "json", config_path=("stage_inputs", "processed_valid")),
    _param("Input/model_refs", "json", config_path=("stage_inputs", "model_refs")),
    _param("Input/ensemble_refs", "json", config_path=("stage_inputs", "ensemble_refs")),
)
TABULAR_OUTPUT_PARAMETERS = (
    _param("Output/prediction_name", "str"),
    _param("Output/upload_plots", "bool"),
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
    parameters=_params_by_name(TABULAR_DATA_PARAMETERS, TABULAR_SPLIT_PARAMETERS, TABULAR_FEATURE_PARAMETERS),
    output_artifacts=(
        _artifact("preprocess_bundle"),
        _artifact("feature_spec"),
        _artifact("processed_train"),
        _artifact("processed_valid"),
    ),
)
TABULAR_TRAIN_STAGE = StageSpec(
    key="train_model",
    parameters=TABULAR_TRAIN_MODEL_PARAMETERS,
    output_artifacts=(
        _artifact("model"),
        _artifact("model_info"),
        _artifact("metrics"),
        _artifact("selection_predictions"),
    ),
)
TABULAR_ENSEMBLE_STAGE = StageSpec(
    key="build_ensemble",
    parameters=(
        *_select_params(TABULAR_STAGE_INPUT_PARAMETERS, ("Input/model_refs",)),
        *TABULAR_ENSEMBLE_MODEL_PARAMETERS,
    ),
    output_artifacts=(
        _artifact("model"),
        _artifact("model_info"),
        _artifact("metrics"),
        _artifact("selection_predictions"),
    ),
)
TABULAR_EVALUATE_STAGE = StageSpec(
    key="evaluate_models",
    parameters=(
        *_select_params(
            TABULAR_STAGE_INPUT_PARAMETERS,
            (
                "Input/preprocess_bundle",
                "Input/processed_train",
                "Input/processed_valid",
                "Input/model_refs",
                "Input/ensemble_refs",
            ),
        ),
        *TABULAR_EVALUATE_MODEL_PARAMETERS,
    ),
    output_artifacts=(
        _artifact("leaderboard"),
        _artifact("best_model"),
        _artifact("model_info"),
        _artifact("best_model_json"),
        _artifact("metrics"),
        _artifact("evaluation_predictions"),
    ),
)
TABULAR_INFER_STAGE = StageSpec(
    key="infer",
    parameters=TABULAR_INFER_PARAMETERS,
    output_artifacts=(
        _artifact("predictions"),
        _artifact("schema_check_summary"),
        _artifact("prediction_summary"),
        _artifact("prediction_preview"),
        _artifact("prediction_distribution"),
        _artifact("manifest"),
    ),
)

TABULAR_STAGES = (
    TABULAR_PREPROCESS_STAGE,
    TABULAR_TRAIN_STAGE,
    TABULAR_ENSEMBLE_STAGE,
    TABULAR_EVALUATE_STAGE,
    TABULAR_INFER_STAGE,
)
TABULAR_PIPELINE_TASK = TaskSpec(
    key="tabular_pipeline",
    parameters=TABULAR_PIPELINE_PARAMETERS,
)
TABULAR_STAGE_TASK = TaskSpec(
    key="tabular_stage",
    parameters=TABULAR_STAGE_TASK_PARAMETERS,
)
TABULAR_INFER_TASK = TaskSpec(
    key="tabular_infer",
    parameters=TABULAR_INFER_PARAMETERS,
)
TABULAR_MANIFEST = PackageManifest(
    version=TABULAR_MANIFEST_VERSION,
    tasks=(TABULAR_PIPELINE_TASK, TABULAR_STAGE_TASK, TABULAR_INFER_TASK),
    stages=TABULAR_STAGES,
)


def get_tabular_manifest() -> PackageManifest:
    return TABULAR_MANIFEST
