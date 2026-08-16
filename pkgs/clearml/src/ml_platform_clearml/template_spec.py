"""Stable template definitions and default parameter construction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .adapter import clearml_tags
from .execution import ExecutionSpec
from .param_defaults import build_default_connected_params
from .support import replace_task_tags, set_task_comment

REPO_ROOT = Path(__file__).resolve().parents[4]

TASK_TEMPLATES = [
    ("tabular_infer_template", "config/tasks/tabular_infer.yaml", "inference"),
    ("tabular_stage_template", "config/tasks/tabular_stage.yaml", "training"),
]
PIPELINE_TEMPLATES = [("tabular_train_pipeline_template", "config/tasks/tabular_pipeline.yaml", "pipeline")]
TEMPLATES = TASK_TEMPLATES + PIPELINE_TEMPLATES
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
        "or Input/source_manifest; start with Basic/model_suite and Basic/use_ensemble. "
        "Advanced users can still edit Model/candidates and Model/ensemble_methods. "
        "Synced templates install GBM packages into the remote execution venv."
    ),
}
TEMPLATE_TAG_OPTIONS = {
    "tabular_infer_template": {"user_facing": True},
    "tabular_stage_template": {"internal": True},
    "tabular_train_pipeline_template": {"user_facing": True},
}


def task_type(Task: Any, name: str):
    return getattr(Task.TaskTypes, name, getattr(Task.TaskTypes, "training", None))


def template_note(task_name: str, execution: ExecutionSpec | None = None) -> str:
    execution_note = (
        f" Revision: {execution.commit}. Image: {execution.image}. Python: {execution.python_binary}."
        if execution
        else ""
    )
    default = "Unsupported template name for the current product surface"
    return f"{TEMPLATE_NOTES.get(task_name, default)}{execution_note}"


def template_tags(task_name: str) -> list[str]:
    options = TEMPLATE_TAG_OPTIONS.get(task_name, {})
    return clearml_tags(
        "template",
        user_facing=bool(options.get("user_facing")),
        internal=bool(options.get("internal")),
    )


def apply_task_metadata(task: Any, task_name: str, execution: ExecutionSpec | None = None) -> None:
    replace_task_tags(
        task,
        template_tags(task_name),
        remove_tags={"internal:true", "user_facing:true"},
        remove_prefixes=("run_type:",),
    )
    set_task_comment(task, template_note(task_name, execution))


def entry_point(task_name: str) -> str:
    return "clearml/pipelines.py" if task_name == "tabular_train_pipeline_template" else "clearml/app.py"


def remote_packages(requirements_file: str = "config/requirements/clearml-agent.lock") -> list[str]:
    path = (REPO_ROOT / requirements_file).resolve()
    try:
        path.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError("clearml.execution.requirements_file must stay inside the repository.") from exc
    if not path.is_file():
        raise ValueError(f"ClearML Agent requirements file does not exist: {requirements_file}")
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def task_runtime_params(task_name: str, cfg: dict[str, Any]) -> dict[str, Any]:
    params = build_default_connected_params(cfg)
    if task_name == "tabular_infer_template" and bool(cfg.get("runtime", {}).get("use_clearml")):
        params["Model/source_type"] = "task_id"
        dataset_id, dataset_file = _infer_dataset_defaults(cfg)
        if dataset_id and not params.get("Input/clearml_dataset_id"):
            params["Input/local_path"] = ""
            params["Input/clearml_dataset_id"] = dataset_id
            params["Input/dataset_file"] = params.get("Input/dataset_file") or dataset_file
    return params


def _infer_dataset_defaults(cfg: dict[str, Any]) -> tuple[Any, Any]:
    clearml_cfg = cfg.get("clearml", {}) or {}
    return (
        clearml_cfg.get("default_infer_dataset_id") or clearml_cfg.get("default_dataset_id"),
        clearml_cfg.get("default_infer_dataset_file") or clearml_cfg.get("default_dataset_file"),
    )
