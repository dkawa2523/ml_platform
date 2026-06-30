from __future__ import annotations

BOOL_PARAM_KEYS = {
    "Basic/use_ensemble",
    "Model/ensemble_enabled",
    "Output/upload_plots",
}
INT_PARAM_KEYS = {
    "Run/seed",
    "Model/ensemble_top_k",
    "Output/chunk_size",
}
FLOAT_PARAM_KEYS = {
    "Split/valid_size",
}
LIST_PARAM_KEYS = {
    "Input/feature_columns",
    "Input/id_columns",
    "Model/evaluation_metrics",
    "Model/ensemble_methods",
    "Features/drop_columns",
    "Features/passthrough_columns",
}
DICT_PARAM_KEYS = {
    "Model/model_params_by_name",
    "Model/params",
}
CANDIDATE_PARAM_KEYS = {
    "Model/candidates",
}
DATA_INPUT_KEYS = {
    "Input/local_path",
    "Input/clearml_dataset_id",
    "Input/dataset_file",
    "Input/target_column",
    "Input/feature_columns",
    "Input/id_columns",
}

SPLIT_PARAM_TO_CONFIG = {
    "Split/method": "method",
    "Split/group_column": "group_column",
    "Split/time_column": "time_column",
    "Split/valid_filter_column": "valid_filter_column",
    "Split/valid_filter_value": "valid_filter_value",
}
DATA_PARAM_TO_CONFIG = (
    ("Input/clearml_dataset_id", "clearml_dataset_id"),
    ("Input/dataset_file", "dataset_file"),
    ("Input/target_column", "target_column"),
)
MODEL_SOURCE_PARAM_TO_CONFIG = (
    ("Model/source_type", "source_type"),
    ("Model/source_task_id", "source_task_id"),
    ("Model/model_selector", "model_selector"),
    ("Model/local_model_path", "local_model_path"),
    ("Model/feature_spec_path", "feature_spec_path"),
    ("Model/preprocess_bundle_path", "preprocess_bundle_path"),
    ("Model/info_path", "info_path"),
)
FEATURE_PARAM_TO_CONFIG = (
    ("Features/preset", "preset"),
    ("Features/numeric_impute_strategy", "numeric_impute_strategy"),
    ("Features/categorical_impute_strategy", "categorical_impute_strategy"),
    ("Features/categorical_encoder", "categorical_encoder"),
    ("Features/scaling", "scaling"),
)

MODEL_SOURCE_DEFAULT_KEYS = (
    "source_type",
    "source_task_id",
    "model_selector",
    "local_model_path",
    "feature_spec_path",
    "preprocess_bundle_path",
)
FEATURE_DEFAULT_KEYS = (
    "preset",
    "numeric_impute_strategy",
    "categorical_impute_strategy",
    "categorical_encoder",
    "scaling",
    "drop_columns",
    "passthrough_columns",
)
