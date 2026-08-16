from __future__ import annotations

import json
from typing import Any

from ml_platform_core.value_coercion import as_bool, as_candidates, as_dict, as_str_list

from .param_bindings import keys_with_type


def normalize_clearml_param_value(value: Any) -> Any:
    """Serialize composite values for ClearML parameter transport."""
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return value


PARAM_VALUE_COERCERS = (
    (keys_with_type("bool"), as_bool),
    (keys_with_type("int"), int),
    (keys_with_type("float"), float),
    (keys_with_type("list"), as_str_list),
    (keys_with_type("dict"), as_dict),
    (keys_with_type("candidates"), as_candidates),
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
