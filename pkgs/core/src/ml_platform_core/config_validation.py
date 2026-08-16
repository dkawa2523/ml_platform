from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .stages import as_stage_name


class ConfigValidationError(ValueError):
    """Raised when a merged run configuration has an invalid public value."""


_SECTIONS = (
    "runtime",
    "run",
    "data",
    "split",
    "metrics",
    "features",
    "model",
    "output",
    "clearml",
    "logging",
    "basic",
    "stage_inputs",
    "_meta",
)

_STRING_FIELDS = (
    "profile",
    "runtime.output_dir",
    "run.name",
    "data.local_path",
    "data.clearml_dataset_id",
    "data.dataset_file",
    "data.source_manifest",
    "data.target_column",
    "data.base_dir",
    "split.method",
    "split.group_column",
    "split.time_column",
    "split.valid_filter_column",
    "split.valid_filter_value",
    "features.preset",
    "features.numeric_impute_strategy",
    "features.categorical_impute_strategy",
    "features.categorical_encoder",
    "features.scaling",
    "model.name",
    "model.selection_metric",
    "model.source_type",
    "model.source_task_id",
    "model.model_selector",
    "model.local_model_path",
    "model.artifact_path",
    "model.info_path",
    "output.prediction_name",
)

_LIST_FIELDS = (
    "data.feature_columns",
    "data.id_columns",
    "metrics.names",
    "features.drop_columns",
    "features.passthrough_columns",
    "model.ensemble.methods",
)

_MAPPING_FIELDS = (
    "features.params",
    "model.params",
    "model.ensemble",
)


def validate_run_config(config: Mapping[str, Any]) -> None:
    """Validate the small external configuration boundary without reshaping it."""
    if not isinstance(config, Mapping):
        raise ConfigValidationError("run config must be a mapping.")
    _validate_task(config)
    _validate_sections(config)
    _validate_declared_fields(config)
    _validate_scalars(config)


def _validate_task(config: Mapping[str, Any]) -> None:
    task = config.get("task")
    if not isinstance(task, str) or not task.strip():
        raise ConfigValidationError("task must be a non-empty string.")


def _validate_sections(config: Mapping[str, Any]) -> None:
    for name in _SECTIONS:
        value = config.get(name)
        if value is not None and not isinstance(value, Mapping):
            raise ConfigValidationError(f"{name} must be a mapping.")


def _validate_declared_fields(config: Mapping[str, Any]) -> None:
    for path in _STRING_FIELDS:
        _require_type(config, path, str, "a string")

    for path in _LIST_FIELDS:
        value = _get(config, path)
        if value is not None and not isinstance(value, (str, list, tuple)):
            raise ConfigValidationError(f"{path} must be a list, comma string, or null.")

    for path in _MAPPING_FIELDS:
        _require_type(config, path, Mapping, "a mapping")


def _validate_scalars(config: Mapping[str, Any]) -> None:
    _require_type(config, "runtime.use_clearml", bool, "a boolean")
    _require_type(config, "output.upload_plots", bool, "a boolean")
    _require_type(config, "model.ensemble.enabled", bool, "a boolean")
    _require_int(config, "run.seed")
    _require_int(config, "model.ensemble.top_k")
    _require_int(config, "features.max_dense_cells")
    _validate_stage(config)
    _validate_fraction(config, "split.valid_size")
    _validate_fraction(config, "split.selection_size")
    _validate_top_k(config)


def _validate_stage(config: Mapping[str, Any]) -> None:
    stage = _get(config, "run.stage")
    if stage is None:
        return
    if not isinstance(stage, str):
        raise ConfigValidationError("run.stage must be a string or null.")
    try:
        as_stage_name(stage)
    except ValueError as exc:
        raise ConfigValidationError(str(exc)) from exc


def _validate_fraction(config: Mapping[str, Any], path: str) -> None:
    value = _get(config, path)
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigValidationError(f"{path} must be a number or null.")
    if not 0 < float(value) < 1:
        raise ConfigValidationError(f"{path} must be between 0 and 1.")


def _validate_top_k(config: Mapping[str, Any]) -> None:
    top_k = _get(config, "model.ensemble.top_k")
    if top_k is not None and top_k < 1:
        raise ConfigValidationError("model.ensemble.top_k must be at least 1.")
    max_dense_cells = _get(config, "features.max_dense_cells")
    if max_dense_cells is not None and max_dense_cells < 1:
        raise ConfigValidationError("features.max_dense_cells must be at least 1.")


def _require_type(config: Mapping[str, Any], path: str, expected: type, description: str) -> None:
    value = _get(config, path)
    if value is not None and not isinstance(value, expected):
        raise ConfigValidationError(f"{path} must be {description} or null.")


def _require_int(config: Mapping[str, Any], path: str) -> None:
    value = _get(config, path)
    if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
        raise ConfigValidationError(f"{path} must be an integer or null.")


def _get(config: Mapping[str, Any], path: str) -> Any:
    value: Any = config
    for key in path.split("."):
        if not isinstance(value, Mapping) or key not in value:
            return None
        value = value[key]
    return value
