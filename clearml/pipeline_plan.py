from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from adapter import (
    clearml_execution_image,
    clearml_projects,
    clearml_stage_project,
    clearml_tags,
    clearml_template_name,
    prefixed_task_name,
    stage_task_label,
)
from ml_platform_core.config import apply_overrides, load_yaml
from ml_platform_core.contracts import DomainPipelinePlan, DomainStepPlan
from ml_platform_core.stages import StageName, as_stage_name
from ml_platform_core.value_coercion import as_bool, as_str_list
from ml_platform_tabular.domain_plan import build_tabular_domain_plan
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
from param_bindings import runtime_keys_for_config_section
from param_transport import (
    coerce_connected_params,
    connected_params_from_task,
    normalize_clearml_param_value,
    prefixed_connected_params,
)


PIPELINE_ARG_PREFIX = "Args/"
STAGE_TASK_CONFIG = "config/tasks/tabular_stage.yaml"
STAGE_TEMPLATE = "tabular_stage_template"
MODEL_REF_ARTIFACTS = ("model", "model_info", "metrics", "validation_predictions")
ENSEMBLE_REF_ARTIFACTS = ("model", "model_info", "ensemble_info", "metrics", "ensemble_predictions")
PIPELINE_DRY_RUN_KEYS = (
    "kind",
    "project",
    "stage_project",
    "stage_projects",
    "name",
    "version",
    "training_flow",
    "model_suite",
    "quality_mode",
    "candidate_models",
    "ensemble_enabled",
    "controller_queue",
    "stage_queue",
)


def execution_image(profile: dict[str, Any]) -> str | None:
    return clearml_execution_image(profile.get("clearml", {}) or {})


def pipeline_runtime_params(
    task_path: str | Path = "config/tasks/tabular_pipeline.yaml",
    profile_path: str | Path = "config/profiles/clearml-dev.yaml",
) -> dict[str, Any]:
    pipeline_cfg = load_yaml(task_path)
    if "data" not in pipeline_cfg:
        raise ValueError("ClearML pipeline sync supports only the official stage-based training pipeline config.")
    return _training_pipeline_runtime_params(pipeline_cfg, load_yaml(profile_path))


def pipeline_arg_params(params: dict[str, Any]) -> dict[str, Any]:
    """Mirror runtime params under Args/* so ClearML Pipeline New Run exposes them."""
    return prefixed_connected_params(params, prefix=PIPELINE_ARG_PREFIX)


def pipeline_params_from_task(defaults: dict[str, Any], task_params: dict[str, Any]) -> dict[str, Any]:
    """Read Pipeline New Run values, preferring Args/* over template defaults."""
    return connected_params_from_task(defaults, task_params, prefix=PIPELINE_ARG_PREFIX)


def build_pipeline_plan(
    task_path: str | Path = "config/tasks/tabular_pipeline.yaml",
    profile_path: str | Path = "config/profiles/clearml-dev.yaml",
    runtime_params: dict[str, Any] | None = None,
    overrides: list[str] | dict[str, Any] | None = None,
) -> dict[str, Any]:
    pipeline_cfg = apply_overrides(load_yaml(task_path), overrides)
    profile = load_yaml(profile_path)
    if "data" not in pipeline_cfg:
        raise ValueError(
            "ClearML pipeline planning requires a stage-based tabular_pipeline config with a data section."
        )
    return _build_training_plan(pipeline_cfg, profile, task_path, profile_path, runtime_params)


def print_pipeline_plan(plan: dict[str, Any]) -> None:
    print("DRY-RUN pipeline: " + _format_fields(_pipeline_dry_run_fields(plan)))
    for step in plan["steps"]:
        parents = ",".join(step["parents"]) if step["parents"] else "-"
        overrides = ", ".join(f"{key}={value}" for key, value in step["parameter_override"].items()) or "-"
        print("DRY-RUN step: " + _format_fields(_step_dry_run_fields(step, parents, overrides)))


def _format_fields(fields: tuple[tuple[str, Any], ...]) -> str:
    return " ".join(f"{key}={value}" for key, value in fields)


def _pipeline_dry_run_fields(plan: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    return tuple((key, plan.get(key)) for key in PIPELINE_DRY_RUN_KEYS)


def _step_dry_run_fields(step: dict[str, Any], parents: str, overrides: str) -> tuple[tuple[str, Any], ...]:
    return (
        ("name", step["name"]),
        ("parents", parents),
        ("target_project", step.get("target_project")),
        ("execution_queue", step.get("execution_queue")),
        ("template", f"{step['base_task_project']}/{step['base_task_name']}"),
        ("task_config", step["task_config"]),
        ("parameter_override", f"[{overrides}]"),
        ("tags", step.get("tags", [])),
    )


def _artifact_ref(step_name: str, artifact_name: str) -> str:
    return "${" + f"{step_name}.artifacts.{artifact_name}.url" + "}"


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _training_pipeline_runtime_params(
    pipeline_cfg: dict[str, Any], profile: dict[str, Any] | None = None
) -> dict[str, Any]:
    profile = profile or {}
    clearml_cfg = profile.get("clearml", {}) or {}
    return pipeline_runtime_defaults(
        pipeline_cfg,
        remote_default_dataset_id=clearml_cfg.get("default_dataset_id"),
        remote_default_dataset_file=clearml_cfg.get("default_dataset_file"),
        use_clearml=bool(profile.get("runtime", {}).get("use_clearml")),
    )


def _data_overrides(params: dict[str, Any]) -> dict[str, Any]:
    return _section_overrides(params, "data", include_empty=True)


def _split_overrides(params: dict[str, Any]) -> dict[str, Any]:
    return _section_overrides(params, "split", float_keys=("Split/valid_size",))


def _feature_overrides(params: dict[str, Any]) -> dict[str, Any]:
    return _section_overrides(params, "features")


def _section_overrides(
    params: dict[str, Any],
    section: str,
    *,
    include_empty: bool = False,
    float_keys: tuple[str, ...] = (),
) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    list_keys = set(runtime_keys_for_config_section(section, value_type="list"))
    for key in runtime_keys_for_config_section(section):
        if key not in params:
            continue
        value = params[key]
        if key in list_keys:
            overrides[key] = as_str_list(value) or []
        elif include_empty or value not in {None, ""}:
            overrides[key] = float(value) if key in float_keys else value
    return overrides


def _artifact_ref_map(
    step: DomainStepPlan,
    *,
    suffix: str = "",
    required: tuple[str, ...] = (),
) -> dict[str, str]:
    refs = {artifact: _artifact_ref(step.name, f"{artifact}{suffix}") for artifact in step.expected_artifacts}
    missing = [artifact for artifact in required if artifact not in refs]
    if missing:
        raise ValueError(f"Domain step {step.name!r} is missing expected artifact(s): {', '.join(missing)}.")
    return refs


def _preprocess_refs(domain_plan: DomainPipelinePlan) -> dict[str, str]:
    preprocess = _step_by_stage(domain_plan, "preprocess_features")
    return {f"Input/{artifact}": ref for artifact, ref in _artifact_ref_map(preprocess).items()}


def _step_by_stage(domain_plan: DomainPipelinePlan, stage: str) -> DomainStepPlan:
    return next(step for step in domain_plan.steps if step.stage_key == stage)


def _model_ref(step: DomainStepPlan, model_params: dict[str, Any]) -> dict[str, Any]:
    refs = _artifact_ref_map(step, required=MODEL_REF_ARTIFACTS)
    return {
        "stage": step.name,
        "model_name": step.model_name,
        "model_params": model_params,
        "artifact_kind": "model",
        **{artifact: refs[artifact] for artifact in MODEL_REF_ARTIFACTS},
    }


def _ensemble_reference(step: DomainStepPlan) -> dict[str, Any]:
    method = step.ensemble_method
    suffix = f"_{method}" if method else ""
    refs = _artifact_ref_map(step, suffix=suffix, required=ENSEMBLE_REF_ARTIFACTS)
    return {
        "stage": step.name,
        "model_name": method or "mean_topk",
        "ensemble_method": method,
        "artifact_kind": "ensemble",
        **{artifact: refs[artifact] for artifact in ENSEMBLE_REF_ARTIFACTS},
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
    for key in ("Model/params", "Model/ensemble_methods", "Model/evaluation_metrics"):
        if key in serialized and not isinstance(serialized[key], str):
            serialized[key] = normalize_clearml_param_value(serialized[key])
    return serialized


def _render_domain_plan_steps(
    domain_plan: DomainPipelinePlan,
    *,
    templates_project: str,
    projects: dict[str, str],
    run_name: str,
    execution_queue: str,
) -> list[dict[str, Any]]:
    preprocess_refs = _preprocess_refs(domain_plan)
    model_refs = _model_refs(domain_plan)
    ensemble_refs = _ensemble_refs(domain_plan)
    return [
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
            overrides=_serialized_stage_overrides(
                _domain_step_overrides(step, preprocess_refs, model_refs, ensemble_refs)
            ),
        )
        for step in domain_plan.steps
    ]


def _model_refs(domain_plan: DomainPipelinePlan) -> list[dict[str, Any]]:
    return [
        _model_ref(step, _step_model_params(step))
        for step in domain_plan.steps
        if step.stage_key == "train_model" and step.model_name is not None
    ]


def _ensemble_refs(domain_plan: DomainPipelinePlan) -> list[dict[str, Any]]:
    return [
        _ensemble_reference(step)
        for step in domain_plan.steps
        if step.stage_key == "build_ensemble" and step.ensemble_method is not None
    ]


def _domain_step_overrides(
    step: DomainStepPlan,
    preprocess_refs: dict[str, str],
    model_refs: list[dict[str, Any]],
    ensemble_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    overrides = dict(step.parameter_overrides)
    if step.stage_key == "train_model":
        return {**preprocess_refs, **overrides}
    if step.stage_key == "build_ensemble":
        return {**preprocess_refs, "Input/model_refs": _json(model_refs), **overrides}
    if step.stage_key == "evaluate_models":
        return {
            **overrides,
            "Input/model_refs": _json(model_refs),
            "Input/ensemble_refs": _json(ensemble_refs) if ensemble_refs else None,
        }
    return overrides


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
    runtime_params: dict[str, Any] | None,
) -> dict[str, Any]:
    projects = clearml_projects(profile.get("clearml", {}))
    templates_project = projects["templates"]
    pipelines_project = projects["pipelines"]
    stages_project = projects["stages"]
    stage_queue, controller_queue = _pipeline_queues(profile)
    effective_params, explicit_params = _runtime_param_sets(pipeline_cfg, profile, runtime_params)
    run_name = str(effective_params.get("Run/name") or pipeline_cfg.get("run", {}).get("name") or "run")
    model_suite = runtime_model_suite(effective_params)
    quality_mode = runtime_quality_mode(effective_params)
    model_cfg, candidates, ensemble_cfg = _runtime_model_plan(pipeline_cfg, effective_params, explicit_params)
    ensemble_enabled = ensemble_enabled_from_config(ensemble_cfg)
    domain_plan = _build_domain_plan(run_name, candidates, ensemble_cfg, ensemble_enabled, effective_params, model_cfg)
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


def _pipeline_queues(profile: dict[str, Any]) -> tuple[str, str]:
    clearml_cfg = profile.get("clearml", {})
    stage_queue = str(clearml_cfg.get("stage_queue") or clearml_cfg.get("queue") or "default")
    controller_queue = str(clearml_cfg.get("controller_queue") or clearml_cfg.get("pipeline_queue") or stage_queue)
    return stage_queue, controller_queue


def _runtime_param_sets(
    pipeline_cfg: dict[str, Any],
    profile: dict[str, Any],
    runtime_params: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    default_params = coerce_connected_params(_training_pipeline_runtime_params(pipeline_cfg, profile))
    raw_runtime_params = coerce_connected_params(runtime_params or {})
    explicit_params = {
        key: value
        for key, value in raw_runtime_params.items()
        if key not in default_params or value != default_params.get(key)
    }
    return {**default_params, **raw_runtime_params}, explicit_params


def _runtime_model_plan(
    pipeline_cfg: dict[str, Any],
    effective_params: dict[str, Any],
    explicit_params: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    model_cfg = model_cfg_for_runtime(pipeline_cfg, effective_params, explicit_params)
    validate_primary_training_graph(model_cfg)
    candidates = training_model_candidates(model_cfg)
    ensemble_cfg = model_cfg.get("ensemble", {}) or {}
    if not isinstance(ensemble_cfg, dict):
        ensemble_cfg = {}
    return model_cfg, candidates, ensemble_cfg


def _build_domain_plan(
    run_name: str,
    candidates: list[dict[str, Any]],
    ensemble_cfg: dict[str, Any],
    ensemble_enabled: bool,
    effective_params: dict[str, Any],
    model_cfg: dict[str, Any],
) -> DomainPipelinePlan:
    return build_tabular_domain_plan(
        run_name=run_name,
        candidates=candidates,
        ensemble_methods=ensemble_methods_from_config(ensemble_cfg),
        include_ensemble=ensemble_enabled,
        selection_metric=str(model_cfg.get("selection_metric") or "rmse"),
        preprocess_overrides={
            **_data_overrides(effective_params),
            **_split_overrides(effective_params),
            **_feature_overrides(effective_params),
        },
        stage_common_overrides={
            "Model/evaluation_metrics": effective_params.get("Model/evaluation_metrics"),
            "Output/upload_plots": as_bool(effective_params.get("Output/upload_plots"), default=True),
        },
        ensemble_top_k=int(ensemble_cfg.get("top_k") or 3),
    )
