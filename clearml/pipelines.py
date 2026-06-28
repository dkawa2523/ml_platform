from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


_CLEARML_DIR = Path(__file__).resolve().parent
if str(_CLEARML_DIR) not in sys.path:
    sys.path.insert(0, str(_CLEARML_DIR))

from _entrypoint_bootstrap import add_clearml_entrypoint_paths

add_clearml_entrypoint_paths()

from adapter import (
    apply_execution_image,
    as_bool,
    as_str_list,
    clearml_execution_image,
    clearml_projects,
    clearml_stage_project,
    clearml_tags,
    clearml_template_name,
    import_clearml_automation,
    import_clearml_sdk,
    import_clearml_symbol,
    prefixed_task_name,
    stage_task_label,
    validate_clearml_runtime,
)
from ml_platform_core.config import apply_overrides, load_yaml
from ml_platform_core.contracts import DomainPipelinePlan, DomainStepPlan
from ml_platform_core.stages import StageName, as_stage_name
from ml_platform_tabular.manifest import build_tabular_domain_plan
from ml_platform_tabular.policy import (
    ensemble_enabled_from_config,
    ensemble_methods_from_config,
    model_cfg_for_runtime,
    pipeline_runtime_defaults,
    runtime_model_suite,
    runtime_quality_mode,
    training_model_candidates,
    validate_primary_training_graph,
)


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


def _execution_image(profile: dict[str, Any]) -> str | None:
    return clearml_execution_image(profile.get("clearml", {}) or {})


def _remote_dataset_defaults(profile: dict[str, Any]) -> tuple[str | None, str | None]:
    clearml_cfg = profile.get("clearml", {}) or {}
    dataset_id = clearml_cfg.get("default_dataset_id")
    dataset_file = clearml_cfg.get("default_dataset_file")
    return dataset_id, dataset_file


def _training_pipeline_runtime_params(
    pipeline_cfg: dict[str, Any], profile: dict[str, Any] | None = None
) -> dict[str, Any]:
    profile = profile or {}
    remote_default_dataset_id, remote_default_dataset_file = _remote_dataset_defaults(profile)
    return pipeline_runtime_defaults(
        pipeline_cfg,
        remote_default_dataset_id=remote_default_dataset_id,
        remote_default_dataset_file=remote_default_dataset_file,
        use_clearml=bool(profile.get("runtime", {}).get("use_clearml")),
    )


def pipeline_runtime_params(
    task_path: str | Path = "config/tasks/tabular_pipeline.yaml",
    profile_path: str | Path = "config/profiles/clearml-dev.yaml",
) -> dict[str, Any]:
    pipeline_cfg = load_yaml(task_path)
    if "data" not in pipeline_cfg:
        raise ValueError("ClearML pipeline sync supports only the official stage-based training pipeline config.")
    return _training_pipeline_runtime_params(pipeline_cfg, load_yaml(profile_path))


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
                value = as_str_list(value)
            overrides[key] = value
    return overrides


def _split_overrides(params: dict[str, Any]) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for key in (
        "Split/method",
        "Split/group_column",
        "Split/time_column",
        "Split/valid_filter_column",
        "Split/valid_filter_value",
    ):
        if key in params and params.get(key) not in {None, ""}:
            overrides[key] = params[key]
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
            overrides[key] = as_str_list(params.get(key)) or []
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


def _step_model_params(step: DomainStepPlan) -> dict[str, Any]:
    raw = step.parameter_overrides.get("Model/params") or {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError(f"Domain step {step.name!r} Model/params must be a mapping.")
        return parsed
    raise ValueError(f"Domain step {step.name!r} Model/params must be a mapping.")


def _serialized_stage_overrides(overrides: dict[str, Any]) -> dict[str, Any]:
    serialized = dict(overrides)
    for key in ("Model/params", "Model/ensemble_methods"):
        if key in serialized and not isinstance(serialized[key], str):
            serialized[key] = _json(serialized[key])
    return serialized


def _render_domain_plan_steps(
    domain_plan: DomainPipelinePlan,
    *,
    templates_project: str,
    projects: dict[str, str],
    run_name: str,
    execution_queue: str,
) -> list[dict[str, Any]]:
    model_refs = [
        _model_ref(step.name, step.model_name, _step_model_params(step))
        for step in domain_plan.steps
        if step.stage_key == "train_model" and step.model_name is not None
    ]
    ensemble_refs = [
        _ensemble_ref(step.name, step.ensemble_method)
        for step in domain_plan.steps
        if step.stage_key == "build_ensemble" and step.ensemble_method is not None
    ]
    rendered_steps: list[dict[str, Any]] = []
    for step in domain_plan.steps:
        overrides = dict(step.parameter_overrides)
        if step.stage_key == "train_model":
            overrides = {**_preprocess_refs(), **overrides}
        elif step.stage_key == "build_ensemble":
            overrides = {
                **_preprocess_refs(),
                "Input/model_refs": _json(model_refs),
                **overrides,
            }
        elif step.stage_key == "evaluate_models":
            overrides = {
                **overrides,
                "Input/model_refs": _json(model_refs),
                "Input/ensemble_refs": _json(ensemble_refs) if ensemble_refs else None,
                "Input/ensemble_ref": _json(ensemble_refs[0]) if ensemble_refs else None,
            }
        rendered_steps.append(
            _stage_step(
                name=step.name,
                stage=step.stage_key,
                templates_project=templates_project,
                projects=projects,
                run_name=run_name,
                execution_queue=execution_queue,
                model_name=step.model_name,
                ensemble_method=step.ensemble_method,
                parents=list(step.parents),
                overrides=_serialized_stage_overrides(overrides),
            )
        )
    return rendered_steps


def _stage_step(
    *,
    name: str,
    stage: StageName | str,
    templates_project: str,
    projects: dict[str, str],
    run_name: str,
    execution_queue: str,
    model_name: str | None = None,
    ensemble_method: str | None = None,
    parents: list[str] | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stage_name = as_stage_name(str(stage))
    label = stage_task_label(stage_name, model_name, ensemble_method)
    parameter_override = {
        "Run/name": prefixed_task_name("stage", label, run_name),
        "Run/stage": stage_name,
        **(overrides or {}),
    }
    parameter_override = {key: value for key, value in parameter_override.items() if value is not None}
    return {
        "name": name,
        "parents": parents or [],
        "base_task_project": templates_project,
        "base_task_name": clearml_template_name(STAGE_TEMPLATE),
        "task_config": STAGE_TASK_CONFIG,
        "target_project": clearml_stage_project(projects, stage_name),
        "execution_queue": execution_queue,
        "pipeline_stage_group": label,
        "parameter_override": parameter_override,
        "tags": clearml_tags(
            "stage",
            internal=True,
            stage=stage_name,
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
    stage_queue = str(clearml_cfg.get("stage_queue") or clearml_cfg.get("queue") or "default")
    controller_queue = str(clearml_cfg.get("controller_queue") or clearml_cfg.get("pipeline_queue") or stage_queue)
    default_params = _training_pipeline_runtime_params(pipeline_cfg, profile)
    raw_ui_params = ui_params or {}
    explicit_params = {
        key: value
        for key, value in raw_ui_params.items()
        if key not in default_params or value != default_params.get(key)
    }
    effective_params = {**default_params, **(ui_params or {})}
    run_name = str(effective_params.get("Run/name") or pipeline_cfg.get("run", {}).get("name") or "run")
    model_suite = runtime_model_suite(effective_params)
    quality_mode = runtime_quality_mode(effective_params)
    model_cfg = model_cfg_for_runtime(pipeline_cfg, effective_params, explicit_params)
    validate_primary_training_graph(model_cfg)
    candidates = training_model_candidates(model_cfg)
    ensemble_cfg = model_cfg.get("ensemble", {}) or {}
    if not isinstance(ensemble_cfg, dict):
        ensemble_cfg = {}
    ensemble_enabled = ensemble_enabled_from_config(ensemble_cfg)
    ensemble_methods = ensemble_methods_from_config(ensemble_cfg)
    selection_metric = str(model_cfg.get("selection_metric") or "rmse")
    data_overrides = _data_overrides(effective_params)
    split_overrides = _split_overrides(effective_params)
    feature_overrides = _feature_overrides(effective_params)
    stage_common_overrides = {
        "Model/evaluation_metrics": effective_params.get("Model/evaluation_metrics"),
        "Output/report_plots": as_bool(effective_params.get("Output/report_plots"), default=True),
    }
    domain_plan = build_tabular_domain_plan(
        run_name=run_name,
        candidates=candidates,
        ensemble_methods=ensemble_methods,
        include_ensemble=ensemble_enabled,
        selection_metric=selection_metric,
        preprocess_overrides={
            **data_overrides,
            **split_overrides,
            **feature_overrides,
        },
        stage_common_overrides=stage_common_overrides,
        ensemble_top_k=int(ensemble_cfg.get("top_k") or 3),
    )
    steps = _render_domain_plan_steps(
        domain_plan,
        templates_project=templates_project,
        projects=projects,
        run_name=run_name,
        execution_queue=stage_queue,
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
        "queue": stage_queue,
        "stage_queue": stage_queue,
        "controller_queue": controller_queue,
        "candidate_models": [candidate["name"] for candidate in candidates],
        "model_suite": model_suite,
        "quality_mode": quality_mode,
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
            "ClearML pipeline planning requires a stage-based tabular_pipeline config with a data section."
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
        f"model_suite={plan.get('model_suite')} "
        f"quality_mode={plan.get('quality_mode')} "
        f"candidate_models={plan.get('candidate_models', [])} "
        f"ensemble_enabled={plan.get('ensemble_enabled')} "
        f"controller_queue={plan.get('controller_queue')} "
        f"stage_queue={plan.get('stage_queue')}"
    )
    for step in plan["steps"]:
        parents = ",".join(step["parents"]) if step["parents"] else "-"
        overrides = ", ".join(f"{key}={value}" for key, value in step["parameter_override"].items()) or "-"
        print(
            "DRY-RUN step: "
            f"name={step['name']} "
            f"parents={parents} "
            f"target_project={step.get('target_project')} "
            f"execution_queue={step.get('execution_queue')} "
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
        if step.get("execution_queue"):
            kwargs["execution_queue"] = step["execution_queue"]
        if step.get("pipeline_stage_group"):
            kwargs["stage"] = step["pipeline_stage_group"]
        pipe.add_step(**kwargs)


def _find_pipeline_draft(Task: Any, project_name: str, task_name: str):
    tasks = Task.get_tasks(task_name=task_name, allow_archived=False)
    for task in reversed(tasks):
        if getattr(task, "status", None) != "created":
            continue
        get_project_name = getattr(task, "get_project_name", None)
        if callable(get_project_name):
            candidate_project = str(get_project_name())
            if candidate_project != project_name and not candidate_project.startswith(f"{project_name}/.pipelines/"):
                continue
        task_type = (
            getattr(task, "task_type", None)
            or getattr(task, "type", None)
            or getattr(getattr(task, "data", None), "type", None)
        )
        if str(task_type) != str(Task.TaskTypes.controller):
            continue
        if "pipeline" not in (task.get_system_tags() or []):
            continue
        return task
    return None


def _delete_stale_pipeline_drafts(Task: Any, project_name: str, task_name: str, keep_id: str) -> None:
    for task in Task.get_tasks(task_name=task_name, allow_archived=True):
        if task.id == keep_id or getattr(task, "status", None) != "created":
            continue
        get_project_name = getattr(task, "get_project_name", None)
        if callable(get_project_name):
            candidate_project = str(get_project_name())
            if candidate_project != project_name and not candidate_project.startswith(f"{project_name}/.pipelines/"):
                continue
        task_type = (
            getattr(task, "task_type", None)
            or getattr(task, "type", None)
            or getattr(getattr(task, "data", None), "type", None)
        )
        if str(task_type) != str(Task.TaskTypes.controller):
            continue
        delete = getattr(task, "delete", None)
        if callable(delete):
            delete(delete_artifacts_and_models=False, raise_on_error=False)


def _delete_created_pipeline_draft(task: Any) -> None:
    """Delete a created pipeline draft so sync can rebuild the stored graph."""
    if task is None:
        return
    if getattr(task, "status", None) != "created":
        return
    delete = getattr(task, "delete", None)
    if callable(delete):
        delete(delete_artifacts_and_models=False, raise_on_error=False)


def _delete_legacy_pipeline_templates(Task: Any, names: list[str]) -> None:
    """Remove old created pipeline templates that can still appear as New Run entries."""
    for task_name in names:
        for task in Task.get_tasks(task_name=task_name, allow_archived=True):
            if getattr(task, "status", None) != "created":
                continue
            project_name = ""
            get_project_name = getattr(task, "get_project_name", None)
            if callable(get_project_name):
                project_name = str(get_project_name())
            if ".pipelines/" not in project_name:
                continue
            delete = getattr(task, "delete", None)
            if callable(delete):
                delete(delete_artifacts_and_models=False, raise_on_error=False)


def _apply_pipeline_template_metadata(
    task: Any,
    execution_image: str | None = None,
    *,
    controller_queue: str | None = None,
    stage_queue: str | None = None,
) -> None:
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
        set_tags(sorted(set(kept) | set(PIPELINE_TEMPLATE_TAGS)))
    else:
        add_tags = getattr(task, "add_tags", None)
        if callable(add_tags):
            add_tags(PIPELINE_TEMPLATE_TAGS)
    set_comment = getattr(task, "set_comment", None)
    if callable(set_comment):
        image_note = f" Execution image: {execution_image}." if execution_image else ""
        queue_note = ""
        if controller_queue or stage_queue:
            queue_note = f" Run the PipelineController on queue {controller_queue or '-'}; stages run on queue {stage_queue or '-'}."
        set_comment(
            "USER-FACING training pipeline template. Remote runs should use "
            "Input/clearml_dataset_id + Input/dataset_file, not Agent-local paths. "
            "Start with Basic/model_suite and Basic/use_ensemble; tune preprocessing "
            "with Features/*. Advanced users can still edit Model/candidates and "
            "Model/ensemble_methods. Synced templates install GBM packages into the "
            "remote execution venv."
            f"{queue_note}"
            f"{image_note}"
        )


def _apply_pipeline_run_metadata(task: Any, *, task_name: str | None = None) -> None:
    if task_name:
        set_name = getattr(task, "set_name", None)
        if callable(set_name):
            set_name(task_name)
    set_tags = getattr(task, "set_tags", None)
    tags = clearml_tags("pipeline", user_facing=True)
    if callable(set_tags):
        current = []
        get_tags = getattr(task, "get_tags", None)
        if callable(get_tags):
            current = list(get_tags() or [])
        kept = [tag for tag in current if not tag.startswith("run_type:") and tag not in {"internal:true"}]
        set_tags(sorted(set(kept) | set(tags)))
    else:
        add_tags = getattr(task, "add_tags", None)
        if callable(add_tags):
            add_tags(tags)


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
    plan = build_pipeline_plan(task_path=task_path, profile_path=profile_path, ui_params=params)
    if execution_image is None:
        execution_image = _execution_image(load_yaml(profile_path))
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
    plan = build_pipeline_plan(task_path=task_path, profile_path=profile_path, ui_params=connected, overrides=overrides)

    _add_plan_steps(pipe, plan)
    if task is not None:
        _apply_pipeline_run_metadata(task, task_name=plan["name"])
    pipe.start_locally(run_pipeline_steps_locally=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Register or dry-run the ClearML tabular training pipeline graph.")
    parser.add_argument(
        "--task", default="config/tasks/tabular_pipeline.yaml", help="Path to pipeline task config YAML."
    )
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
