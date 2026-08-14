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
    clearml_projects,
    clearml_tags,
    clearml_template_name,
    import_clearml_sdk,
    validate_clearml_runtime,
)
from execution import ExecutionSpec, apply_task_execution, load_execution_spec, set_task_script
from ml_platform_core.config import load_run_config, load_yaml
from param_defaults import build_default_connected_params
from pipeline_controller import sync_pipeline_draft
from pipeline_params import pipeline_runtime_params
from pipeline_plan import build_pipeline_plan
from support import delete_task, replace_task_tags, script_args, script_entry_point, set_task_comment


TASK_TEMPLATES = [
    ("tabular_infer_template", "config/tasks/tabular_infer.yaml", "inference"),
    ("tabular_stage_template", "config/tasks/tabular_stage.yaml", "training"),
]
PIPELINE_TEMPLATES = [("tabular_train_pipeline_template", "config/tasks/tabular_pipeline.yaml", "pipeline")]
# Default sync targets: tabular_infer_template, tabular_stage_template, and
# tabular_train_pipeline_template.
TEMPLATES = TASK_TEMPLATES + PIPELINE_TEMPLATES
REMOTE_GBM_PACKAGES = ["lightgbm>=4.0", "xgboost>=2.0", "catboost>=1.2"]
TEMPLATE_NOTES = {
    "tabular_stage_template": (
        "INTERNAL ONLY: PipelineController stage task. Do not clone directly; "
        "normal users should start template/tabular_train_pipeline from the Pipeline tab."
    ),
    "tabular_infer_template": (
        "USER-FACING inference task. Recommended: source_task_id + model_selector "
        "(best or ensemble). Use local_model_path only when the Agent can access it."
    ),
    "tabular_train_pipeline_template": (
        "USER-FACING training Pipeline-tab draft: preprocess_features -> train_<model>* "
        "-> build_ensemble_<method>* -> evaluate_models. Package stage keys stay "
        "train_model/build_ensemble; suffixes are ClearML step labels. Set remote inputs with "
        "Input/clearml_dataset_id plus either Input/dataset_file/Input/target_column "
        "or Input/source_manifest; "
        "start with Basic/model_suite and Basic/use_ensemble. Advanced users can "
        "still edit Model/candidates and Model/ensemble_methods. Synced templates "
        "install GBM packages into the remote execution venv."
    ),
}
TEMPLATE_TAG_OPTIONS = {
    "tabular_infer_template": {"user_facing": True},
    "tabular_stage_template": {"internal": True},
    "tabular_train_pipeline_template": {"user_facing": True},
}


def _task_type(Task: Any, name: str):
    return getattr(Task.TaskTypes, name, getattr(Task.TaskTypes, "training", None))


def _template_note(task_name: str, execution: ExecutionSpec | None = None) -> str:
    execution_note = (
        f" Revision: {execution.commit}. Image: {execution.image}. Python: {execution.python_binary}."
        if execution
        else ""
    )
    return (
        f"{TEMPLATE_NOTES.get(task_name, 'Unsupported template name for the current product surface')}{execution_note}"
    )


def _template_tags(task_name: str) -> list[str]:
    options = TEMPLATE_TAG_OPTIONS.get(task_name, {})
    return clearml_tags(
        "template",
        user_facing=bool(options.get("user_facing")),
        internal=bool(options.get("internal")),
    )


def _apply_task_metadata(task: Any, task_name: str, execution: ExecutionSpec | None = None) -> None:
    replace_task_tags(
        task,
        _template_tags(task_name),
        remove_tags={"internal:true", "user_facing:true"},
        remove_prefixes=("run_type:",),
    )
    set_task_comment(task, _template_note(task_name, execution))


def _entry_point(task_name: str) -> str:
    return "clearml/pipelines.py" if task_name == "tabular_train_pipeline_template" else "clearml/app.py"


def _remote_packages() -> list[str]:
    packages = _requirements_packages()
    _append_package_if_missing(packages, "clearml==2.1.7", package_name="clearml")
    for package in REMOTE_GBM_PACKAGES:
        _append_package_if_missing(packages, package)
    return packages


def _requirements_packages() -> list[str]:
    requirements = REPO_ROOT / "requirements.txt"
    return [
        line.strip()
        for line in requirements.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _append_package_if_missing(packages: list[str], package: str, *, package_name: str | None = None) -> None:
    name = package_name or _package_name(package)
    if not any(_package_name(item) == name for item in packages):
        packages.append(package)


def _package_name(package: str) -> str:
    return package.split("=", 1)[0].split("<", 1)[0].split(">", 1)[0].strip().lower()


def _task_runtime_params(task_name: str, cfg: dict[str, Any]) -> dict[str, Any]:
    params = build_default_connected_params(cfg)
    if _uses_remote_infer_defaults(task_name, cfg):
        _apply_remote_infer_defaults(params, cfg)
    return params


def _uses_remote_infer_defaults(task_name: str, cfg: dict[str, Any]) -> bool:
    return task_name == "tabular_infer_template" and bool(cfg.get("runtime", {}).get("use_clearml"))


def _apply_remote_infer_defaults(params: dict[str, Any], cfg: dict[str, Any]) -> None:
    params["Model/source_type"] = "task_id"
    dataset_id, dataset_file = _infer_dataset_defaults(cfg)
    if dataset_id and not params.get("Input/clearml_dataset_id"):
        params["Input/local_path"] = ""
        params["Input/clearml_dataset_id"] = dataset_id
        params["Input/dataset_file"] = params.get("Input/dataset_file") or dataset_file


def _infer_dataset_defaults(cfg: dict[str, Any]) -> tuple[Any, Any]:
    clearml_cfg = cfg.get("clearml", {}) or {}
    return (
        clearml_cfg.get("default_infer_dataset_id") or clearml_cfg.get("default_dataset_id"),
        clearml_cfg.get("default_infer_dataset_file") or clearml_cfg.get("default_dataset_file"),
    )


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
            packages=_remote_packages(),
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
    _replace_template_params(task, params)
    return task


def _replace_template_params(task: Any, params: dict[str, Any]) -> None:
    for key in list(task.get_parameters() or {}):
        if key.startswith("Model/params/") or key.startswith("Model/candidates/"):
            task.delete_parameter(key, force=True)
    task.update_parameters(params)
    task.delete_parameter("Args/task", force=True)
    task.delete_parameter("Args/profile", force=True)
    task.set_packages(_remote_packages())


def _cli_args(task_config: str, profile_path: str | Path) -> dict[str, str]:
    return {"--task": task_config, "--profile": str(profile_path)}


def _template_sync_settings(profile_path: str | Path) -> dict[str, Any]:
    profile = load_yaml(profile_path)
    clearml_cfg = profile.get("clearml", {})
    projects = clearml_projects(clearml_cfg)
    return {
        "profile_path": profile_path,
        "clearml_cfg": clearml_cfg,
        "project_name": projects["templates"],
        "pipeline_project_name": projects["pipelines"],
        "execution": load_execution_spec(profile),
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
    runtime_params = _task_runtime_params(task_name, cfg)
    entry_point = _entry_point(task_name)
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
        f"entry_point={entry_point} "
        f'args="{script_args(_cli_args(task_config, settings["profile_path"]))}" '
        f"params=[{', '.join(runtime_params)}] "
        f"tags={_template_tags(task_name)} "
        f'note="{_template_note(task_name, execution)}"'
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
        f"entry_point={_entry_point(task_name)} "
        f'args="{script_args(_cli_args(task_config, settings["profile_path"]))}" '
        f"params=[{', '.join(runtime_params)}] "
        f"steps={' -> '.join(step['name'] for step in plan['steps'])} "
        f"tags={_template_tags(task_name)} "
        f'note="{_template_note(task_name, execution)}"'
    )


def _sync_task_templates(Task: Any, settings: dict[str, Any]) -> None:
    for task_name, task_config, task_type_name in TASK_TEMPLATES:
        cfg = load_run_config(task_config, settings["profile_path"])
        entry_point = _entry_point(task_name)
        params = _task_runtime_params(task_name, cfg)
        display_name = clearml_template_name(task_name)
        task = _sync_template_task(
            Task,
            project_name=settings["project_name"],
            task_name=display_name,
            task_type=_task_type(Task, task_type_name),
            execution=settings["execution"],
            entry_point=entry_point,
            task_config=task_config,
            profile_path=settings["profile_path"],
            params=params,
        )
        apply_task_execution(task, settings["execution"])
        _apply_task_metadata(task, task_name, settings["execution"])
        _delete_stale_created_templates(Task, settings["project_name"], display_name, task.id)
        print(
            f"Synced template: {settings['project_name']}/{display_name} "
            f"id={task.id} revision={settings['execution'].commit} image={settings['execution'].image} "
            f"({_template_note(task_name, settings['execution'])})"
        )


def _sync_pipeline_templates(settings: dict[str, Any]) -> None:
    for task_name, task_config, _ in PIPELINE_TEMPLATES:
        task = sync_pipeline_draft(
            task_path=task_config,
            profile_path=settings["profile_path"],
            template_name=task_name,
            execution=settings["execution"],
            packages=_remote_packages(),
        )
        print(
            "Synced pipeline template: "
            f"{settings['pipeline_project_name']}/{clearml_template_name(task_name)} "
            f"id={task.id} revision={settings['execution'].commit} image={settings['execution'].image} "
            f"({_template_note(task_name, settings['execution'])})"
        )
