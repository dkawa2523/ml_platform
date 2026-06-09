from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CLEARML_DIR = Path(__file__).resolve().parent
for p in (str(CLEARML_DIR), str(REPO_ROOT / "pkgs/core/src"), str(REPO_ROOT / "pkgs/tabular/src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from adapter import clearml_projects, clearml_tags, clearml_template_name, default_ui_params, import_clearml_sdk
from ml_platform_core.config import load_run_config, load_yaml
from pipelines import build_pipeline_plan, pipeline_ui_params, sync_pipeline_draft


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


def _task_type(Task: Any, name: str):
    return getattr(Task.TaskTypes, name, getattr(Task.TaskTypes, "training", None))


def _template_note(task_name: str) -> str:
    if task_name == "tabular_stage_template":
        return (
            "INTERNAL ONLY: PipelineController stage task. Do not clone directly; "
            "normal users should start template/tabular_train_pipeline from the Pipeline tab."
        )
    if task_name == "tabular_infer_template":
        return (
            "USER-FACING inference task. Recommended: source_task_id + model_selector "
            "(best or ensemble). Use local_model_path only when the Agent can access it."
        )
    if task_name == "tabular_train_pipeline_template":
        return (
            "USER-FACING training Pipeline-tab draft: preprocess_features -> train_<model>* "
            "-> build_ensemble_<method>* -> evaluate_models. Set remote inputs with "
            "Input/clearml_dataset_id, Input/dataset_file, and Input/target_column; tune "
            "preprocessing under Features/* and ensembles with Model/ensemble_methods. "
            "Model/candidates is prefilled with all 10 supported models; the standard "
            "Agent image includes pkgs/tabular[gbm]. Remove GBM names only for slim/custom Agents."
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


def _apply_task_metadata(task: Any, task_name: str) -> None:
    tags = _template_tags(task_name)
    add_tags = getattr(task, "add_tags", None)
    set_tags = getattr(task, "set_tags", None)
    if callable(add_tags):
        add_tags(tags)
    elif callable(set_tags):
        current = []
        get_tags = getattr(task, "get_tags", None)
        if callable(get_tags):
            current = list(get_tags() or [])
        set_tags(sorted(set(current) | set(tags)))
    set_comment = getattr(task, "set_comment", None)
    if callable(set_comment):
        set_comment(_template_note(task_name))


def _entry_point(task_name: str) -> str:
    if task_name == "tabular_train_pipeline_template":
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
    repository = clearml_cfg.get("repository", ".")
    branch = clearml_cfg.get("branch", "main")
    working_dir = clearml_cfg.get("working_dir", ".")

    if dry_run:
        for task_name, task_config, task_type_name in TASK_TEMPLATES:
            cfg = load_run_config(task_config, profile_path)
            ui_params = default_ui_params(cfg)
            params = ", ".join(ui_params)
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
                f"entry_point={entry_point} "
                f"args=\"{_task_args(task_config, profile_path)}\" "
                f"params=[{params}] "
                f"tags={_template_tags(task_name)} "
                f"note=\"{_template_note(task_name)}\""
            )
        for task_name, task_config, task_type_name in PIPELINE_TEMPLATES:
            ui_params = pipeline_ui_params(task_config, profile_path)
            plan = build_pipeline_plan(task_path=task_config, profile_path=profile_path, ui_params=ui_params)
            params = ", ".join(ui_params)
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
                f"entry_point={_entry_point(task_name)} "
                f"args=\"{_task_args(task_config, profile_path)}\" "
                f"params=[{params}] "
                f"steps={steps} "
                f"tags={_template_tags(task_name)} "
                f"note=\"{_template_note(task_name)}\""
            )
        return

    clearml_sdk = import_clearml_sdk()
    Task = clearml_sdk.Task

    for task_name, task_config, task_type_name in TASK_TEMPLATES:
        cfg = load_run_config(task_config, profile_path)
        entry_point = _entry_point(task_name)
        params = default_ui_params(cfg)
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
        _apply_task_metadata(task, task_name)
        print(f"Synced template: {project_name}/{display_name} id={task.id} ({_template_note(task_name)})")

    for task_name, task_config, _ in PIPELINE_TEMPLATES:
        task = sync_pipeline_draft(
            task_path=task_config,
            profile_path=profile_path,
            template_name=task_name,
            repository=repository,
            branch=branch,
            working_dir=working_dir,
            packages=_remote_packages(),
        )
        print(
            "Synced pipeline template: "
            f"{clearml_projects(clearml_cfg)['pipelines']}/{clearml_template_name(task_name)} "
            f"id={task.id} ({_template_note(task_name)})"
        )
