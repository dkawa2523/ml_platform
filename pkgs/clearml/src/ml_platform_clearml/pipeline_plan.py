from __future__ import annotations

from pathlib import Path
from typing import Any

from ml_platform_core.config import apply_overrides, load_yaml
from ml_platform_core.contracts import DomainPipelinePlan
from ml_platform_core.value_coercion import as_bool
from ml_platform_tabular.domain_plan import build_tabular_domain_plan
from ml_platform_tabular.policy import (
    ensemble_enabled_from_config,
    ensemble_methods_from_config,
    model_cfg_for_runtime,
    runtime_model_suite,
    runtime_quality_mode,
    training_model_candidates,
    validate_primary_training_graph,
)

from .adapter import clearml_projects, clearml_tags, prefixed_task_name
from .pipeline_params import (
    model_params_overridden,
    preprocess_parameter_overrides,
    runtime_param_sets,
)
from .pipeline_steps import render_pipeline_steps

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


def build_pipeline_plan(
    task_path: str | Path = "config/tasks/tabular_pipeline.yaml",
    profile_path: str | Path = "config/profiles/clearml-dev.yaml",
    runtime_params: dict[str, Any] | None = None,
    overrides: list[str] | dict[str, Any] | None = None,
) -> dict[str, Any]:
    pipeline_cfg = apply_overrides(load_yaml(task_path), overrides)
    if "data" not in pipeline_cfg:
        raise ValueError("ClearML pipeline planning requires the official stage-based training config.")
    return _build_training_plan(
        pipeline_cfg,
        load_yaml(profile_path),
        task_path,
        profile_path,
        runtime_params,
        explicit_model_params=model_params_overridden(overrides),
    )


def print_pipeline_plan(plan: dict[str, Any]) -> None:
    fields = ((key, plan.get(key)) for key in PIPELINE_DRY_RUN_KEYS)
    print("DRY-RUN pipeline: " + _format_fields(fields))
    for step in plan["steps"]:
        parents = ",".join(step["parents"]) if step["parents"] else "-"
        overrides = ", ".join(f"{key}={value}" for key, value in step["parameter_override"].items()) or "-"
        print(
            "DRY-RUN step: "
            + _format_fields(
                (
                    ("name", step["name"]),
                    ("parents", parents),
                    ("target_project", step.get("target_project")),
                    ("execution_queue", step.get("execution_queue")),
                    ("template", f"{step['base_task_project']}/{step['base_task_name']}"),
                    ("task_config", step["task_config"]),
                    ("parameter_override", f"[{overrides}]"),
                    ("tags", step.get("tags", [])),
                )
            )
        )


def _format_fields(fields) -> str:
    return " ".join(f"{key}={value}" for key, value in fields)


def _build_training_plan(
    pipeline_cfg: dict[str, Any],
    profile: dict[str, Any],
    task_path: str | Path,
    profile_path: str | Path,
    runtime_params: dict[str, Any] | None,
    *,
    explicit_model_params: bool,
) -> dict[str, Any]:
    projects = clearml_projects(profile.get("clearml", {}))
    stage_queue, controller_queue = _pipeline_queues(profile)
    effective_params, explicit_params = runtime_param_sets(pipeline_cfg, profile, runtime_params)
    if explicit_model_params:
        explicit_params["Model/model_params_by_name"] = effective_params["Model/model_params_by_name"]
    run_name = str(effective_params.get("Run/name") or pipeline_cfg.get("run", {}).get("name") or "run")
    model_cfg, candidates, ensemble_cfg = _runtime_model_plan(pipeline_cfg, effective_params, explicit_params)
    ensemble_enabled = ensemble_enabled_from_config(ensemble_cfg)
    domain_plan = _build_domain_plan(
        run_name,
        candidates,
        ensemble_cfg,
        ensemble_enabled,
        effective_params,
        model_cfg,
    )
    steps = render_pipeline_steps(
        domain_plan,
        templates_project=projects["templates"],
        projects=projects,
        run_name=run_name,
        execution_queue=stage_queue,
    )
    return _plan_payload(
        projects,
        run_name=run_name,
        task_path=task_path,
        profile_path=profile_path,
        stage_queue=stage_queue,
        controller_queue=controller_queue,
        candidates=candidates,
        model_suite=runtime_model_suite(effective_params),
        quality_mode=runtime_quality_mode(effective_params),
        ensemble_enabled=ensemble_enabled,
        steps=steps,
    )


def _runtime_model_plan(
    pipeline_cfg: dict[str, Any],
    effective_params: dict[str, Any],
    explicit_params: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    model_cfg = model_cfg_for_runtime(pipeline_cfg, effective_params, explicit_params)
    validate_primary_training_graph(model_cfg)
    candidates = training_model_candidates(model_cfg, seed=int(effective_params.get("Run/seed") or 42))
    ensemble_cfg = model_cfg.get("ensemble", {}) or {}
    return model_cfg, candidates, ensemble_cfg if isinstance(ensemble_cfg, dict) else {}


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
        preprocess_overrides=preprocess_parameter_overrides(effective_params),
        stage_common_overrides={
            "Run/seed": int(effective_params.get("Run/seed") or 42),
            "Model/evaluation_metrics": effective_params.get("Model/evaluation_metrics"),
            "Output/upload_plots": as_bool(effective_params.get("Output/upload_plots"), default=True),
        },
        ensemble_top_k=int(ensemble_cfg.get("top_k") or 3),
    )


def _plan_payload(
    projects: dict[str, str],
    *,
    run_name: str,
    task_path: str | Path,
    profile_path: str | Path,
    stage_queue: str,
    controller_queue: str,
    candidates: list[dict[str, Any]],
    model_suite: str,
    quality_mode: str,
    ensemble_enabled: bool,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "kind": "training",
        "project": projects["pipelines"],
        "stage_project": projects["stages"],
        "stage_projects": {key: projects[key] for key in ("preprocess", "train", "ensemble", "evaluate")},
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
