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

from adapter import as_dict, import_clearml_automation, import_clearml_symbol
from ml_platform_core.config import load_yaml


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
    train_model = train_cfg.get("model", {})
    return {
        "Run/task": pipeline_cfg.get("task"),
        "Run/name": run.get("name"),
        "Run/seed": run.get("seed"),
        "Input/clearml_dataset_id": None,
        "Input/train_dataset_file": train_cfg.get("data", {}).get("dataset_file"),
        "Input/eval_dataset_file": eval_cfg.get("data", {}).get("dataset_file"),
        "Input/infer_dataset_file": infer_cfg.get("data", {}).get("dataset_file"),
        "Model/name": train_model.get("name"),
        "Model/params": train_model.get("params", {}),
        "Model/feature_preset": train_cfg.get("features", {}).get("preset"),
    }


def _apply_pipeline_overrides(step: dict[str, Any], ui_params: dict[str, Any]) -> None:
    dataset_id = ui_params.get("Input/clearml_dataset_id")
    if dataset_id:
        step["parameter_override"]["Input/clearml_dataset_id"] = dataset_id
        step["parameter_override"]["Input/local_path"] = ""
        dataset_file = ui_params.get(f"Input/{step['name']}_dataset_file")
        if dataset_file:
            step["parameter_override"]["Input/dataset_file"] = dataset_file

    if step["name"] == "train":
        if ui_params.get("Model/name"):
            step["parameter_override"]["Model/name"] = ui_params["Model/name"]
        if "Model/params" in ui_params:
            step["parameter_override"]["Model/params"] = json.dumps(as_dict(ui_params.get("Model/params")))
        if ui_params.get("Model/feature_preset"):
            step["parameter_override"]["Model/feature_preset"] = ui_params["Model/feature_preset"]


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
            _apply_pipeline_overrides(step, ui_params)
        steps.append(step)

    return {
        "project": f"{project_root}/Pipelines",
        "name": pipeline_cfg.get("run", {}).get("name", "tabular_pipeline"),
        "version": "0.1.0",
        "queue": clearml_cfg.get("queue", "default"),
        "steps": steps,
    }


def print_pipeline_plan(plan: dict[str, Any]) -> None:
    print(
        "DRY-RUN pipeline: "
        f"project={plan['project']} "
        f"name={plan['name']} "
        f"version={plan['version']} "
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
    task = Task.current_task()
    defaults = pipeline_ui_params(task_path, profile_path)
    task_params = task.get_parameters() if task else {}
    connected = {**defaults, **{key: value for key, value in task_params.items() if key in defaults}}
    plan = build_pipeline_plan(task_path=task_path, profile_path=profile_path, ui_params=connected)

    pipe = PipelineController(
        project=plan["project"],
        name=plan["name"],
        version=plan["version"],
    )
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
