from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ml_platform_core.source_version import git_revision

from .support import script_entry_point

REPO_ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class ExecutionSpec:
    """Immutable source and runtime used by every synced ClearML task."""

    repository: str
    commit: str
    working_dir: str
    image: str
    python_binary: str
    requirements_file: str = "config/requirements/clearml-agent.lock"


def load_execution_spec(profile: dict[str, Any], *, repo_root: Path = REPO_ROOT) -> ExecutionSpec:
    clearml_cfg = profile.get("clearml") or {}
    execution = clearml_cfg.get("execution") or {}
    if not isinstance(execution, dict):
        raise ValueError("clearml.execution must be a mapping.")

    revision = _required_text(execution, "revision")
    return ExecutionSpec(
        repository=_required_text(execution, "repository"),
        commit=_resolve_commit(revision, repo_root),
        working_dir=str(execution.get("working_dir") or "."),
        image=_required_text(execution, "image"),
        python_binary=str(execution.get("python_binary") or "python3.11"),
        requirements_file=str(execution.get("requirements_file") or "config/requirements/clearml-agent.lock"),
    )


def apply_task_execution(task: Any, execution: ExecutionSpec) -> None:
    task.set_base_docker(docker_image=execution.image)
    task.update_parameters(
        {
            "Execution/image": execution.image,
            "Execution/revision": execution.commit,
            "Execution/python": execution.python_binary,
        }
    )


def set_task_script(
    task: Any,
    execution: ExecutionSpec,
    *,
    entry_point: str,
    cli_args: Mapping[str, str | Path],
) -> None:
    task.set_script(
        repository=execution.repository,
        branch="",
        commit=execution.commit,
        diff="",
        working_dir=execution.working_dir,
        entry_point=script_entry_point(entry_point, cli_args),
        binary=execution.python_binary,
    )


def _required_text(mapping: dict[str, Any], key: str) -> str:
    value = str(mapping.get(key) or "").strip()
    if value.startswith("${") and value.endswith("}"):
        variable = value[2:-1]
        value = os.environ.get(variable, "").strip()
        if not value:
            raise ValueError(f"Environment variable {variable} is required by clearml.execution.{key}.")
    if not value:
        raise ValueError(f"clearml.execution.{key} is required.")
    return value


def _resolve_commit(revision: str, repo_root: Path) -> str:
    commit = git_revision(repo_root, revision)
    if commit is None or len(commit) != 40:
        raise ValueError(f"Could not resolve clearml.execution.revision={revision!r} to a git commit.")
    return commit
