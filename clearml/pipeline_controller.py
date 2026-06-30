from __future__ import annotations

from pathlib import Path
from typing import Any

from adapter import (
    apply_execution_image,
    clearml_tags,
    clearml_template_name,
    import_clearml_automation,
    import_clearml_sdk,
    import_clearml_symbol,
    validate_clearml_runtime,
)
from ml_platform_core.config import load_yaml

from pipeline_plan import (
    build_pipeline_plan,
    execution_image as profile_execution_image,
    pipeline_arg_params,
    pipeline_params_from_task,
    pipeline_runtime_params,
)


PIPELINE_TEMPLATE_TAGS = clearml_tags("template", user_facing=True)


def sync_pipeline_draft(
    task_path: str | Path = "config/tasks/tabular_pipeline.yaml",
    profile_path: str | Path = "config/profiles/clearml-dev.yaml",
    *,
    template_name: str = "tabular_train_pipeline_template",
    repository: str | None = None,
    branch: str | None = None,
    working_dir: str | None = None,
    packages: list[str] | None = None,
    execution_image: str | None = None,
):
    """Create a Pipeline-tab draft for the stage-based training graph."""
    clearml_sdk = import_clearml_sdk()
    Task = clearml_sdk.Task
    display_name = clearml_template_name(template_name)
    validate_clearml_runtime()
    params = pipeline_runtime_params(task_path, profile_path)
    plan = build_pipeline_plan(task_path=task_path, profile_path=profile_path, runtime_params=params)
    if execution_image is None:
        execution_image = profile_execution_image(load_yaml(profile_path))
    existing = _find_pipeline_draft(Task, plan["project"], display_name)
    # ClearML pipeline drafts persist their step graph separately from normal
    # task parameters. Updating an existing draft can leave New Run parameters
    # current while executing an old graph, so template sync rebuilds the draft.
    if existing is not None:
        _delete_created_pipeline_draft(existing)
    draft_params = {
        **params,
        **pipeline_arg_params(params),
        "pipeline/controller_queue": plan["controller_queue"],
        "pipeline/default_queue": plan["stage_queue"],
    }

    automation = import_clearml_automation()
    PipelineController = automation.PipelineController
    pipe = PipelineController(
        project=plan["project"],
        name=display_name,
        version=plan["version"],
        add_run_number=False,
        target_project=plan["stage_project"],
        repo=repository or ".",
        repo_branch=branch,
        packages=packages,
        working_dir=working_dir or ".",
    )
    _add_pipeline_args(pipe, params)
    _set_pipeline_script_with_compat(
        pipe.task,
        repository=repository or ".",
        branch=branch or "main",
        working_dir=working_dir or ".",
        task_config=task_path,
        profile_path=profile_path,
    )
    pipe.task.update_parameters(draft_params)
    _add_plan_steps(pipe, plan)
    pipe.create_draft()
    pipe.task.update_parameters(draft_params)
    apply_execution_image(pipe.task, execution_image)
    _apply_pipeline_template_metadata(
        pipe.task,
        execution_image,
        controller_queue=plan["controller_queue"],
        stage_queue=plan["stage_queue"],
    )
    _delete_stale_pipeline_drafts(Task, plan["project"], display_name, pipe.task.id)
    _delete_legacy_pipeline_templates(Task, ["tabular_train_pipeline_template"])
    return pipe.task


def register_tabular_pipeline(
    task_path: str | Path = "config/tasks/tabular_pipeline.yaml",
    profile_path: str | Path = "config/profiles/clearml-dev.yaml",
    *,
    overrides: list[str] | dict[str, Any] | None = None,
) -> None:
    """Register and start the stage-based ClearML training pipeline."""
    automation = import_clearml_automation()
    PipelineController = automation.PipelineController
    Task = import_clearml_symbol("Task")
    validate_clearml_runtime()
    defaults = pipeline_runtime_params(task_path, profile_path)
    plan = build_pipeline_plan(task_path=task_path, profile_path=profile_path, overrides=overrides)

    pipe = PipelineController(
        project=plan["project"],
        name=plan["name"],
        version=plan["version"],
        target_project=plan["stage_project"],
    )
    task = Task.current_task()
    task_params = task.get_parameters() if task else {}
    connected = pipeline_params_from_task(defaults, task_params)
    plan = build_pipeline_plan(
        task_path=task_path,
        profile_path=profile_path,
        runtime_params=connected,
        overrides=overrides,
    )

    _add_plan_steps(pipe, plan)
    if task is not None:
        _apply_pipeline_run_metadata(task, task_name=plan["name"])
    pipe.start_locally(run_pipeline_steps_locally=False)


def _add_pipeline_args(pipe: Any, params: dict[str, Any]) -> None:
    for key, value in params.items():
        pipe.add_parameter(name=key, default=value)


def _entry_command(task_config: str | Path, profile_path: str | Path) -> str:
    return f"clearml/pipelines.py --task {Path(task_config).as_posix()} --profile {Path(profile_path).as_posix()}"


def _set_pipeline_script_with_compat(
    task: Any,
    *,
    repository: str,
    branch: str,
    working_dir: str,
    task_config: str | Path,
    profile_path: str | Path,
) -> None:
    entry_command = _entry_command(task_config, profile_path)
    common = {
        "repository": repository,
        "branch": branch,
        "commit": "",
        "diff": "",
        "working_dir": working_dir,
        "entry_point": entry_command,
    }
    try:
        task.set_script(
            **common,
            arguments={"--task": str(task_config), "--profile": str(profile_path)},
        )
    except TypeError:  # pragma: no cover - depends on ClearML SDK version
        try:
            task.set_script(**common, args=f"--task {task_config} --profile {profile_path}")
        except TypeError:
            task.set_script(**common)


def _add_plan_steps(pipe: Any, plan: dict[str, Any]) -> None:
    pipe.set_default_execution_queue(plan["queue"])
    for step in plan["steps"]:
        kwargs = {
            "name": step["name"],
            "base_task_project": step["base_task_project"],
            "base_task_name": step["base_task_name"],
        }
        if step["parents"]:
            kwargs["parents"] = step["parents"]
        if step["parameter_override"]:
            kwargs["parameter_override"] = step["parameter_override"]
        if step.get("execution_queue"):
            kwargs["execution_queue"] = step["execution_queue"]
        if step.get("pipeline_stage_group"):
            kwargs["stage"] = step["pipeline_stage_group"]
        pipe.add_step(**kwargs)


def _find_pipeline_draft(Task: Any, project_name: str, task_name: str):
    tasks = Task.get_tasks(task_name=task_name, allow_archived=False)
    for task in reversed(tasks):
        if _is_created_pipeline_controller(Task, task, project_name=project_name, require_pipeline_tag=True):
            return task
    return None


def _delete_stale_pipeline_drafts(Task: Any, project_name: str, task_name: str, keep_id: str) -> None:
    for task in Task.get_tasks(task_name=task_name, allow_archived=True):
        if task.id != keep_id and _is_created_pipeline_controller(Task, task, project_name=project_name):
            _delete_task(task)


def _is_created_pipeline_controller(
    Task: Any,
    task: Any,
    *,
    project_name: str | None = None,
    require_pipeline_tag: bool = False,
) -> bool:
    if getattr(task, "status", None) != "created":
        return False
    if project_name and not _task_is_under_pipeline_project(task, project_name):
        return False
    if str(_task_type(task)) != str(Task.TaskTypes.controller):
        return False
    if require_pipeline_tag and "pipeline" not in (task.get_system_tags() or []):
        return False
    return True


def _task_is_under_pipeline_project(task: Any, project_name: str) -> bool:
    candidate_project = _task_project_name(task)
    if not candidate_project:
        return True
    return candidate_project == project_name or candidate_project.startswith(f"{project_name}/.pipelines/")


def _task_project_name(task: Any) -> str:
    get_project_name = getattr(task, "get_project_name", None)
    return str(get_project_name()) if callable(get_project_name) else ""


def _task_type(task: Any) -> Any:
    return (
        getattr(task, "task_type", None)
        or getattr(task, "type", None)
        or getattr(getattr(task, "data", None), "type", None)
    )


def _delete_task(task: Any) -> None:
    delete = getattr(task, "delete", None)
    if callable(delete):
        delete(delete_artifacts_and_models=False, raise_on_error=False)


def _delete_created_pipeline_draft(task: Any) -> None:
    """Delete a created pipeline draft so sync can rebuild the stored graph."""
    if task is None:
        return
    if getattr(task, "status", None) != "created":
        return
    _delete_task(task)


def _delete_legacy_pipeline_templates(Task: Any, names: list[str]) -> None:
    """Remove old created pipeline templates that can still appear as New Run entries."""
    for task_name in names:
        for task in Task.get_tasks(task_name=task_name, allow_archived=True):
            if getattr(task, "status", None) != "created":
                continue
            if ".pipelines/" not in _task_project_name(task):
                continue
            _delete_task(task)


def _apply_pipeline_template_metadata(
    task: Any,
    execution_image: str | None = None,
    *,
    controller_queue: str | None = None,
    stage_queue: str | None = None,
) -> None:
    _replace_task_tags(task, PIPELINE_TEMPLATE_TAGS, remove_roles={"internal:true", "user_facing:true"})
    set_comment = getattr(task, "set_comment", None)
    if callable(set_comment):
        set_comment(_pipeline_template_comment(execution_image, controller_queue, stage_queue))


def _apply_pipeline_run_metadata(task: Any, *, task_name: str | None = None) -> None:
    if task_name:
        set_name = getattr(task, "set_name", None)
        if callable(set_name):
            set_name(task_name)
    _replace_task_tags(task, clearml_tags("pipeline", user_facing=True), remove_roles={"internal:true"})


def _replace_task_tags(task: Any, tags: list[str], *, remove_roles: set[str]) -> None:
    set_tags = getattr(task, "set_tags", None)
    if callable(set_tags):
        kept = _kept_tags(task, remove_roles)
        set_tags(sorted(set(kept) | set(tags)))
    else:
        add_tags = getattr(task, "add_tags", None)
        if callable(add_tags):
            add_tags(tags)


def _kept_tags(task: Any, remove_roles: set[str]) -> list[str]:
    get_tags = getattr(task, "get_tags", None)
    current = list(get_tags() or []) if callable(get_tags) else []
    return [tag for tag in current if not tag.startswith("run_type:") and tag not in remove_roles]


def _pipeline_template_comment(
    execution_image: str | None,
    controller_queue: str | None,
    stage_queue: str | None,
) -> str:
    image_note = f" Execution image: {execution_image}." if execution_image else ""
    queue_note = ""
    if controller_queue or stage_queue:
        queue_note = (
            f" Run the PipelineController on queue {controller_queue or '-'}; stages run on queue {stage_queue or '-'}."
        )
    return (
        "USER-FACING training pipeline template. Remote runs should use "
        "Input/clearml_dataset_id + Input/dataset_file, not Agent-local paths. "
        "Start with Basic/model_suite and Basic/use_ensemble; tune preprocessing "
        "with Features/*. Advanced users can still edit Model/candidates and "
        "Model/ensemble_methods. Synced templates install GBM packages into the "
        "remote execution venv."
        f"{queue_note}"
        f"{image_note}"
    )
