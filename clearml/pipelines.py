from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CLEARML_DIR = Path(__file__).resolve().parent
for p in (str(CLEARML_DIR), str(REPO_ROOT / "pkgs/core/src"), str(REPO_ROOT / "pkgs/tabular/src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from adapter import (
    as_bool,
    as_candidates,
    as_dict,
    as_list,
    clearml_projects,
    clearml_stage_project,
    clearml_tags,
    clearml_template_name,
    import_clearml_automation,
    import_clearml_sdk,
    import_clearml_symbol,
    prefixed_task_name,
    stage_task_label,
)
from ml_platform_core.config import apply_overrides, load_yaml
from ml_platform_tabular.models import candidate_params, model_candidates


PIPELINE_ARG_PREFIX = "Args/"
STAGE_TASK_CONFIG = "config/tasks/tabular_stage.yaml"
STAGE_TEMPLATE = "tabular_stage_template"
PIPELINE_TEMPLATE_TAGS = clearml_tags("template", user_facing=True)


def _artifact_ref(step_name: str, artifact_name: str) -> str:
    return "${" + f"{step_name}.artifacts.{artifact_name}.url" + "}"


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _project_layout(profile: dict[str, Any]) -> dict[str, str]:
    clearml_cfg = profile.get("clearml", {})
    return clearml_projects(clearml_cfg)


def _pipeline_model_cfg(pipeline_cfg: dict[str, Any], ui_params: dict[str, Any] | None = None) -> dict[str, Any]:
    model_cfg = deepcopy(pipeline_cfg.get("model", {}) or {})
    ui_params = ui_params or {}
    if "Model/candidates" in ui_params:
        model_cfg["candidates"] = as_candidates(ui_params.get("Model/candidates"))
    if "Model/model_params_by_name" in ui_params:
        model_cfg["params"] = as_dict(ui_params.get("Model/model_params_by_name"))
    elif "Model/params" in ui_params:
        model_cfg["params"] = as_dict(ui_params.get("Model/params"))
    if "Model/selection_metric" in ui_params and ui_params.get("Model/selection_metric"):
        model_cfg["selection_metric"] = ui_params["Model/selection_metric"]
    if "Model/ensemble_enabled" in ui_params:
        model_cfg.setdefault("ensemble", {})["enabled"] = as_bool(ui_params.get("Model/ensemble_enabled"))
    if "Model/ensemble_methods" in ui_params:
        model_cfg.setdefault("ensemble", {})["methods"] = as_list(ui_params.get("Model/ensemble_methods")) or []
    if "Model/ensemble_method" in ui_params and ui_params.get("Model/ensemble_method"):
        model_cfg.setdefault("ensemble", {})["method"] = ui_params["Model/ensemble_method"]
    if "Model/ensemble_top_k" in ui_params and ui_params.get("Model/ensemble_top_k") not in {None, ""}:
        model_cfg.setdefault("ensemble", {})["top_k"] = int(ui_params["Model/ensemble_top_k"])
    return model_cfg


def _remote_dataset_defaults(profile: dict[str, Any]) -> tuple[str | None, str | None]:
    clearml_cfg = profile.get("clearml", {}) or {}
    dataset_id = clearml_cfg.get("default_dataset_id")
    dataset_file = clearml_cfg.get("default_dataset_file")
    return dataset_id, dataset_file


def _training_pipeline_ui_params(pipeline_cfg: dict[str, Any], profile: dict[str, Any] | None = None) -> dict[str, Any]:
    run = pipeline_cfg.get("run", {})
    data = pipeline_cfg.get("data", {})
    split = pipeline_cfg.get("split", {}) or {}
    features = pipeline_cfg.get("features", {}) or {}
    model = pipeline_cfg.get("model", {})
    metrics = pipeline_cfg.get("metrics", {}) or {}
    output = pipeline_cfg.get("output", {}) or {}
    ensemble = model.get("ensemble", {}) or {}
    if not isinstance(ensemble, dict):
        ensemble = {}
    profile = profile or {}
    remote_default_dataset_id, remote_default_dataset_file = _remote_dataset_defaults(profile)
    use_clearml = bool(profile.get("runtime", {}).get("use_clearml"))
    clearml_dataset_id = data.get("clearml_dataset_id")
    dataset_file = data.get("dataset_file")
    local_path = data.get("local_path")
    if use_clearml and remote_default_dataset_id and not clearml_dataset_id:
        clearml_dataset_id = remote_default_dataset_id
        dataset_file = dataset_file or remote_default_dataset_file
        local_path = ""
    return {
        "Run/name": run.get("name"),
        "Run/seed": run.get("seed"),
        "Split/valid_size": split.get("valid_size", 0.2),
        "Input/local_path": local_path,
        "Input/clearml_dataset_id": clearml_dataset_id,
        "Input/dataset_file": dataset_file,
        "Input/target_column": data.get("target_column"),
        "Input/feature_columns": data.get("feature_columns"),
        "Input/id_columns": data.get("id_columns", []),
        "Features/preset": features.get("preset", "basic"),
        "Features/numeric_impute_strategy": features.get("numeric_impute_strategy", "median"),
        "Features/categorical_impute_strategy": features.get("categorical_impute_strategy", "missing_token"),
        "Features/categorical_encoder": features.get("categorical_encoder", "onehot"),
        "Features/scaling": features.get("scaling", "standard"),
        "Features/drop_columns": _json(features.get("drop_columns", []) or []),
        "Features/passthrough_columns": _json(features.get("passthrough_columns", []) or []),
        "Model/candidates": _json(model.get("candidates", []) or []),
        "Model/model_params_by_name": _json(model.get("params", {}) or {}),
        "Model/evaluation_metrics": _json(metrics.get("names", []) or []),
        "Model/selection_metric": model.get("selection_metric", "rmse"),
        "Model/ensemble_enabled": as_bool(ensemble.get("enabled")),
        "Model/ensemble_methods": _json(ensemble.get("methods", [ensemble.get("method", "mean_topk")]) or []),
        "Model/ensemble_top_k": int(ensemble.get("top_k") or 3),
        "Output/report_plots": as_bool(output.get("report_plots"), default=True),
    }


def pipeline_ui_params(
    task_path: str | Path = "config/tasks/tabular_pipeline.yaml",
    profile_path: str | Path = "config/profiles/clearml-dev.yaml",
) -> dict[str, Any]:
    pipeline_cfg = load_yaml(task_path)
    if "data" not in pipeline_cfg:
        raise ValueError("ClearML pipeline sync supports only the official stage-based training pipeline config.")
    return _training_pipeline_ui_params(pipeline_cfg, load_yaml(profile_path))


def pipeline_arg_params(params: dict[str, Any]) -> dict[str, Any]:
    """Mirror UI params under Args/* so ClearML Pipeline New Run exposes them."""
    return {f"{PIPELINE_ARG_PREFIX}{key}": value for key, value in params.items()}


def pipeline_params_from_task(defaults: dict[str, Any], task_params: dict[str, Any]) -> dict[str, Any]:
    """Read Pipeline New Run values, preferring Args/* over template defaults."""
    connected = dict(defaults)
    for key in defaults:
        if key in task_params:
            connected[key] = task_params[key]
        args_key = f"{PIPELINE_ARG_PREFIX}{key}"
        if args_key in task_params:
            connected[key] = task_params[args_key]
    return connected


def _add_pipeline_args(pipe: Any, params: dict[str, Any]) -> None:
    for key, value in params.items():
        pipe.add_parameter(name=key, default=value)


def _data_overrides(params: dict[str, Any]) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for key in (
        "Input/local_path",
        "Input/clearml_dataset_id",
        "Input/dataset_file",
        "Input/target_column",
        "Input/feature_columns",
        "Input/id_columns",
    ):
        if key in params:
            value = params[key]
            if key in {"Input/feature_columns", "Input/id_columns"}:
                value = as_list(value)
            overrides[key] = value
    return overrides


def _split_overrides(params: dict[str, Any]) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    if "Split/valid_size" in params and params.get("Split/valid_size") not in {None, ""}:
        overrides["Split/valid_size"] = float(params["Split/valid_size"])
    return overrides


def _feature_overrides(params: dict[str, Any]) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for key in (
        "Features/preset",
        "Features/numeric_impute_strategy",
        "Features/categorical_impute_strategy",
        "Features/categorical_encoder",
        "Features/scaling",
    ):
        if key in params and params.get(key) not in {None, ""}:
            overrides[key] = params[key]
    for key in ("Features/drop_columns", "Features/passthrough_columns"):
        if key in params:
            overrides[key] = as_list(params.get(key)) or []
    return overrides


def _preprocess_refs() -> dict[str, str]:
    return {
        "Input/preprocess_bundle": _artifact_ref("preprocess_features", "preprocess_bundle"),
        "Input/feature_spec": _artifact_ref("preprocess_features", "feature_spec"),
        "Input/processed_train": _artifact_ref("preprocess_features", "processed_train"),
        "Input/processed_valid": _artifact_ref("preprocess_features", "processed_valid"),
    }


def _model_ref(step_name: str, model_name: str, model_params: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": step_name,
        "model_name": model_name,
        "model_params": model_params,
        "artifact_kind": "model",
        "model": _artifact_ref(step_name, "model"),
        "model_info": _artifact_ref(step_name, "model_info"),
        "metrics": _artifact_ref(step_name, "metrics"),
        "validation_predictions": _artifact_ref(step_name, "validation_predictions"),
    }


def _ensemble_methods(ensemble_cfg: dict[str, Any]) -> list[str]:
    raw = ensemble_cfg.get("methods")
    if raw is None or raw == "":
        raw = [ensemble_cfg.get("method") or "mean_topk"]
    methods = as_list(raw) or []
    return methods or ["mean_topk"]


def _ensemble_ref(step_name: str, method: str | None = None) -> dict[str, Any]:
    suffix = f"_{method}" if method else ""
    return {
        "stage": step_name,
        "model_name": method or "mean_topk",
        "ensemble_method": method,
        "artifact_kind": "ensemble",
        "model": _artifact_ref(step_name, f"model{suffix}"),
        "model_info": _artifact_ref(step_name, f"model_info{suffix}"),
        "ensemble_info": _artifact_ref(step_name, f"ensemble_info{suffix}"),
        "metrics": _artifact_ref(step_name, f"metrics{suffix}"),
        "ensemble_predictions": _artifact_ref(step_name, f"ensemble_predictions{suffix}"),
    }


def _stage_step(
    *,
    name: str,
    stage: str,
    templates_project: str,
    projects: dict[str, str],
    run_name: str,
    model_name: str | None = None,
    ensemble_method: str | None = None,
    parents: list[str] | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    label = stage_task_label(stage, model_name, ensemble_method)
    parameter_override = {
        "Run/name": prefixed_task_name("stage", label, run_name),
        "Run/stage": stage,
        **(overrides or {}),
    }
    parameter_override = {key: value for key, value in parameter_override.items() if value is not None}
    return {
        "name": name,
        "parents": parents or [],
        "base_task_project": templates_project,
        "base_task_name": clearml_template_name(STAGE_TEMPLATE),
        "task_config": STAGE_TASK_CONFIG,
        "target_project": clearml_stage_project(projects, stage),
        "pipeline_stage_group": label,
        "parameter_override": parameter_override,
        "tags": clearml_tags(
            "stage",
            internal=True,
            stage=stage,
            model=model_name,
            ensemble=ensemble_method,
        ),
    }


def _build_training_plan(
    pipeline_cfg: dict[str, Any],
    profile: dict[str, Any],
    task_path: str | Path,
    profile_path: str | Path,
    ui_params: dict[str, Any] | None,
) -> dict[str, Any]:
    projects = _project_layout(profile)
    templates_project = projects["templates"]
    pipelines_project = projects["pipelines"]
    stages_project = projects["stages"]
    clearml_cfg = profile.get("clearml", {})
    default_params = _training_pipeline_ui_params(pipeline_cfg, profile)
    effective_params = {**default_params, **(ui_params or {})}
    run_name = str(effective_params.get("Run/name") or pipeline_cfg.get("run", {}).get("name") or "run")
    model_cfg = _pipeline_model_cfg(pipeline_cfg, effective_params)
    search_cfg = model_cfg.get("search", {}) or {}
    if not isinstance(search_cfg, dict):
        search_cfg = {}
    if as_bool(search_cfg.get("enabled")):
        raise ValueError(
            "model.search.enabled=true is future/experimental and is not part of the "
            "primary ClearML training pipeline graph. Remove model.search or set enabled=false for "
            "preprocess_features -> train_<model>* -> build_ensemble_<method>* -> evaluate_models."
        )
    candidates = model_candidates(model_cfg)
    if not candidates:
        raise ValueError("Training pipeline requires at least one model candidate.")

    ensemble_cfg = model_cfg.get("ensemble", {}) or {}
    if not isinstance(ensemble_cfg, dict):
        ensemble_cfg = {}
    ensemble_enabled = as_bool(ensemble_cfg.get("enabled"))
    ensemble_methods = _ensemble_methods(ensemble_cfg)
    selection_metric = str(model_cfg.get("selection_metric") or "rmse")
    data_overrides = _data_overrides(effective_params)
    split_overrides = _split_overrides(effective_params)
    feature_overrides = _feature_overrides(effective_params)
    stage_common_overrides = {
        "Model/evaluation_metrics": effective_params.get("Model/evaluation_metrics"),
        "Output/report_plots": as_bool(effective_params.get("Output/report_plots"), default=True),
    }

    steps: list[dict[str, Any]] = [
        _stage_step(
            name="preprocess_features",
            stage="preprocess_features",
            templates_project=templates_project,
            projects=projects,
            run_name=run_name,
            overrides={
                **data_overrides,
                **split_overrides,
                **feature_overrides,
                **stage_common_overrides,
            },
        )
    ]

    model_refs: list[dict[str, Any]] = []
    train_steps: list[str] = []
    for candidate in candidates:
        model_name = candidate["name"]
        step_name = f"train_{model_name}"
        model_params = candidate_params(model_cfg.get("params") or {}, model_name)
        train_steps.append(step_name)
        model_refs.append(_model_ref(step_name, model_name, model_params))
        steps.append(
            _stage_step(
                name=step_name,
                stage="train_model",
                templates_project=templates_project,
                projects=projects,
                run_name=run_name,
                model_name=model_name,
                parents=["preprocess_features"],
                overrides={
                    **_preprocess_refs(),
                    **stage_common_overrides,
                    "Model/name": model_name,
                    "Model/params": _json(model_params),
                    "Model/selection_metric": selection_metric,
                },
            )
        )

    parents_for_evaluate = list(train_steps)
    ensemble_refs = []
    ensemble_steps: list[str] = []
    if ensemble_enabled:
        for method in ensemble_methods:
            step_name = f"build_ensemble_{method}"
            ensemble_steps.append(step_name)
            ensemble_refs.append(_ensemble_ref(step_name, method))
            steps.append(
                _stage_step(
                    name=step_name,
                    stage="build_ensemble",
                    templates_project=templates_project,
                    projects=projects,
                    run_name=run_name,
                    ensemble_method=method,
                    parents=train_steps,
                    overrides={
                        **_preprocess_refs(),
                        **stage_common_overrides,
                        "Input/model_refs": _json(model_refs),
                        "Model/selection_metric": selection_metric,
                        "Model/ensemble_enabled": True,
                        "Model/ensemble_methods": _json([method]),
                        "Model/ensemble_method": method,
                        "Model/ensemble_top_k": int(ensemble_cfg.get("top_k") or 3),
                    },
                )
            )
        parents_for_evaluate.extend(ensemble_steps)

    steps.append(
        _stage_step(
            name="evaluate_models",
            stage="evaluate_models",
            templates_project=templates_project,
            projects=projects,
            run_name=run_name,
            parents=parents_for_evaluate,
            overrides={
                **stage_common_overrides,
                "Input/model_refs": _json(model_refs),
                "Input/ensemble_refs": _json(ensemble_refs) if ensemble_refs else None,
                "Input/ensemble_ref": _json(ensemble_refs[0]) if ensemble_refs else None,
                "Model/selection_metric": selection_metric,
            },
        )
    )

    return {
        "kind": "training",
        "project": pipelines_project,
        "stage_project": stages_project,
        "stage_projects": {
            "preprocess": projects["preprocess"],
            "train": projects["train"],
            "ensemble": projects["ensemble"],
            "evaluate": projects["evaluate"],
        },
        "name": prefixed_task_name("pipeline", "tabular_train_pipeline", run_name),
        "version": "0.2.0",
        "training_flow": "preprocess_train_ensemble_evaluate" if ensemble_enabled else "preprocess_train_evaluate",
        "queue": clearml_cfg.get("queue", "default"),
        "candidate_models": [candidate["name"] for candidate in candidates],
        "ensemble_enabled": ensemble_enabled,
        "steps": steps,
        "task_config": str(task_path),
        "profile_config": str(profile_path),
        "tags": clearml_tags("pipeline", user_facing=True),
    }


def build_pipeline_plan(
    task_path: str | Path = "config/tasks/tabular_pipeline.yaml",
    profile_path: str | Path = "config/profiles/clearml-dev.yaml",
    ui_params: dict[str, Any] | None = None,
    overrides: list[str] | dict[str, Any] | None = None,
) -> dict[str, Any]:
    pipeline_cfg = apply_overrides(load_yaml(task_path), overrides)
    profile = load_yaml(profile_path)
    if "data" not in pipeline_cfg:
        raise ValueError(
            "ClearML pipeline planning supports only the official stage-based training pipeline. "
            "The legacy train/eval/infer full-run flow is sync-excluded."
        )
    return _build_training_plan(pipeline_cfg, profile, task_path, profile_path, ui_params)


def print_pipeline_plan(plan: dict[str, Any]) -> None:
    print(
        "DRY-RUN pipeline: "
        f"kind={plan['kind']} "
        f"project={plan['project']} "
        f"stage_project={plan['stage_project']} "
        f"stage_projects={plan.get('stage_projects', {})} "
        f"name={plan['name']} "
        f"version={plan['version']} "
        f"training_flow={plan['training_flow']} "
        f"queue={plan['queue']}"
    )
    for step in plan["steps"]:
        parents = ",".join(step["parents"]) if step["parents"] else "-"
        overrides = ", ".join(f"{key}={value}" for key, value in step["parameter_override"].items()) or "-"
        print(
            "DRY-RUN step: "
            f"name={step['name']} "
            f"parents={parents} "
            f"target_project={step.get('target_project')} "
            f"template={step['base_task_project']}/{step['base_task_name']} "
            f"task_config={step['task_config']} "
            f"parameter_override=[{overrides}] "
            f"tags={step.get('tags', [])}"
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
        if step.get("pipeline_stage_group"):
            kwargs["stage"] = step["pipeline_stage_group"]
        pipe.add_step(**kwargs)


def _find_pipeline_draft(Task: Any, project_name: str, task_name: str):
    tasks = Task.get_tasks(project_name=project_name, task_name=task_name, allow_archived=False)
    for task in reversed(tasks):
        if getattr(task, "status", None) != "created":
            continue
        if str(getattr(task, "task_type", "")) != str(Task.TaskTypes.controller):
            continue
        if "pipeline" not in (task.get_system_tags() or []):
            continue
        return task
    return None


def _apply_pipeline_template_metadata(task: Any) -> None:
    add_tags = getattr(task, "add_tags", None)
    set_tags = getattr(task, "set_tags", None)
    if callable(add_tags):
        add_tags(PIPELINE_TEMPLATE_TAGS)
    elif callable(set_tags):
        current = []
        get_tags = getattr(task, "get_tags", None)
        if callable(get_tags):
            current = list(get_tags() or [])
        set_tags(sorted(set(current) | set(PIPELINE_TEMPLATE_TAGS)))
    set_comment = getattr(task, "set_comment", None)
    if callable(set_comment):
        set_comment(
            "USER-FACING training pipeline template. Remote runs should use "
            "Input/clearml_dataset_id + Input/dataset_file, not Agent-local paths. "
            "Tune preprocessing with Features/* and ensembles with Model/ensemble_methods. "
            "Add lightgbm/xgboost/catboost to Model/candidates only when the Agent has pkgs/tabular[gbm]."
        )


def _apply_pipeline_run_metadata(task: Any, *, task_name: str | None = None) -> None:
    if task_name:
        set_name = getattr(task, "set_name", None)
        if callable(set_name):
            set_name(task_name)
    add_tags = getattr(task, "add_tags", None)
    set_tags = getattr(task, "set_tags", None)
    tags = clearml_tags("pipeline", user_facing=True)
    if callable(add_tags):
        add_tags(tags)
    elif callable(set_tags):
        current = []
        get_tags = getattr(task, "get_tags", None)
        if callable(get_tags):
            current = list(get_tags() or [])
        set_tags(sorted(set(current) | set(tags)))


def sync_pipeline_draft(
    task_path: str | Path = "config/tasks/tabular_pipeline.yaml",
    profile_path: str | Path = "config/profiles/clearml-dev.yaml",
    *,
    template_name: str = "tabular_train_pipeline_template",
    repository: str | None = None,
    branch: str | None = None,
    working_dir: str | None = None,
    packages: list[str] | None = None,
):
    """Create a Pipeline-tab draft for the stage-based training graph."""
    clearml_sdk = import_clearml_sdk()
    Task = clearml_sdk.Task
    display_name = clearml_template_name(template_name)
    params = pipeline_ui_params(task_path, profile_path)
    plan = build_pipeline_plan(task_path=task_path, profile_path=profile_path, ui_params=params)
    existing = _find_pipeline_draft(Task, plan["project"], display_name)
    draft_params = {**params, **pipeline_arg_params(params)}
    if existing is not None:
        _set_pipeline_script_with_compat(
            existing,
            repository=repository or ".",
            branch=branch or "main",
            working_dir=working_dir or ".",
            task_config=task_path,
            profile_path=profile_path,
        )
        existing.update_parameters(draft_params)
        if packages:
            existing.set_packages(packages)
        _apply_pipeline_template_metadata(existing)
        return existing

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
    _apply_pipeline_template_metadata(pipe.task)
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
    defaults = pipeline_ui_params(task_path, profile_path)
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
    plan = build_pipeline_plan(task_path=task_path, profile_path=profile_path, ui_params=connected, overrides=overrides)

    _add_plan_steps(pipe, plan)
    if task is not None:
        _apply_pipeline_run_metadata(task, task_name=plan["name"])
    pipe.start_locally(run_pipeline_steps_locally=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Register or dry-run the ClearML tabular training pipeline graph.")
    parser.add_argument("--task", default="config/tasks/tabular_pipeline.yaml", help="Path to pipeline task config YAML.")
    parser.add_argument("--profile", default="config/profiles/clearml-dev.yaml", help="Path to profile config YAML.")
    parser.add_argument("--dry-run", action="store_true", help="Print the pipeline DAG without requiring ClearML SDK.")
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        help="Override config value with dotted path syntax for local dry-run inspection.",
    )
    args = parser.parse_args()

    plan = build_pipeline_plan(task_path=args.task, profile_path=args.profile, overrides=args.overrides)
    if args.dry_run:
        print_pipeline_plan(plan)
        return
    register_tabular_pipeline(task_path=args.task, profile_path=args.profile, overrides=args.overrides)


if __name__ == "__main__":
    main()
