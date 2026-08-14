from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ml_platform_core.contracts import DomainPipelinePlan, DomainStepPlan

from .ensemble import SUPPORTED_ENSEMBLE_METHODS
from .manifest import (
    TABULAR_ENSEMBLE_STAGE,
    TABULAR_EVALUATE_STAGE,
    TABULAR_MANIFEST,
    TABULAR_PREPROCESS_STAGE,
    TABULAR_TRAIN_STAGE,
    TABULAR_TRAINING_PIPELINE_SPEC,
)
from .models import validate_model_name


def build_tabular_domain_plan(
    *,
    run_name: str = "tabular_training_pipeline",
    candidates: Sequence[str | Mapping[str, Any]] | None = None,
    ensemble_methods: Sequence[str] | None = None,
    include_ensemble: bool = True,
    selection_metric: str | None = None,
    preprocess_overrides: Mapping[str, object] | None = None,
    stage_common_overrides: Mapping[str, object] | None = None,
    ensemble_top_k: int = 3,
) -> DomainPipelinePlan:
    model_candidates = _normalize_candidates(candidates)
    methods = _normalize_ensemble_methods(ensemble_methods) if include_ensemble else ()
    preprocess_params = {
        **dict(preprocess_overrides or {}),
        **dict(stage_common_overrides or {}),
    }
    train_steps = _train_steps(model_candidates, stage_common_overrides, selection_metric)
    train_step_names = [step.name for step in train_steps]
    ensemble_steps = _ensemble_steps(
        methods, train_step_names, stage_common_overrides, selection_metric, ensemble_top_k
    )
    evaluate_parents = list(train_step_names)
    evaluate_parents.extend(step.name for step in ensemble_steps)
    steps = [
        _preprocess_step(preprocess_params),
        *train_steps,
        *ensemble_steps,
        _evaluate_step(evaluate_parents, stage_common_overrides, selection_metric),
    ]
    return DomainPipelinePlan(
        key=TABULAR_TRAINING_PIPELINE_SPEC.key,
        version=TABULAR_MANIFEST.version,
        run_name=run_name,
        steps=tuple(steps),
    )


def _preprocess_step(preprocess_params: dict[str, object]) -> DomainStepPlan:
    return DomainStepPlan(
        name="preprocess_features",
        stage_key="preprocess_features",
        parameter_overrides=preprocess_params,
        expected_artifacts=tuple(artifact.name for artifact in TABULAR_PREPROCESS_STAGE.output_artifacts),
    )


def _train_steps(
    model_candidates: tuple[dict[str, Any], ...],
    stage_common_overrides: Mapping[str, object] | None,
    selection_metric: str | None,
) -> list[DomainStepPlan]:
    return [_train_step(candidate, stage_common_overrides, selection_metric) for candidate in model_candidates]


def _train_step(
    candidate: dict[str, Any],
    stage_common_overrides: Mapping[str, object] | None,
    selection_metric: str | None,
) -> DomainStepPlan:
    model_name = candidate["name"]
    train_params: dict[str, object] = {
        **dict(stage_common_overrides or {}),
        "Model/name": model_name,
        "Model/params": candidate.get("params") or {},
    }
    if selection_metric is not None:
        train_params["Model/selection_metric"] = selection_metric
    return DomainStepPlan(
        name=f"train_{_safe_step_suffix(model_name)}",
        stage_key="train_model",
        parents=("preprocess_features",),
        parameter_overrides=train_params,
        expected_artifacts=tuple(artifact.name for artifact in TABULAR_TRAIN_STAGE.output_artifacts),
        model_name=model_name,
    )


def _ensemble_steps(
    methods: tuple[str, ...],
    train_step_names: list[str],
    stage_common_overrides: Mapping[str, object] | None,
    selection_metric: str | None,
    ensemble_top_k: int,
) -> list[DomainStepPlan]:
    return [
        _ensemble_step(method, train_step_names, stage_common_overrides, selection_metric, ensemble_top_k)
        for method in methods
    ]


def _ensemble_step(
    method: str,
    train_step_names: list[str],
    stage_common_overrides: Mapping[str, object] | None,
    selection_metric: str | None,
    ensemble_top_k: int,
) -> DomainStepPlan:
    ensemble_params: dict[str, object] = {
        **dict(stage_common_overrides or {}),
        "Model/ensemble_enabled": True,
        "Model/ensemble_methods": [method],
        "Model/ensemble_method": method,
        "Model/ensemble_top_k": ensemble_top_k,
    }
    if selection_metric is not None:
        ensemble_params["Model/selection_metric"] = selection_metric
    return DomainStepPlan(
        name=f"build_ensemble_{_safe_step_suffix(method)}",
        stage_key="build_ensemble",
        parents=tuple(train_step_names),
        parameter_overrides=ensemble_params,
        expected_artifacts=tuple(artifact.name for artifact in TABULAR_ENSEMBLE_STAGE.output_artifacts),
        ensemble_method=method,
    )


def _evaluate_step(
    evaluate_parents: list[str],
    stage_common_overrides: Mapping[str, object] | None,
    selection_metric: str | None,
) -> DomainStepPlan:
    evaluate_params: dict[str, object] = dict(stage_common_overrides or {})
    if selection_metric is not None:
        evaluate_params["Model/selection_metric"] = selection_metric
    return DomainStepPlan(
        name="evaluate_models",
        stage_key="evaluate_models",
        parents=tuple(evaluate_parents),
        parameter_overrides=evaluate_params,
        expected_artifacts=tuple(artifact.name for artifact in TABULAR_EVALUATE_STAGE.output_artifacts),
    )


def _safe_step_suffix(value: str) -> str:
    text = "".join(char if char.isalnum() else "_" for char in value.strip().lower())
    return text.strip("_") or "unnamed"


def _normalize_candidates(candidates: Sequence[str | Mapping[str, Any]] | None) -> tuple[dict[str, Any], ...]:
    raw_values = tuple(candidates or ("ridge",))
    values = [_normalize_candidate(item, index) for index, item in enumerate(raw_values)]
    if not values:
        raise ValueError("Domain plan requires at least one model candidate.")
    for value in values:
        validate_model_name(value["name"])
    return tuple(values)


def _normalize_candidate(item: str | Mapping[str, Any], index: int) -> dict[str, Any]:
    if isinstance(item, str):
        return {"name": item, "params": {}}
    if isinstance(item, Mapping):
        return _normalize_candidate_mapping(item, index)
    raise ValueError(f"Domain plan candidate[{index}] must be a model name or mapping.")


def _normalize_candidate_mapping(item: Mapping[str, Any], index: int) -> dict[str, Any]:
    name = item.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError(f"Domain plan candidate[{index}].name is required.")
    params = item.get("params") or {}
    if not isinstance(params, dict):
        raise ValueError(f"Domain plan candidate[{index}].params must be a mapping.")
    return {"name": name, "params": dict(params)}


def _normalize_ensemble_methods(methods: Sequence[str] | None) -> tuple[str, ...]:
    values = tuple(methods or ("mean_topk",))
    invalid = [value for value in values if value not in SUPPORTED_ENSEMBLE_METHODS]
    if invalid:
        choices = ", ".join(SUPPORTED_ENSEMBLE_METHODS)
        raise ValueError(f"Unsupported ensemble methods: {invalid}. Available: {choices}.")
    return values
