from __future__ import annotations

import json
from typing import Any

from ml_platform_core.value_coercion import as_bool, as_candidates, as_dict, as_str_list

from param_keys import (
    BOOL_PARAM_KEYS,
    CANDIDATE_PARAM_KEYS,
    DICT_PARAM_KEYS,
    FLOAT_PARAM_KEYS,
    INT_PARAM_KEYS,
    LIST_PARAM_KEYS,
)


def normalize_clearml_param_value(value: Any) -> Any:
    """Serialize composite values for ClearML parameter transport."""
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return value


PARAM_VALUE_COERCERS = (
    (BOOL_PARAM_KEYS, as_bool),
    (INT_PARAM_KEYS, int),
    (FLOAT_PARAM_KEYS, float),
    (LIST_PARAM_KEYS, as_str_list),
    (DICT_PARAM_KEYS, as_dict),
    (CANDIDATE_PARAM_KEYS, as_candidates),
)


def _coerce_connected_value(key: str, value: Any) -> Any:
    if value is None or value == "":
        return value
    for keys, coercer in PARAM_VALUE_COERCERS:
        if key in keys:
            return coercer(value)
    return value


def coerce_connected_params(raw_params: dict[str, Any]) -> dict[str, Any]:
    """Return canonical ClearML parameter keys with transport values decoded."""
    connected: dict[str, Any] = {}
    for raw_key, value in raw_params.items():
        connected[raw_key] = _coerce_connected_value(raw_key, value)
    return connected


def group_connected_params(params: dict[str, Any]) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for key, value in params.items():
        group, name = key.split("/", 1)
        groups.setdefault(group, {})[name] = value
    return groups


def prefixed_connected_params(params: dict[str, Any], *, prefix: str) -> dict[str, Any]:
    return {f"{prefix}{key}": value for key, value in params.items()}


def connected_params_from_task(
    defaults: dict[str, Any],
    task_params: dict[str, Any],
    *,
    prefix: str = "Args/",
) -> dict[str, Any]:
    """Read ClearML task values, preferring prefixed New Run values."""
    connected = dict(defaults)
    for key in defaults:
        if key in task_params:
            connected[key] = task_params[key]
        prefixed_key = f"{prefix}{key}"
        if prefixed_key in task_params:
            connected[key] = task_params[prefixed_key]
    return coerce_connected_params(connected)
