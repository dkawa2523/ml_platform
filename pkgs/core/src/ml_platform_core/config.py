from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from .config_validation import validate_run_config

OverrideInput = list[str] | dict[str, Any] | None


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML file as a mapping.

    The platform deliberately keeps configuration small: one task file plus one profile file.
    Hydra can be introduced later, but only when this simple axis becomes insufficient.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    return data


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge dicts recursively without mutating inputs.

    Values from ``override`` win. Lists are replaced, not merged, because list merge rules are
    hard to reason about from ClearML UI parameters.
    """
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def coerce_value(raw: str) -> Any:
    """Coerce a CLI override value into YAML-like Python values."""
    text = raw.strip()
    if text == "":
        return None
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError:
        return raw


def set_by_dotted_path(mapping: dict[str, Any], dotted_path: str, value: Any) -> None:
    """Set ``a.b.c`` inside a nested mapping."""
    if not dotted_path or dotted_path.startswith(".") or dotted_path.endswith(".") or ".." in dotted_path:
        raise ValueError(f"Invalid override path: {dotted_path!r}")

    cursor = mapping
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        existing = cursor.get(part)
        if existing is None:
            existing = {}
            cursor[part] = existing
        if not isinstance(existing, dict):
            raise ValueError(f"Cannot set {dotted_path!r}; {part!r} is not a mapping.")
        cursor = existing
    cursor[parts[-1]] = value


def parse_overrides(overrides: list[str] | None) -> dict[str, Any]:
    """Parse CLI overrides into a nested dict.

    Examples:
    - ``model.name=ridge`` -> ``{"model": {"name": "ridge"}}``
    - ``data.feature_columns=[x1, x2]`` -> ``{"data": {"feature_columns": ["x1", "x2"]}}``
    """
    result: dict[str, Any] = {}
    for item in overrides or []:
        if "=" not in item:
            raise ValueError(f"Override must be KEY=VALUE: {item}")
        key, raw_value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Override key must not be empty: {item}")
        set_by_dotted_path(result, key, coerce_value(raw_value))
    return result


def apply_overrides(cfg: dict[str, Any], overrides: OverrideInput) -> dict[str, Any]:
    """Apply CLI or nested-dict overrides and return a copy.

    For CLI list overrides, each dotted path replaces the target value exactly.
    This allows ``--set model.params={}`` to clear model-specific defaults.
    For nested dict overrides, values are deep-merged.
    """
    result = deepcopy(cfg)
    if not overrides:
        return result
    if isinstance(overrides, dict):
        return deep_merge(result, overrides)
    for item in overrides:
        if "=" not in item:
            raise ValueError(f"Override must be KEY=VALUE: {item}")
        key, raw_value = item.split("=", 1)
        set_by_dotted_path(result, key.strip(), coerce_value(raw_value))
    return result


def load_run_config(
    task_path: str | Path, profile_path: str | Path, *, overrides: OverrideInput = None
) -> dict[str, Any]:
    """Load profile then task config.

    Profile is environment information. Task is execution intent. Task values override
    profile values when keys collide. Optional overrides are applied last.
    """
    profile = load_yaml(profile_path)
    task = load_yaml(task_path)
    cfg = deep_merge(profile, task)
    cfg = apply_overrides(cfg, overrides)
    cfg["_meta"] = {
        "task_config": str(task_path),
        "profile_config": str(profile_path),
        "overrides": parse_overrides(overrides) if isinstance(overrides, list) else (overrides or {}),
    }
    validate_run_config(cfg)
    return cfg
