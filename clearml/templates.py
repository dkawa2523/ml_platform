from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CLEARML_DIR = Path(__file__).resolve().parent
for p in (str(CLEARML_DIR), str(REPO_ROOT / "pkgs/core/src"), str(REPO_ROOT / "pkgs/tabular/src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from adapter import default_ui_params, import_clearml_sdk
from ml_platform_core.config import load_run_config, load_yaml


TEMPLATES = [
    ("tabular_train_template", "config/tasks/tabular_train.yaml", "training"),
    ("tabular_eval_template", "config/tasks/tabular_eval.yaml", "testing"),
    ("tabular_infer_template", "config/tasks/tabular_infer.yaml", "inference"),
    ("tabular_pipeline_template", "config/tasks/tabular_pipeline.yaml", "controller"),
]


def _task_type(Task: Any, name: str):
    return getattr(Task.TaskTypes, name, getattr(Task.TaskTypes, "training", None))


def _template_note(task_name: str) -> str:
    if task_name == "tabular_pipeline_template":
        return "Phase 3 PipelineController entrypoint"
    return "Phase 2 clone-run target"


def _entry_point(task_name: str) -> str:
    if task_name == "tabular_pipeline_template":
        return "clearml/pipelines.py"
    return "clearml/app.py"


def _set_script_with_compat(
    task: Any,
    *,
    repository: str,
    branch: str,
    working_dir: str,
    entry_point: str,
    task_config: str,
    profile_path: str | Path,
) -> None:
    common = {
        "repository": repository,
        "branch": branch,
        "working_dir": working_dir,
        "entry_point": entry_point,
    }
    try:
        task.set_script(**common, arguments={"--task": task_config, "--profile": str(profile_path)})
    except TypeError:  # pragma: no cover - depends on ClearML SDK version
        task.set_script(**common, args=f"--task {task_config} --profile {profile_path}")


def _task_args(task_config: str, profile_path: str | Path) -> str:
    return f"--task {task_config} --profile {profile_path}"


def sync_templates(profile_path: str | Path, *, dry_run: bool = False) -> None:
    """Register minimal ClearML template tasks.

    Keep templates few. Do not create one template per model or per dataset.
    """
    profile = load_yaml(profile_path)
    clearml_cfg = profile.get("clearml", {})
    project_name = clearml_cfg.get("project_root", "MLPlatform/Dev") + "/Templates"
    repository = clearml_cfg.get("repository", ".")
    branch = clearml_cfg.get("branch", "main")
    working_dir = clearml_cfg.get("working_dir", ".")

    if dry_run:
        for task_name, task_config, task_type_name in TEMPLATES:
            cfg = load_run_config(task_config, profile_path)
            params = ", ".join(default_ui_params(cfg))
            entry_point = _entry_point(task_name)
            print(
                "DRY-RUN template: "
                f"project={project_name} "
                f"name={task_name} "
                f"type={task_type_name} "
                f"repository={repository} "
                f"branch={branch} "
                f"working_dir={working_dir} "
                f"entry_point={entry_point} "
                f"args=\"{_task_args(task_config, profile_path)}\" "
                f"params=[{params}] "
                f"note=\"{_template_note(task_name)}\""
            )
        return

    clearml_sdk = import_clearml_sdk()
    Task = clearml_sdk.Task

    for task_name, task_config, task_type_name in TEMPLATES:
        cfg = load_run_config(task_config, profile_path)
        task = Task.init(project_name=project_name, task_name=task_name, task_type=_task_type(Task, task_type_name))
        task.connect(default_ui_params(cfg))
        entry_point = _entry_point(task_name)
        _set_script_with_compat(
            task,
            repository=repository,
            branch=branch,
            working_dir=working_dir,
            entry_point=entry_point,
            task_config=task_config,
            profile_path=profile_path,
        )
        task.close()
        print(f"Synced template: {project_name}/{task_name} ({_template_note(task_name)})")
