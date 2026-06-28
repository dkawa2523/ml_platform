from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


_CLEARML_DIR = Path(__file__).resolve().parent
if str(_CLEARML_DIR) not in sys.path:
    sys.path.insert(0, str(_CLEARML_DIR))

from _entrypoint_bootstrap import add_clearml_entrypoint_paths

add_clearml_entrypoint_paths()

REPO_ROOT = Path(__file__).resolve().parents[1]

from adapter import (
    apply_execution_image,
    clearml_execution_image,
    clearml_projects,
    clearml_tags,
    clearml_template_name,
    default_runtime_params,
    import_clearml_sdk,
    validate_clearml_runtime,
)
from ml_platform_core.config import load_run_config, load_yaml
from pipelines import build_pipeline_plan, pipeline_runtime_params, sync_pipeline_draft


TASK_TEMPLATES = [
    ("tabular_infer_template", "config/tasks/tabular_infer.yaml", "inference"),
    ("tabular_stage_template", "config/tasks/tabular_stage.yaml", "training"),
]
PIPELINE_TEMPLATES = [
    ("tabular_train_pipeline_template", "config/tasks/tabular_pipeline.yaml", "pipeline"),
]
# Default sync targets: tabular_infer_template, tabular_stage_template, and
# tabular_train_pipeline_template.
TEMPLATES = TASK_TEMPLATES + PIPELINE_TEMPLATES
REMOTE_GBM_PACKAGES = ["lightgbm>=4.0", "xgboost>=2.0", "catboost>=1.2"]


def _task_type(Task: Any, name: str):
    return getattr(Task.TaskTypes, name, getattr(Task.TaskTypes, "training", None))


def _template_note(task_name: str, execution_image: str | None = None) -> str:
    image_note = f" Execution image: {execution_image}." if execution_image else ""
    if task_name == "tabular_stage_template":
        return (
            "INTERNAL ONLY: PipelineController stage task. Do not clone directly; "
            "normal users should start template/tabular_train_pipeline from the Pipeline tab."
            f"{image_note}"
        )
    if task_name == "tabular_infer_template":
        return (
            "USER-FACING inference task. Recommended: source_task_id + model_selector "
            "(best or ensemble). Use local_model_path only when the Agent can access it."
            f"{image_note}"
        )
    if task_name == "tabular_train_pipeline_template":
        return (
            "USER-FACING training Pipeline-tab draft: preprocess_features -> train_<model>* "
            "-> build_ensemble_<method>* -> evaluate_models. Set remote inputs with "
            "Input/clearml_dataset_id, Input/dataset_file, and Input/target_column; "
            "start with Basic/model_suite and Basic/use_ensemble. Advanced users can "
            "still edit Model/candidates and Model/ensemble_methods. Synced templates "
            "install GBM packages into the remote execution venv."
            f"{image_note}"
        )
    return "Unsupported template name for the current product surface"


def _template_tags(task_name: str) -> list[str]:
    if task_name == "tabular_stage_template":
        return clearml_tags("template", internal=True)
    if task_name == "tabular_train_pipeline_template":
        return clearml_tags("template", user_facing=True)
    if task_name == "tabular_infer_template":
        return clearml_tags("template", user_facing=True)
    return clearml_tags("template")


def _apply_task_metadata(task: Any, task_name: str, execution_image: str | None = None) -> None:
    tags = _template_tags(task_name)
    set_tags = getattr(task, "set_tags", None)
    if callable(set_tags):
        current = []
        get_tags = getattr(task, "get_tags", None)
        if callable(get_tags):
            current = list(get_tags() or [])
        kept = [
            tag
            for tag in current
            if not tag.startswith("run_type:") and tag not in {"internal:true", "user_facing:true"}
        ]
        set_tags(sorted(set(kept) | set(tags)))
    else:
        add_tags = getattr(task, "add_tags", None)
        if callable(add_tags):
            add_tags(tags)
    set_comment = getattr(task, "set_comment", None)
    if callable(set_comment):
        set_comment(_template_note(task_name, execution_image))


def _entry_point(task_name: str) -> str:
    if task_name == "tabular_train_pipeline_template":
        return "clearml/pipelines.py"
    return "clearml/app.py"


def _entry_command(entry_point: str, task_config: str, profile_path: str | Path) -> str:
    return f"{entry_point} --task {task_config} --profile {Path(profile_path).as_posix()}"


def _remote_packages() -> list[str]:
    requirements = REPO_ROOT / "requirements.txt"
    packages = [
        line.strip()
        for line in requirements.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not any(
        line.split("=", 1)[0].split("<", 1)[0].split(">", 1)[0].strip().lower() == "clearml" for line in packages
    ):
        packages.append("clearml==2.1.7")
    for package in REMOTE_GBM_PACKAGES:
        if package not in packages:
            packages.append(package)
    return packages


def _task_runtime_params(task_name: str, cfg: dict[str, Any]) -> dict[str, Any]:
    params = default_runtime_params(cfg)
    clearml_cfg = cfg.get("clearml", {}) or {}
    if task_name == "tabular_infer_template" and cfg.get("runtime", {}).get("use_clearml"):
        params["Model/source_type"] = "task_id"
        dataset_id = clearml_cfg.get("default_infer_dataset_id") or clearml_cfg.get("default_dataset_id")
        dataset_file = clearml_cfg.get("default_infer_dataset_file") or clearml_cfg.get("default_dataset_file")
        if dataset_id and not params.get("Input/clearml_dataset_id"):
            params["Input/local_path"] = ""
            params["Input/clearml_dataset_id"] = dataset_id
            params["Input/dataset_file"] = params.get("Input/dataset_file") or dataset_file
    return params


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
        "commit": "",
        "diff": "",
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


def _delete_stale_created_templates(Task: Any, project_name: str, task_name: str, keep_id: str) -> None:
    for task in Task.get_tasks(project_name=project_name, task_name=task_name, allow_archived=True):
        if task.id == keep_id or getattr(task, "status", None) != "created":
            continue
        delete = getattr(task, "delete", None)
        if callable(delete):
            delete(delete_artifacts_and_models=False, raise_on_error=False)


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
    for key in list(task.get_parameters() or {}):
        if key.startswith("Model/params/") or key.startswith("Model/candidates/"):
            task.delete_parameter(key, force=True)
    task.update_parameters(params)
    task.delete_parameter("Args/task", force=True)
    task.delete_parameter("Args/profile", force=True)
    task.set_packages(_remote_packages())
    return task


def _task_args(task_config: str, profile_path: str | Path) -> str:
    return f"--task {task_config} --profile {Path(profile_path).as_posix()}"


def sync_templates(profile_path: str | Path, *, dry_run: bool = False) -> None:
    """Register minimal ClearML template tasks and Pipeline-tab drafts."""
    profile = load_yaml(profile_path)
    clearml_cfg = profile.get("clearml", {})
    project_name = clearml_projects(clearml_cfg)["templates"]
    execution_image = clearml_execution_image(clearml_cfg)
    repository = clearml_cfg.get("repository", ".")
    branch = clearml_cfg.get("branch", "main")
    working_dir = clearml_cfg.get("working_dir", ".")

    if dry_run:
        for task_name, task_config, task_type_name in TASK_TEMPLATES:
            cfg = load_run_config(task_config, profile_path)
            runtime_params = _task_runtime_params(task_name, cfg)
            params = ", ".join(runtime_params)
            entry_point = _entry_point(task_name)
            display_name = clearml_template_name(task_name)
            print(
                "DRY-RUN template: "
                f"project={project_name} "
                f"name={display_name} "
                f"type={task_type_name} "
                f"repository={repository} "
                f"branch={branch} "
                f"working_dir={working_dir} "
                f"execution_image={execution_image or ''} "
                f"entry_point={entry_point} "
                f'args="{_task_args(task_config, profile_path)}" '
                f"params=[{params}] "
                f"tags={_template_tags(task_name)} "
                f'note="{_template_note(task_name, execution_image)}"'
            )
        for task_name, task_config, task_type_name in PIPELINE_TEMPLATES:
            runtime_params = pipeline_runtime_params(task_config, profile_path)
            plan = build_pipeline_plan(task_path=task_config, profile_path=profile_path, ui_params=runtime_params)
            params = ", ".join(runtime_params)
            steps = " -> ".join(step["name"] for step in plan["steps"])
            display_name = clearml_template_name(task_name)
            print(
                "DRY-RUN pipeline template: "
                f"project={plan['project']} "
                f"name={display_name} "
                f"type={task_type_name} "
                f"repository={repository} "
                f"branch={branch} "
                f"working_dir={working_dir} "
                f"execution_image={execution_image or ''} "
                f"entry_point={_entry_point(task_name)} "
                f'args="{_task_args(task_config, profile_path)}" '
                f"params=[{params}] "
                f"steps={steps} "
                f"tags={_template_tags(task_name)} "
                f'note="{_template_note(task_name, execution_image)}"'
            )
        return

    validate_clearml_runtime()
    clearml_sdk = import_clearml_sdk()
    Task = clearml_sdk.Task

    for task_name, task_config, task_type_name in TASK_TEMPLATES:
        cfg = load_run_config(task_config, profile_path)
        entry_point = _entry_point(task_name)
        params = _task_runtime_params(task_name, cfg)
        display_name = clearml_template_name(task_name)
        task = _sync_template_task(
            Task,
            project_name=project_name,
            task_name=display_name,
            task_type=_task_type(Task, task_type_name),
            repository=repository,
            branch=branch,
            working_dir=working_dir,
            entry_point=entry_point,
            task_config=task_config,
            profile_path=profile_path,
            params=params,
        )
        apply_execution_image(task, execution_image)
        _apply_task_metadata(task, task_name, execution_image)
        _delete_stale_created_templates(Task, project_name, display_name, task.id)
        print(
            f"Synced template: {project_name}/{display_name} id={task.id} image={execution_image or '-'} ({_template_note(task_name, execution_image)})"
        )

    for task_name, task_config, _ in PIPELINE_TEMPLATES:
        task = sync_pipeline_draft(
            task_path=task_config,
            profile_path=profile_path,
            template_name=task_name,
            repository=repository,
            branch=branch,
            working_dir=working_dir,
            packages=_remote_packages(),
            execution_image=execution_image,
        )
        print(
            "Synced pipeline template: "
            f"{clearml_projects(clearml_cfg)['pipelines']}/{clearml_template_name(task_name)} "
            f"id={task.id} image={execution_image or '-'} ({_template_note(task_name, execution_image)})"
        )
