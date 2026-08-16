"""Resolve remote stage artifact URLs into local paths."""

from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

ArtifactPathResolver = Callable[[str | Path | None], str | None]


def resolve_stage_inputs_config(
    cfg: dict[str, Any],
    resolve_artifact_path: ArtifactPathResolver,
) -> dict[str, Any]:
    resolved = deepcopy(cfg)
    if "stage_inputs" not in resolved:
        return resolved
    resolved["stage_inputs"] = {
        key: _resolve_value(value, resolve_artifact_path) for key, value in (resolved.get("stage_inputs") or {}).items()
    }
    return resolved


def _resolve_value(value: Any, resolve_artifact_path: ArtifactPathResolver) -> Any:
    value = _decode_json(value)
    if isinstance(value, dict):
        return {key: _resolve_value(item, resolve_artifact_path) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_value(item, resolve_artifact_path) for item in value]
    if isinstance(value, str) and "://" in value.strip():
        return resolve_artifact_path(value)
    return value


def _decode_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not (text.startswith("{") or text.startswith("[")):
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value
