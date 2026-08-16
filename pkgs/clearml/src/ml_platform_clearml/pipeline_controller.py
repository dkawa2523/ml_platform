from __future__ import annotations

from pathlib import Path
from typing import Any

from ml_platform_core.config import load_yaml

from .adapter import (
    clearml_tags,
    clearml_template_name,
    import_clearml_automation,
    import_clearml_sdk,
    import_clearml_symbol,
    validate_clearml_runtime,
)
from .execution import ExecutionSpec, apply_task_execution, load_execution_spec, set_task_script
from .pipeline_params import pipeline_params_from_task, pipeline_runtime_params
from .pipeline_plan import build_pipeline_plan
from .support import delete_task as _delete_clearml_task
from .support import replace_task_tags, set_task_comment

PIPELINE_TEMPLATE_TAGS = clearml_tags("template", user_facing=True)


def sync_pipeline_draft(
    task_path: str | Path = "config/tasks/tabular_pipeline.yaml",
    profile_path: str | Path = "config/profiles/clearml-dev.yaml",
    *,
    template_name: str = "tabular_train_pipeline_template",
    execution: ExecutionSpec | None = None,
    packages: list[str] | None = None,
):
    """Create a Pipeline-tab draft for the stage-based training graph."""
    clearml_sdk = import_clearml_sdk()
    Task = clearml_sdk.Task
    display_name = clearml_template_name(template_name)
    validate_clearml_runtime(require_automation=True)
    params = pipeline_runtime_params(task_path, profile_path)
    plan = build_pipeline_plan(task_path=task_path, profile_path=profile_path, runtime_params=params)
    execution = execution or load_execution_spec(load_yaml(profile_path))
    draft_params = _pipeline_draft_params(plan)

    automation = import_clearml_automation()
    PipelineController = automation.PipelineController
    pipe = _pipeline_controller(
        PipelineController,
        plan,
        display_name=display_name,
        execution=execution,
        packages=packages,
    )
    _configure_pipeline_draft(
        pipe,
        plan,
        params=params,
        draft_params=draft_params,
        task_path=task_path,
        profile_path=profile_path,
        execution=execution,
    )
    apply_task_execution(pipe.task, execution)
    _apply_pipeline_template_metadata(
        pipe.task,
        execution,
        controller_queue=plan["controller_queue"],
        stage_queue=plan["stage_queue"],
    )
    _delete_stale_pipeline_drafts(Task, plan["project"], display_name, pipe.task.id)
    return pipe.task


def _pipeline_draft_params(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "pipeline/controller_queue": plan["controller_queue"],
        "pipeline/default_queue": plan["stage_queue"],
    }


def _pipeline_controller(
    PipelineController: Any,
    plan: dict[str, Any],
    *,
    display_name: str,
    execution: ExecutionSpec,
    packages: list[str] | None,
) -> Any:
    return PipelineController(
        project=plan["project"],
        name=display_name,
        version=plan["version"],
        add_run_number=False,
        target_project=plan["stage_project"],
        repo=execution.repository,
        repo_commit=execution.commit,
        packages=packages,
        working_dir=execution.working_dir,
    )


def _configure_pipeline_draft(
    pipe: Any,
    plan: dict[str, Any],
    *,
    params: dict[str, Any],
    draft_params: dict[str, Any],
    task_path: str | Path,
    profile_path: str | Path,
    execution: ExecutionSpec,
) -> None:
    _add_pipeline_args(pipe, params)
    set_task_script(
        pipe.task,
        execution,
        entry_point="clearml/pipelines.py",
        cli_args={"--task": str(task_path), "--profile": str(profile_path)},
    )
    pipe.task.update_parameters(draft_params)
    _add_plan_steps(pipe, plan)
    pipe.create_draft()
    pipe.task.update_parameters(draft_params)


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
    validate_clearml_runtime(require_automation=True)
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


def _add_plan_steps(pipe: Any, plan: dict[str, Any]) -> None:
    pipe.set_default_execution_queue(plan["queue"])
    for step in plan["steps"]:
        pipe.add_step(**_step_kwargs(step))


def _step_kwargs(step: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "name": step["name"],
        "base_task_project": step["base_task_project"],
        "base_task_name": step["base_task_name"],
    }
    _add_step_kwarg(kwargs, "parents", step.get("parents"))
    _add_step_kwarg(kwargs, "parameter_override", step.get("parameter_override"))
    _add_step_kwarg(kwargs, "execution_queue", step.get("execution_queue"))
    _add_step_kwarg(kwargs, "stage", step.get("pipeline_stage_group"))
    return kwargs


def _add_step_kwarg(kwargs: dict[str, Any], key: str, value: Any) -> None:
    if value:
        kwargs[key] = value


def _delete_stale_pipeline_drafts(Task: Any, project_name: str, task_name: str, keep_id: str) -> None:
    for task in Task.get_tasks(task_name=task_name, allow_archived=True):
        if task.id != keep_id and _is_created_pipeline_controller(
            Task,
            task,
            project_name=project_name,
            require_pipeline_tag=True,
        ):
            _delete_task(task)


def _is_created_pipeline_controller(
    Task: Any,
    task: Any,
    *,
    project_name: str | None = None,
    require_pipeline_tag: bool = False,
) -> bool:
    return (
        getattr(task, "status", None) == "created"
        and _matches_pipeline_project(task, project_name)
        and str(_task_type(task)) == str(Task.TaskTypes.controller)
        and _has_required_pipeline_tag(task, require_pipeline_tag)
    )


def _matches_pipeline_project(task: Any, project_name: str | None) -> bool:
    return not project_name or _task_is_under_pipeline_project(task, project_name)


def _has_required_pipeline_tag(task: Any, require_pipeline_tag: bool) -> bool:
    return not require_pipeline_tag or "pipeline" in (task.get_system_tags() or [])


def _task_is_under_pipeline_project(task: Any, project_name: str) -> bool:
    candidate_project = _task_project_name(task)
    if not candidate_project:
        return False
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
    _delete_clearml_task(task)


def _apply_pipeline_template_metadata(
    task: Any,
    execution: ExecutionSpec | None = None,
    *,
    controller_queue: str | None = None,
    stage_queue: str | None = None,
) -> None:
    _replace_task_tags(task, PIPELINE_TEMPLATE_TAGS, remove_roles={"internal:true", "user_facing:true"})
    set_task_comment(task, _pipeline_template_comment(execution, controller_queue, stage_queue))


def _apply_pipeline_run_metadata(task: Any, *, task_name: str | None = None) -> None:
    if task_name:
        set_name = getattr(task, "set_name", None)
        if callable(set_name):
            set_name(task_name)
    _replace_task_tags(task, clearml_tags("pipeline", user_facing=True), remove_roles={"internal:true"})


def _replace_task_tags(task: Any, tags: list[str], *, remove_roles: set[str]) -> None:
    replace_task_tags(task, tags, remove_tags=remove_roles, remove_prefixes=("run_type:",))


def _pipeline_template_comment(
    execution: ExecutionSpec | None,
    controller_queue: str | None,
    stage_queue: str | None,
) -> str:
    return (
        "USER-FACING training pipeline template. Remote runs should use "
        "Input/clearml_dataset_id + Input/dataset_file, not Agent-local paths. "
        "Start with Basic/model_suite and Basic/use_ensemble; tune preprocessing "
        "with Features/*. Advanced users can still edit Model/candidates and "
        "Model/ensemble_methods. Synced templates install GBM packages into the "
        "remote execution venv."
        f"{_queue_note(controller_queue, stage_queue)}"
        f"{_execution_note(execution)}"
    )


def _queue_note(controller_queue: str | None, stage_queue: str | None) -> str:
    if not controller_queue and not stage_queue:
        return ""
    return f" Run the PipelineController on queue {controller_queue or '-'}; stages run on queue {stage_queue or '-'}."


def _execution_note(execution: ExecutionSpec | None) -> str:
    if not execution:
        return ""
    return f" Revision: {execution.commit}. Execution image: {execution.image}. Python: {execution.python_binary}."
