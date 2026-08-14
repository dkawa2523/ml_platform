from __future__ import annotations

import json
from typing import Any


def as_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"", "none", "null"}:
            return default
        if text in {"1", "true", "yes", "y", "on"}:
            return True
        if text in {"0", "false", "no", "n", "off"}:
            return False
        raise ValueError(f"Cannot convert value to boolean: {value!r}")
    return bool(value)


def as_str_list(value: Any) -> list[str] | None:
    if value is None or value == "":
        return None
    if isinstance(value, (list, tuple, set)):
        return _stringified_sequence(value)
    if isinstance(value, str):
        return _stringified_text_list(value)
    raise ValueError(f"Cannot convert value to list: {value!r}")


def _stringified_sequence(value: list[Any] | tuple[Any, ...] | set[Any]) -> list[str]:
    return [str(item) for item in value]


def _stringified_text_list(value: str) -> list[str] | None:
    text = value.strip()
    if not text:
        return None
    parsed = _json_list(text)
    if parsed is not None:
        return _stringified_sequence(parsed)
    return _comma_separated_list(text)


def _json_list(text: str) -> list[Any] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, list) else None


def _comma_separated_list(text: str) -> list[str]:
    return [item.strip() for item in text.split(",") if item.strip()]


def as_dict(value: Any) -> dict[str, Any]:
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        return _dict_from_text(value)
    raise ValueError(f"Cannot convert value to dict: {value!r}")


def _dict_from_text(value: str) -> dict[str, Any]:
    text = value.strip()
    if not text:
        return {}
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected JSON object, got: {value!r}")
    return parsed


def as_candidates(value: Any) -> list[Any]:
    return [_candidate_item(index, item) for index, item in enumerate(_candidate_items(value))]


def _candidate_items(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    parsed = _json_candidate_items(value) if isinstance(value, str) else value
    if not isinstance(parsed, list):
        raise ValueError(f"Expected JSON array for candidates, got: {value!r}")
    return parsed


def _json_candidate_items(value: str) -> list[Any]:
    text = value.strip()
    return [] if not text else json.loads(text)


def _candidate_item(index: int, item: Any) -> Any:
    if isinstance(item, str):
        text = item.strip()
        if not text:
            raise ValueError(f"Model/candidates[{index}] must not be empty.")
        return text
    if isinstance(item, dict):
        return dict(item)
    raise ValueError(f"Model/candidates[{index}] must be a model name or object.")
