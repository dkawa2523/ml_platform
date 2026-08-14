from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
from typing import Any

from support import script_entry_point


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ExecutionSpec:
    """Immutable source and runtime used by every synced ClearML task."""

    repository: str
    commit: str
    working_dir: str
    image: str
    python_binary: str


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
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{revision}^{{commit}}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    commit = result.stdout.strip()
    if result.returncode or len(commit) != 40:
        raise ValueError(f"Could not resolve clearml.execution.revision={revision!r} to a git commit.")
    return commit
