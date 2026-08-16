"""Environment-configurable trust policy for remotely selected model tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelSourcePolicy:
    allowed_statuses: frozenset[str]
    required_tags: frozenset[str]
    allowed_run_types: frozenset[str]
    allowed_projects: frozenset[str]

    def validate(self, *, status: str, tags: set[str], project: str) -> None:
        if status not in self.allowed_statuses:
            allowed = " or ".join(sorted(self.allowed_statuses))
            raise ValueError(f"Model source task must be {allowed}, got: {status or 'unknown'}.")
        if not self.required_tags.issubset(tags) or not any(
            f"run_type:{run_type}" in tags for run_type in self.allowed_run_types
        ):
            raise ValueError("Model source task does not satisfy the configured platform tags.")
        if self.allowed_projects and project not in self.allowed_projects:
            raise ValueError(f"Model source task is outside configured ClearML run projects: {project!r}.")


def model_source_policy(cfg: dict[str, Any]) -> ModelSourcePolicy:
    clearml_cfg = cfg.get("clearml") or {}
    raw = clearml_cfg.get("model_source") or {}
    projects = clearml_cfg.get("projects") or {}
    project_keys = _string_values(raw, "project_keys", ["train", "ensemble", "evaluate", "stages"])
    return ModelSourcePolicy(
        allowed_statuses=frozenset(_string_values(raw, "allowed_statuses", ["completed", "published"])),
        required_tags=frozenset(_string_values(raw, "required_tags", ["domain:tabular"])),
        allowed_run_types=frozenset(_string_values(raw, "allowed_run_types", ["stage", "pipeline"])),
        allowed_projects=frozenset(str(projects[key]) for key in project_keys if projects.get(key)),
    )


def _string_values(mapping: Any, key: str, default: list[str]) -> list[str]:
    values = mapping.get(key, default) if isinstance(mapping, dict) else default
    if not isinstance(values, list) or not all(isinstance(value, str) and value.strip() for value in values):
        raise ValueError(f"clearml.model_source.{key} must be a list of non-empty strings.")
    return [value.strip().lower() if key != "required_tags" else value.strip() for value in values]
