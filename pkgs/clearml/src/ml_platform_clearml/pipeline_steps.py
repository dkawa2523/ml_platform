from __future__ import annotations

import json
from typing import Any

from ml_platform_core.contracts import DomainPipelinePlan, DomainStepPlan
from ml_platform_core.stages import StageName, as_stage_name

from .adapter import clearml_stage_project, clearml_tags, clearml_template_name, prefixed_task_name, stage_task_label
from .param_transport import normalize_clearml_param_value

STAGE_TASK_CONFIG = "config/tasks/tabular_stage.yaml"
STAGE_TEMPLATE = "tabular_stage_template"
MODEL_REF_ARTIFACTS = ("model", "model_info", "metrics", "selection_predictions")
ENSEMBLE_REF_ARTIFACTS = ("model", "model_info", "metrics", "selection_predictions")
PREPROCESS_HANDOFF_ARTIFACTS = ("preprocess_bundle", "processed_train", "processed_valid")


def render_pipeline_steps(
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


def _artifact_ref(step_name: str, artifact_name: str) -> str:
    return "${" + f"{step_name}.artifacts.{artifact_name}.url" + "}"


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
    preprocess = next(step for step in domain_plan.steps if step.stage_key == "preprocess_features")
    refs = _artifact_ref_map(preprocess, required=PREPROCESS_HANDOFF_ARTIFACTS)
    return {f"Input/{artifact}": refs[artifact] for artifact in PREPROCESS_HANDOFF_ARTIFACTS}


def _model_ref(step: DomainStepPlan) -> dict[str, Any]:
    refs = _artifact_ref_map(step, required=MODEL_REF_ARTIFACTS)
    return {
        "stage": step.name,
        "model_name": step.model_name,
        "model_params": _step_model_params(step),
        "artifact_kind": "model",
        **{artifact: refs[artifact] for artifact in MODEL_REF_ARTIFACTS},
    }


def _ensemble_ref(step: DomainStepPlan) -> dict[str, Any]:
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
        if isinstance(parsed, dict):
            return parsed
    raise ValueError(f"Domain step {step.name!r} Model/params must be a mapping.")


def _model_refs(domain_plan: DomainPipelinePlan) -> list[dict[str, Any]]:
    return [_model_ref(step) for step in domain_plan.steps if step.stage_key == "train_model"]


def _ensemble_refs(domain_plan: DomainPipelinePlan) -> list[dict[str, Any]]:
    return [_ensemble_ref(step) for step in domain_plan.steps if step.stage_key == "build_ensemble"]


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
            **preprocess_refs,
            **overrides,
            "Input/model_refs": _json(model_refs),
            "Input/ensemble_refs": _json(ensemble_refs) if ensemble_refs else None,
        }
    return overrides


def _serialized_stage_overrides(overrides: dict[str, Any]) -> dict[str, Any]:
    serialized = dict(overrides)
    for key in ("Model/params", "Model/ensemble_methods", "Model/evaluation_metrics"):
        if key in serialized and not isinstance(serialized[key], str):
            serialized[key] = normalize_clearml_param_value(serialized[key])
    return serialized


def _stage_step(
    *,
    name: str,
    stage: StageName | str,
    templates_project: str,
    projects: dict[str, str],
    run_name: str,
    execution_queue: str,
    model_name: str | None,
    ensemble_method: str | None,
    parents: list[str],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    stage_name = as_stage_name(str(stage))
    label = stage_task_label(stage_name, model_name, ensemble_method)
    parameter_override = {
        "Run/name": prefixed_task_name("stage", label, run_name),
        "Run/stage": stage_name,
        **overrides,
    }
    return {
        "name": name,
        "parents": parents,
        "base_task_project": templates_project,
        "base_task_name": clearml_template_name(STAGE_TEMPLATE),
        "task_config": STAGE_TASK_CONFIG,
        "target_project": clearml_stage_project(projects, stage_name),
        "execution_queue": execution_queue,
        "pipeline_stage_group": label,
        "parameter_override": {key: value for key, value in parameter_override.items() if value is not None},
        "tags": clearml_tags(
            "stage",
            internal=True,
            stage=stage_name,
            model=model_name,
            ensemble=ensemble_method,
        ),
    }


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)
