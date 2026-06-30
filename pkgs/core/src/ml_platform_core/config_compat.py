from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from .config_models import (
    DataConfig,
    EnsembleConfig,
    FeaturesConfig,
    MetricsConfig,
    ModelConfig,
    OutputConfig,
    RunConfig,
    RunSectionConfig,
    RuntimeConfig,
    SplitConfig,
)


def get_present_sections(config: RunConfig) -> frozenset[str]:
    return frozenset(config.present_sections)


def runtime_to_legacy_dict(config: RuntimeConfig) -> dict[str, Any]:
    return {"output_dir": config.output_dir, "use_clearml": config.use_clearml, **deepcopy(config.extras)}


def run_section_to_legacy_dict(config: RunSectionConfig) -> dict[str, Any]:
    data = deepcopy(config.extras)
    if config.name is not None:
        data["name"] = config.name
    if config.seed is not None:
        data["seed"] = config.seed
    if config.stage is not None:
        data["stage"] = config.stage
    return data


def data_to_legacy_dict(config: DataConfig) -> dict[str, Any]:
    data = deepcopy(config.extras)
    for key in ("local_path", "clearml_dataset_id", "dataset_file", "target_column", "feature_columns", "base_dir"):
        value = getattr(config, key)
        if value is not None:
            data[key] = deepcopy(value)
    data["id_columns"] = list(config.id_columns)
    return data


def split_to_legacy_dict(config: SplitConfig) -> dict[str, Any]:
    return {
        "method": config.method,
        "valid_size": config.valid_size,
        "group_column": config.group_column,
        "time_column": config.time_column,
        "valid_filter_column": config.valid_filter_column,
        "valid_filter_value": config.valid_filter_value,
        **deepcopy(config.extras),
    }


def metrics_to_legacy_dict(config: MetricsConfig) -> dict[str, Any]:
    data = deepcopy(config.extras)
    if config.names is not None:
        data["names"] = deepcopy(config.names)
    return data


def features_to_legacy_dict(config: FeaturesConfig) -> dict[str, Any]:
    return {
        "preset": config.preset,
        "numeric_impute_strategy": config.numeric_impute_strategy,
        "categorical_impute_strategy": config.categorical_impute_strategy,
        "categorical_encoder": config.categorical_encoder,
        "scaling": config.scaling,
        "drop_columns": list(config.drop_columns),
        "passthrough_columns": list(config.passthrough_columns),
        "params": deepcopy(config.params),
        **deepcopy(config.extras),
    }


def ensemble_to_legacy_dict(config: EnsembleConfig) -> dict[str, Any]:
    return {
        "enabled": config.enabled,
        "methods": list(config.methods),
        "method": config.method,
        "top_k": config.top_k,
        **deepcopy(config.extras),
    }


def model_to_legacy_dict(config: ModelConfig) -> dict[str, Any]:
    data = deepcopy(config.extras)
    data.update(
        {
            key: value
            for key, value in {
                "name": config.name,
                "selection_metric": config.selection_metric,
                "source_type": config.source_type,
                "source_task_id": config.source_task_id,
                "model_selector": config.model_selector,
                "local_model_path": config.local_model_path,
                "artifact_path": config.artifact_path,
                "info_path": config.info_path,
                "feature_spec_path": config.feature_spec_path,
                "preprocess_bundle_path": config.preprocess_bundle_path,
            }.items()
            if value is not None
        }
    )
    data["params"] = deepcopy(config.params)
    data["candidates"] = deepcopy(config.candidates)
    data["ensemble"] = ensemble_to_legacy_dict(config.ensemble)
    return data


def output_to_legacy_dict(config: OutputConfig) -> dict[str, Any]:
    data = deepcopy(config.extras)
    if config.prediction_name is not None:
        data["prediction_name"] = config.prediction_name
    if config.chunk_size is not None:
        data["chunk_size"] = config.chunk_size
    if config.upload_plots is not None:
        data["upload_plots"] = config.upload_plots
    return data


_SECTION_SERIALIZERS: tuple[tuple[str, Callable[[RunConfig], Any]], ...] = (
    ("runtime", lambda config: runtime_to_legacy_dict(config.runtime)),
    ("run", lambda config: run_section_to_legacy_dict(config.run)),
    ("data", lambda config: data_to_legacy_dict(config.data)),
    ("split", lambda config: split_to_legacy_dict(config.split)),
    ("metrics", lambda config: metrics_to_legacy_dict(config.metrics)),
    ("features", lambda config: features_to_legacy_dict(config.features)),
    ("model", lambda config: model_to_legacy_dict(config.model)),
    ("output", lambda config: output_to_legacy_dict(config.output)),
    ("clearml", lambda config: deepcopy(config.clearml)),
    ("logging", lambda config: deepcopy(config.logging)),
    ("basic", lambda config: deepcopy(config.basic)),
    ("stage_inputs", lambda config: deepcopy(config.stage_inputs)),
    ("_meta", lambda config: deepcopy(config.meta)),
)


def to_legacy_dict(config: RunConfig) -> dict[str, Any]:
    data = deepcopy(config.extras)
    data["task"] = config.task
    present_sections = get_present_sections(config)
    if "profile" in present_sections or config.profile is not None:
        data["profile"] = config.profile
    for section, serializer in _SECTION_SERIALIZERS:
        if section in present_sections:
            data[section] = serializer(config)
    return data
