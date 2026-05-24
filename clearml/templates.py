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
from pipelines import pipeline_ui_params


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


def _entry_command(entry_point: str, task_config: str, profile_path: str | Path) -> str:
    return f"{entry_point} --task {task_config} --profile {Path(profile_path).as_posix()}"


def _remote_packages() -> list[str]:
    requirements = REPO_ROOT / "requirements.txt"
    packages = [line.strip() for line in requirements.read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")]
    if not any(line.split("=", 1)[0].split("<", 1)[0].split(">", 1)[0].strip().lower() == "clearml" for line in packages):
        packages.append("clearml==2.1.7")
    return packages


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
    entry_command = _entry_command(entry_point, task_config, profile_path)
    common = {
        "repository": repository,
        "branch": branch,
        "working_dir": working_dir,
        "entry_point": entry_command,
    }
    try:
        task.set_script(**common, arguments={"--task": task_config, "--profile": str(profile_path)})
    except TypeError:  # pragma: no cover - depends on ClearML SDK version
        try:
            task.set_script(**common, args=f"--task {task_config} --profile {profile_path}")
        except TypeError:
            task.set_script(**common)


def _find_editable_template(Task: Any, project_name: str, task_name: str):
    tasks = Task.get_tasks(project_name=project_name, task_name=task_name, allow_archived=False)
    editable = [task for task in tasks if getattr(task, "status", None) == "created"]
    return editable[-1] if editable else None


def _sync_template_task(
    Task: Any,
    *,
    project_name: str,
    task_name: str,
    task_type: Any,
    repository: str,
    branch: str,
    working_dir: str,
    entry_point: str,
    task_config: str,
    profile_path: str | Path,
    params: dict[str, Any],
):
    profile_arg = Path(profile_path).as_posix()
    task = _find_editable_template(Task, project_name, task_name)
    if task is None:
        task = Task.create(
            project_name=project_name,
            task_name=task_name,
            task_type=task_type,
            repo=repository,
            branch=branch,
            script=_entry_command(entry_point, task_config, profile_arg),
            working_directory=working_dir,
            packages=_remote_packages(),
            add_task_init_call=False,
        )
    else:
        _set_script_with_compat(
            task,
            repository=repository,
            branch=branch,
            working_dir=working_dir,
            entry_point=entry_point,
            task_config=task_config,
            profile_path=profile_arg,
        )
    task.update_parameters(params)
    task.delete_parameter("Args/task", force=True)
    task.delete_parameter("Args/profile", force=True)
    task.set_packages(_remote_packages())
    return task


def _task_args(task_config: str, profile_path: str | Path) -> str:
    return f"--task {task_config} --profile {Path(profile_path).as_posix()}"


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
            ui_params = pipeline_ui_params(task_config, profile_path) if task_name == "tabular_pipeline_template" else default_ui_params(cfg)
            params = ", ".join(ui_params)
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
        entry_point = _entry_point(task_name)
        params = pipeline_ui_params(task_config, profile_path) if task_name == "tabular_pipeline_template" else default_ui_params(cfg)
        task = _sync_template_task(
            Task,
            project_name=project_name,
            task_name=task_name,
            task_type=_task_type(Task, task_type_name),
            repository=repository,
            branch=branch,
            working_dir=working_dir,
            entry_point=entry_point,
            task_config=task_config,
            profile_path=profile_path,
            params=params,
        )
        print(f"Synced template: {project_name}/{task_name} id={task.id} ({_template_note(task_name)})")
