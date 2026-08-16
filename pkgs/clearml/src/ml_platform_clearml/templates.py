from __future__ import annotations

from pathlib import Path
from typing import Any

from ml_platform_core.config import load_run_config, load_yaml

from .adapter import clearml_projects, clearml_template_name, import_clearml_sdk, validate_clearml_runtime
from .execution import ExecutionSpec, apply_task_execution, load_execution_spec, set_task_script
from .pipeline_controller import sync_pipeline_draft
from .pipeline_params import pipeline_runtime_params
from .pipeline_plan import build_pipeline_plan
from .support import delete_task, script_args, script_entry_point
from .template_spec import (
    PIPELINE_TEMPLATES,
    TASK_TEMPLATES,
    apply_task_metadata,
    entry_point,
    remote_packages,
    task_runtime_params,
    task_type,
    template_note,
    template_tags,
)

REPO_ROOT = Path(__file__).resolve().parents[4]


def _find_editable_template(Task: Any, project_name: str, task_name: str):
    tasks = Task.get_tasks(project_name=project_name, task_name=task_name, allow_archived=False)
    editable = [task for task in tasks if getattr(task, "status", None) == "created"]
    return editable[-1] if editable else None


def _delete_stale_created_templates(Task: Any, project_name: str, task_name: str, keep_id: str) -> None:
    for task in Task.get_tasks(project_name=project_name, task_name=task_name, allow_archived=True):
        if task.id == keep_id or getattr(task, "status", None) != "created":
            continue
        delete_task(task)


def _sync_template_task(
    Task: Any,
    *,
    project_name: str,
    task_name: str,
    task_type: Any,
    execution: ExecutionSpec,
    entry_point: str,
    task_config: str,
    profile_path: str | Path,
    params: dict[str, Any],
    packages: list[str],
):
    profile_arg = Path(profile_path).as_posix()
    task = _find_editable_template(Task, project_name, task_name)
    if task is None:
        task = Task.create(
            project_name=project_name,
            task_name=task_name,
            task_type=task_type,
            repo=execution.repository,
            branch="",
            commit=execution.commit,
            script=script_entry_point(entry_point, _cli_args(task_config, profile_arg)),
            working_directory=execution.working_dir,
            packages=packages,
            add_task_init_call=False,
            binary=execution.python_binary,
        )
    else:
        set_task_script(
            task,
            execution,
            entry_point=entry_point,
            cli_args=_cli_args(task_config, profile_arg),
        )
    _replace_template_params(task, params, packages)
    return task


def _replace_template_params(task: Any, params: dict[str, Any], packages: list[str]) -> None:
    for key in list(task.get_parameters() or {}):
        if key.startswith("Model/params/") or key.startswith("Model/candidates/"):
            task.delete_parameter(key, force=True)
    task.update_parameters(params)
    task.delete_parameter("Args/task", force=True)
    task.delete_parameter("Args/profile", force=True)
    task.set_packages(packages)


def _cli_args(task_config: str, profile_path: str | Path) -> dict[str, str]:
    return {"--task": task_config, "--profile": str(profile_path)}


def _template_sync_settings(profile_path: str | Path) -> dict[str, Any]:
    profile = load_yaml(profile_path)
    clearml_cfg = profile.get("clearml", {})
    projects = clearml_projects(clearml_cfg)
    execution = load_execution_spec(profile)
    return {
        "profile_path": profile_path,
        "clearml_cfg": clearml_cfg,
        "project_name": projects["templates"],
        "pipeline_project_name": projects["pipelines"],
        "execution": execution,
        "packages": remote_packages(execution.requirements_file),
    }


def sync_templates(profile_path: str | Path, *, dry_run: bool = False) -> None:
    """Register minimal ClearML template tasks and Pipeline-tab drafts."""
    settings = _template_sync_settings(profile_path)
    if dry_run:
        _dry_run_templates(settings)
        return
    validate_clearml_runtime(require_automation=True)
    clearml_sdk = import_clearml_sdk()
    _sync_task_templates(clearml_sdk.Task, settings)
    _sync_pipeline_templates(settings)


def _dry_run_templates(settings: dict[str, Any]) -> None:
    for task_name, task_config, task_type_name in TASK_TEMPLATES:
        _print_task_template_dry_run(settings, task_name, task_config, task_type_name)
    for task_name, task_config, task_type_name in PIPELINE_TEMPLATES:
        _print_pipeline_template_dry_run(settings, task_name, task_config, task_type_name)


def _print_task_template_dry_run(
    settings: dict[str, Any], task_name: str, task_config: str, task_type_name: str
) -> None:
    cfg = load_run_config(task_config, settings["profile_path"])
    runtime_params = task_runtime_params(task_name, cfg)
    task_entry_point = entry_point(task_name)
    execution = settings["execution"]
    print(
        "DRY-RUN template: "
        f"project={settings['project_name']} "
        f"name={clearml_template_name(task_name)} "
        f"type={task_type_name} "
        f"repository={execution.repository} "
        f"revision={execution.commit} "
        f"working_dir={execution.working_dir} "
        f"execution_image={execution.image} "
        f"python={execution.python_binary} "
        f"requirements={execution.requirements_file} "
        f"entry_point={task_entry_point} "
        f'args="{script_args(_cli_args(task_config, settings["profile_path"]))}" '
        f"params=[{', '.join(runtime_params)}] "
        f"tags={template_tags(task_name)} "
        f'note="{template_note(task_name, execution)}"'
    )


def _print_pipeline_template_dry_run(
    settings: dict[str, Any], task_name: str, task_config: str, task_type_name: str
) -> None:
    runtime_params = pipeline_runtime_params(task_config, settings["profile_path"])
    plan = build_pipeline_plan(
        task_path=task_config,
        profile_path=settings["profile_path"],
        runtime_params=runtime_params,
    )
    execution = settings["execution"]
    print(
        "DRY-RUN pipeline template: "
        f"project={plan['project']} "
        f"name={clearml_template_name(task_name)} "
        f"type={task_type_name} "
        f"repository={execution.repository} "
        f"revision={execution.commit} "
        f"working_dir={execution.working_dir} "
        f"execution_image={execution.image} "
        f"python={execution.python_binary} "
        f"requirements={execution.requirements_file} "
        f"entry_point={entry_point(task_name)} "
        f'args="{script_args(_cli_args(task_config, settings["profile_path"]))}" '
        f"params=[{', '.join(runtime_params)}] "
        f"steps={' -> '.join(step['name'] for step in plan['steps'])} "
        f"tags={template_tags(task_name)} "
        f'note="{template_note(task_name, execution)}"'
    )


def _sync_task_templates(Task: Any, settings: dict[str, Any]) -> None:
    for task_name, task_config, task_type_name in TASK_TEMPLATES:
        cfg = load_run_config(task_config, settings["profile_path"])
        task_entry_point = entry_point(task_name)
        params = task_runtime_params(task_name, cfg)
        display_name = clearml_template_name(task_name)
        task = _sync_template_task(
            Task,
            project_name=settings["project_name"],
            task_name=display_name,
            task_type=task_type(Task, task_type_name),
            execution=settings["execution"],
            entry_point=task_entry_point,
            task_config=task_config,
            profile_path=settings["profile_path"],
            params=params,
            packages=settings["packages"],
        )
        apply_task_execution(task, settings["execution"])
        apply_task_metadata(task, task_name, settings["execution"])
        _delete_stale_created_templates(Task, settings["project_name"], display_name, task.id)
        print(
            f"Synced template: {settings['project_name']}/{display_name} "
            f"id={task.id} revision={settings['execution'].commit} image={settings['execution'].image} "
            f"({template_note(task_name, settings['execution'])})"
        )


def _sync_pipeline_templates(settings: dict[str, Any]) -> None:
    for task_name, task_config, _ in PIPELINE_TEMPLATES:
        task = sync_pipeline_draft(
            task_path=task_config,
            profile_path=settings["profile_path"],
            template_name=task_name,
            execution=settings["execution"],
            packages=settings["packages"],
        )
        print(
            "Synced pipeline template: "
            f"{settings['pipeline_project_name']}/{clearml_template_name(task_name)} "
            f"id={task.id} revision={settings['execution'].commit} image={settings['execution'].image} "
            f"({template_note(task_name, settings['execution'])})"
        )
