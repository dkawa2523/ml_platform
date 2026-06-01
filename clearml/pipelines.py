from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CLEARML_DIR = Path(__file__).resolve().parent
for p in (str(CLEARML_DIR), str(REPO_ROOT / "pkgs/core/src"), str(REPO_ROOT / "pkgs/tabular/src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from adapter import as_bool, as_candidates, as_dict, as_list, import_clearml_automation, import_clearml_sdk, import_clearml_symbol
from ml_platform_core.config import load_yaml
from ml_platform_tabular.pipeline_modes import apply_pipeline_mode_defaults


MODEL_ARTIFACT_REF = "${train.artifacts.model.url}"
TASK_TO_TEMPLATE = {
    "tabular_train": "tabular_train_template",
    "tabular_eval": "tabular_eval_template",
    "tabular_infer": "tabular_infer_template",
}


def pipeline_ui_params(
    task_path: str | Path = "config/tasks/tabular_pipeline.yaml",
    profile_path: str | Path = "config/profiles/clearml-dev.yaml",
) -> dict[str, Any]:
    pipeline_cfg = load_yaml(task_path)
    train_cfg = load_yaml(pipeline_cfg.get("train", {}).get("task_config", "config/tasks/tabular_train.yaml"))
    eval_cfg = load_yaml(pipeline_cfg.get("eval", {}).get("task_config", "config/tasks/tabular_eval.yaml"))
    infer_cfg = load_yaml(pipeline_cfg.get("infer", {}).get("task_config", "config/tasks/tabular_infer.yaml"))
    run = pipeline_cfg.get("run", {})
    train_data = train_cfg.get("data", {})
    infer_output = infer_cfg.get("output", {})
    train_model = train_cfg.get("model", {})
    train_ensemble = train_model.get("ensemble", {}) or {}
    if not isinstance(train_ensemble, dict):
        train_ensemble = {}
    train_search = train_model.get("search", {}) or {}
    if not isinstance(train_search, dict):
        train_search = {}
    return {
        "Run/task": pipeline_cfg.get("task"),
        "Run/name": run.get("name"),
        "Run/seed": run.get("seed"),
        "Run/pipeline_mode": run.get("pipeline_mode", "auto"),
        "Input/clearml_dataset_id": None,
        "Input/train_dataset_file": train_cfg.get("data", {}).get("dataset_file"),
        "Input/eval_dataset_file": eval_cfg.get("data", {}).get("dataset_file"),
        "Input/infer_dataset_file": infer_cfg.get("data", {}).get("dataset_file"),
        "Input/target_column": train_data.get("target_column"),
        "Input/id_columns": train_data.get("id_columns", []),
        "Model/name": train_model.get("name"),
        "Model/params": json.dumps(train_model.get("params", {}) or {}),
        "Model/candidates": json.dumps(train_model.get("candidates", []) or []),
        "Model/selection_metric": train_model.get("selection_metric", "rmse"),
        "Model/search_enabled": bool(train_search.get("enabled", False)),
        "Model/search_method": train_search.get("method", "grid"),
        "Model/search_space": json.dumps(train_search.get("search_space", {}) or {}),
        "Model/max_trials": int(train_search.get("max_trials") or 20),
        "Model/ensemble_enabled": bool(train_ensemble.get("enabled", False)),
        "Model/ensemble_method": train_ensemble.get("method", "mean_topk"),
        "Model/ensemble_top_k": int(train_ensemble.get("top_k") or 3),
        "Model/feature_preset": train_cfg.get("features", {}).get("preset"),
        "Output/prediction_name": infer_output.get("prediction_name"),
        "Output/chunk_size": infer_output.get("chunk_size"),
    }


def _effective_pipeline_params(ui_params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    model_cfg = {
        "name": ui_params.get("Model/name"),
        "params": as_dict(ui_params.get("Model/params")),
        "candidates": as_candidates(ui_params.get("Model/candidates")),
        "selection_metric": ui_params.get("Model/selection_metric", "rmse"),
        "search": {
            "enabled": as_bool(ui_params.get("Model/search_enabled")),
            "method": str(ui_params.get("Model/search_method") or "grid").strip().lower(),
            "search_space": as_dict(ui_params.get("Model/search_space")),
            "max_trials": int(ui_params.get("Model/max_trials") or 20),
        },
        "ensemble": {
            "enabled": as_bool(ui_params.get("Model/ensemble_enabled")),
            "method": ui_params.get("Model/ensemble_method") or "mean_topk",
            "top_k": int(ui_params.get("Model/ensemble_top_k") or 3),
        },
    }
    mode, effective_cfg = apply_pipeline_mode_defaults(
        {
            "run": {"pipeline_mode": ui_params.get("Run/pipeline_mode", "auto")},
            "model": model_cfg,
        }
    )
    effective_model = effective_cfg["model"]
    effective_params = dict(ui_params)
    effective_params.update(
        {
            "Model/params": json.dumps(effective_model.get("params", {}) or {}),
            "Model/candidates": json.dumps(effective_model.get("candidates", []) or []),
            "Model/search_enabled": bool(effective_model.get("search", {}).get("enabled", False)),
            "Model/search_method": effective_model.get("search", {}).get("method", "grid"),
            "Model/search_space": json.dumps(effective_model.get("search", {}).get("search_space", {}) or {}),
            "Model/max_trials": int(effective_model.get("search", {}).get("max_trials") or 20),
            "Model/ensemble_enabled": bool(effective_model.get("ensemble", {}).get("enabled", False)),
            "Model/ensemble_method": effective_model.get("ensemble", {}).get("method", "mean_topk"),
            "Model/ensemble_top_k": int(effective_model.get("ensemble", {}).get("top_k") or 3),
        }
    )
    return mode, effective_params


def _apply_pipeline_overrides(step: dict[str, Any], ui_params: dict[str, Any]) -> None:
    dataset_id = ui_params.get("Input/clearml_dataset_id")
    dataset_file = ui_params.get(f"Input/{step['name']}_dataset_file")
    if dataset_file:
        step["parameter_override"]["Input/dataset_file"] = dataset_file
    if dataset_id:
        step["parameter_override"]["Input/clearml_dataset_id"] = dataset_id
        step["parameter_override"]["Input/local_path"] = ""
    if step["name"] in {"train", "eval"} and ui_params.get("Input/target_column"):
        step["parameter_override"]["Input/target_column"] = ui_params["Input/target_column"]
    if "Input/id_columns" in ui_params:
        step["parameter_override"]["Input/id_columns"] = as_list(ui_params.get("Input/id_columns")) or []

    if step["name"] == "train":
        if ui_params.get("Model/name"):
            step["parameter_override"]["Model/name"] = ui_params["Model/name"]
        if "Model/params" in ui_params:
            step["parameter_override"]["Model/params"] = json.dumps(as_dict(ui_params.get("Model/params")))
        if "Model/candidates" in ui_params:
            step["parameter_override"]["Model/candidates"] = json.dumps(as_candidates(ui_params.get("Model/candidates")))
        if ui_params.get("Model/selection_metric"):
            step["parameter_override"]["Model/selection_metric"] = ui_params["Model/selection_metric"]
        for key in ("Model/search_enabled", "Model/search_method", "Model/search_space", "Model/max_trials"):
            if key in ui_params:
                step["parameter_override"][key] = ui_params[key]
        for key in ("Model/ensemble_enabled", "Model/ensemble_method", "Model/ensemble_top_k"):
            if key in ui_params:
                step["parameter_override"][key] = ui_params[key]
        if ui_params.get("Model/feature_preset"):
            step["parameter_override"]["Model/feature_preset"] = ui_params["Model/feature_preset"]
    if step["name"] == "infer":
        if ui_params.get("Output/prediction_name"):
            step["parameter_override"]["Output/prediction_name"] = ui_params["Output/prediction_name"]
        if "Output/chunk_size" in ui_params and ui_params.get("Output/chunk_size") not in {None, ""}:
            step["parameter_override"]["Output/chunk_size"] = int(ui_params["Output/chunk_size"])


def _load_step_task_name(task_config: str | Path) -> str:
    task_cfg = load_yaml(task_config)
    task_name = task_cfg.get("task")
    if task_name not in TASK_TO_TEMPLATE:
        raise ValueError(f"Unsupported pipeline step task: {task_name!r}")
    return task_name


def build_pipeline_plan(
    task_path: str | Path = "config/tasks/tabular_pipeline.yaml",
    profile_path: str | Path = "config/profiles/clearml-dev.yaml",
    ui_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pipeline_cfg = load_yaml(task_path)
    profile = load_yaml(profile_path)
    clearml_cfg = profile.get("clearml", {})
    project_root = clearml_cfg.get("project_root", "MLPlatform/Dev")
    templates_project = f"{project_root}/Templates"
    default_params = pipeline_ui_params(task_path, profile_path)
    mode, effective_params = _effective_pipeline_params({**default_params, **(ui_params or {})})

    steps = []
    for name, parents in (("train", []), ("eval", ["train"]), ("infer", ["eval"])):
        section = pipeline_cfg.get(name, {})
        task_config = section.get("task_config")
        if not task_config:
            raise ValueError(f"{name}.task_config is required for ClearML pipeline.")
        task_name = _load_step_task_name(task_config)
        step: dict[str, Any] = {
            "name": name,
            "parents": parents,
            "base_task_project": templates_project,
            "base_task_name": TASK_TO_TEMPLATE[task_name],
            "task_config": task_config,
            "parameter_override": {},
        }
        if name in {"eval", "infer"}:
            step["parameter_override"]["Model/artifact_path"] = MODEL_ARTIFACT_REF
        if ui_params:
            _apply_pipeline_overrides(step, effective_params)
        steps.append(step)

    return {
        "project": f"{project_root}/Pipelines",
        "name": pipeline_cfg.get("run", {}).get("name", "tabular_pipeline"),
        "version": "0.1.0",
        "pipeline_mode": mode,
        "queue": clearml_cfg.get("queue", "default"),
        "steps": steps,
    }


def print_pipeline_plan(plan: dict[str, Any]) -> None:
    print(
        "DRY-RUN pipeline: "
        f"project={plan['project']} "
        f"name={plan['name']} "
        f"version={plan['version']} "
        f"pipeline_mode={plan['pipeline_mode']} "
        f"queue={plan['queue']}"
    )
    for step in plan["steps"]:
        parents = ",".join(step["parents"]) if step["parents"] else "-"
        overrides = ", ".join(f"{key}={value}" for key, value in step["parameter_override"].items()) or "-"
        print(
            "DRY-RUN step: "
            f"name={step['name']} "
            f"parents={parents} "
            f"template={step['base_task_project']}/{step['base_task_name']} "
            f"task_config={step['task_config']} "
            f"parameter_override=[{overrides}]"
        )


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
        pipe.add_step(**kwargs)


def _find_pipeline_draft(Task: Any, task_name: str):
    tasks = Task.get_tasks(task_name=task_name, allow_archived=False)
    for task in reversed(tasks):
        if getattr(task, "status", None) != "created":
            continue
        if str(getattr(task, "task_type", "")) != str(Task.TaskTypes.controller):
            continue
        if "pipeline" not in (task.get_system_tags() or []):
            continue
        return task
    return None


def sync_pipeline_draft(
    task_path: str | Path = "config/tasks/tabular_pipeline.yaml",
    profile_path: str | Path = "config/profiles/clearml-dev.yaml",
    *,
    template_name: str = "tabular_pipeline_template",
    repository: str | None = None,
    branch: str | None = None,
    working_dir: str | None = None,
    packages: list[str] | None = None,
):
    """Create a Pipeline-tab draft that users can edit and enqueue from ClearML."""
    clearml_sdk = import_clearml_sdk()
    Task = clearml_sdk.Task
    existing = _find_pipeline_draft(Task, template_name)
    params = pipeline_ui_params(task_path, profile_path)
    if existing is not None:
        _set_pipeline_script_with_compat(
            existing,
            repository=repository or ".",
            branch=branch or "main",
            working_dir=working_dir or ".",
            task_config=task_path,
            profile_path=profile_path,
        )
        existing.update_parameters(params)
        if packages:
            existing.set_packages(packages)
        return existing

    automation = import_clearml_automation()
    PipelineController = automation.PipelineController
    plan = build_pipeline_plan(task_path=task_path, profile_path=profile_path, ui_params=params)
    pipe = PipelineController(
        project=plan["project"],
        name=template_name,
        version=plan["version"],
        add_run_number=False,
        target_project=plan["project"],
        repo=repository or ".",
        repo_branch=branch,
        packages=packages,
        working_dir=working_dir or ".",
    )
    _set_pipeline_script_with_compat(
        pipe.task,
        repository=repository or ".",
        branch=branch or "main",
        working_dir=working_dir or ".",
        task_config=task_path,
        profile_path=profile_path,
    )
    pipe.task.update_parameters(params)
    _add_plan_steps(pipe, plan)
    pipe.create_draft()
    pipe.task.update_parameters(params)
    return pipe.task


def register_tabular_pipeline(
    task_path: str | Path = "config/tasks/tabular_pipeline.yaml",
    profile_path: str | Path = "config/profiles/clearml-dev.yaml",
) -> None:
    """Register a minimal train -> eval -> infer ClearML pipeline.

    This is a Phase 3 starter. The local pipeline remains in pkgs/tabular/pipeline.py.
    Keep this DAG simple until template task execution is stable in the target server.
    """
    automation = import_clearml_automation()
    PipelineController = automation.PipelineController
    Task = import_clearml_symbol("Task")
    defaults = pipeline_ui_params(task_path, profile_path)
    plan = build_pipeline_plan(task_path=task_path, profile_path=profile_path)

    pipe = PipelineController(
        project=plan["project"],
        name=plan["name"],
        version=plan["version"],
    )
    task = Task.current_task()
    task_params = task.get_parameters() if task else {}
    connected = {**defaults, **{key: value for key, value in task_params.items() if key in defaults}}
    plan = build_pipeline_plan(task_path=task_path, profile_path=profile_path, ui_params=connected)

    _add_plan_steps(pipe, plan)
    pipe.start_locally(run_pipeline_steps_locally=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Register or dry-run the ClearML tabular pipeline.")
    parser.add_argument("--task", default="config/tasks/tabular_pipeline.yaml", help="Path to pipeline task config YAML.")
    parser.add_argument("--profile", default="config/profiles/clearml-dev.yaml", help="Path to profile config YAML.")
    parser.add_argument("--dry-run", action="store_true", help="Print the pipeline DAG without requiring ClearML SDK.")
    args = parser.parse_args()

    plan = build_pipeline_plan(task_path=args.task, profile_path=args.profile)
    if args.dry_run:
        print_pipeline_plan(plan)
        return
    register_tabular_pipeline(task_path=args.task, profile_path=args.profile)


if __name__ == "__main__":
    main()
