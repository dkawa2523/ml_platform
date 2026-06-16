from __future__ import annotations

import argparse
import importlib.util
import json
from copy import deepcopy
from pathlib import Path
from typing import Any


def _load_entrypoint_bootstrap():
    module_path = Path(__file__).resolve().parent / "_entrypoint_bootstrap.py"
    spec = importlib.util.spec_from_file_location("ml_platform_clearml_entrypoint_bootstrap", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load ClearML entrypoint bootstrap: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_load_entrypoint_bootstrap().add_clearml_entrypoint_paths()

from adapter import (
    apply_execution_image,
    as_bool,
    as_candidates,
    as_dict,
    as_list,
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
)
from ml_platform_core.config import apply_overrides, load_yaml
from ml_platform_tabular.models import (
    DEPENDENCY_FREE_MODELS,
    OPTIONAL_DEPENDENCY_MODELS,
    SUPPORTED_MODELS,
    candidate_params,
    model_candidates,
)


PIPELINE_ARG_PREFIX = "Args/"
STAGE_TASK_CONFIG = "config/tasks/tabular_stage.yaml"
STAGE_TEMPLATE = "tabular_stage_template"
PIPELINE_TEMPLATE_TAGS = clearml_tags("template", user_facing=True)
BASIC_MODEL_SUITES = {
    "default": list(SUPPORTED_MODELS),
    "fast": list(DEPENDENCY_FREE_MODELS),
    "interpretable": ["linear", "ridge", "lasso", "elasticnet"],
    "tree": ["random_forest", "extra_trees", "gradient_boosting"],
    "gbm": list(OPTIONAL_DEPENDENCY_MODELS),
}
BASIC_QUALITY_MODES = {"fast", "standard", "quality"}
BASIC_QUALITY_MODEL_PARAMS = {
    "fast": {
        "linear": {},
        "ridge": {"alpha": 1.0},
        "lasso": {"alpha": 0.01, "max_iter": 3000},
        "elasticnet": {"alpha": 0.01, "l1_ratio": 0.5, "max_iter": 3000, "random_state": 42},
        "random_forest": {"n_estimators": 10, "random_state": 42, "n_jobs": 1},
        "extra_trees": {"n_estimators": 10, "random_state": 42, "n_jobs": 1},
        "gradient_boosting": {"n_estimators": 10, "random_state": 42},
        "lightgbm": {"n_estimators": 30, "random_state": 42, "n_jobs": 1},
        "xgboost": {
            "n_estimators": 30,
            "random_state": 42,
            "n_jobs": 1,
            "objective": "reg:squarederror",
            "verbosity": 0,
        },
        "catboost": {"iterations": 30, "random_seed": 42, "verbose": False},
    },
    "standard": {
        "linear": {},
        "ridge": {"alpha": 1.0},
        "lasso": {"alpha": 0.01, "max_iter": 5000},
        "elasticnet": {"alpha": 0.01, "l1_ratio": 0.5, "max_iter": 5000, "random_state": 42},
        "random_forest": {"n_estimators": 20, "random_state": 42, "n_jobs": 1},
        "extra_trees": {"n_estimators": 20, "random_state": 42, "n_jobs": 1},
        "gradient_boosting": {"n_estimators": 20, "random_state": 42},
        "lightgbm": {"n_estimators": 100, "random_state": 42, "n_jobs": 1},
        "xgboost": {
            "n_estimators": 100,
            "random_state": 42,
            "n_jobs": 1,
            "objective": "reg:squarederror",
            "verbosity": 0,
        },
        "catboost": {"iterations": 100, "random_seed": 42, "verbose": False},
    },
    "quality": {
        "linear": {},
        "ridge": {"alpha": 1.0},
        "lasso": {"alpha": 0.01, "max_iter": 8000},
        "elasticnet": {"alpha": 0.01, "l1_ratio": 0.5, "max_iter": 8000, "random_state": 42},
        "random_forest": {"n_estimators": 60, "random_state": 42, "n_jobs": 1},
        "extra_trees": {"n_estimators": 60, "random_state": 42, "n_jobs": 1},
        "gradient_boosting": {"n_estimators": 60, "random_state": 42},
        "lightgbm": {"n_estimators": 200, "random_state": 42, "n_jobs": 1},
        "xgboost": {
            "n_estimators": 200,
            "random_state": 42,
            "n_jobs": 1,
            "objective": "reg:squarederror",
            "verbosity": 0,
        },
        "catboost": {"iterations": 200, "random_seed": 42, "verbose": False},
    },
}


def _artifact_ref(step_name: str, artifact_name: str) -> str:
    return "${" + f"{step_name}.artifacts.{artifact_name}.url" + "}"


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _project_layout(profile: dict[str, Any]) -> dict[str, str]:
    clearml_cfg = profile.get("clearml", {})
    return clearml_projects(clearml_cfg)


def _execution_image(profile: dict[str, Any]) -> str | None:
    return clearml_execution_image(profile.get("clearml", {}) or {})


def _has_ui_value(value: Any) -> bool:
    return value is not None and not (isinstance(value, str) and value.strip() == "")


def _basic_config(pipeline_cfg: dict[str, Any]) -> dict[str, Any]:
    raw = pipeline_cfg.get("basic") or pipeline_cfg.get("Basic") or {}
    return raw if isinstance(raw, dict) else {}


def _basic_text(ui_params: dict[str, Any], key: str, default: str) -> str:
    value = ui_params.get(key)
    if not _has_ui_value(value):
        return default
    return str(value).strip().lower()


def _basic_model_suite(ui_params: dict[str, Any]) -> str:
    suite = _basic_text(ui_params, "Basic/model_suite", "default")
    if suite not in {*BASIC_MODEL_SUITES, "custom"}:
        choices = ", ".join([*BASIC_MODEL_SUITES, "custom"])
        raise ValueError(f"Basic/model_suite must be one of: {choices}.")
    return suite


def _basic_quality_mode(ui_params: dict[str, Any]) -> str:
    mode = _basic_text(ui_params, "Basic/quality_mode", "standard")
    if mode not in BASIC_QUALITY_MODES:
        choices = ", ".join(sorted(BASIC_QUALITY_MODES))
        raise ValueError(f"Basic/quality_mode must be one of: {choices}.")
    return mode


def _apply_basic_model_suite(model_cfg: dict[str, Any], ui_params: dict[str, Any]) -> None:
    suite = _basic_model_suite(ui_params)
    if suite in {"default", "custom"}:
        return
    model_cfg["candidates"] = list(BASIC_MODEL_SUITES[suite])


def _basic_quality_model_params(mode: str) -> dict[str, Any]:
    return deepcopy(BASIC_QUALITY_MODEL_PARAMS[mode])


def _apply_basic_quality_mode(
    model_cfg: dict[str, Any],
    ui_params: dict[str, Any],
    explicit_ui_params: dict[str, Any],
) -> None:
    if "Model/model_params_by_name" in explicit_ui_params or "Model/params" in explicit_ui_params:
        return
    if _basic_model_suite(ui_params) == "custom":
        return
    model_cfg["params"] = _basic_quality_model_params(_basic_quality_mode(ui_params))


def _model_cfg_for_pipeline(
    pipeline_cfg: dict[str, Any],
    ui_params: dict[str, Any] | None = None,
    explicit_ui_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model_cfg = deepcopy(pipeline_cfg.get("model", {}) or {})
    ui_params = ui_params or {}
    explicit_ui_params = explicit_ui_params or {}
    if "Model/candidates" in ui_params:
        model_cfg["candidates"] = as_candidates(ui_params.get("Model/candidates"))
    if "Model/model_params_by_name" in explicit_ui_params:
        model_cfg["params"] = as_dict(ui_params.get("Model/model_params_by_name"))
    elif "Model/params" in explicit_ui_params:
        model_cfg["params"] = as_dict(ui_params.get("Model/params"))
    if "Model/selection_metric" in ui_params and ui_params.get("Model/selection_metric"):
        model_cfg["selection_metric"] = ui_params["Model/selection_metric"]
    _apply_basic_model_suite(model_cfg, ui_params)
    _apply_basic_quality_mode(model_cfg, ui_params, explicit_ui_params)
    if _has_ui_value(ui_params.get("Basic/use_ensemble")):
        model_cfg.setdefault("ensemble", {})["enabled"] = as_bool(ui_params.get("Basic/use_ensemble"))
    if _has_ui_value(ui_params.get("Model/ensemble_enabled")):
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
    basic = _basic_config(pipeline_cfg)
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
        "Basic/model_suite": basic.get("model_suite", "default"),
        "Basic/quality_mode": basic.get("quality_mode", "standard"),
        "Basic/use_ensemble": basic.get("use_ensemble", as_bool(ensemble.get("enabled"), default=True)),
        "Basic/notes": basic.get("notes") or run.get("description", ""),
        "Run/name": run.get("name"),
        "Run/seed": run.get("seed"),
        "Split/method": split.get("method", "random"),
        "Split/valid_size": split.get("valid_size", 0.2),
        "Split/group_column": split.get("group_column"),
        "Split/time_column": split.get("time_column"),
        "Split/valid_filter_column": split.get("valid_filter_column"),
        "Split/valid_filter_value": split.get("valid_filter_value"),
        "Input/local_path": local_path,
        "Input/clearml_dataset_id": clearml_dataset_id,
        "Input/dataset_file": dataset_file,
        "Input/target_column": data.get("target_column"),
        "Input/feature_columns": data.get("feature_columns") or [],
        "Input/id_columns": data.get("id_columns", []),
        "Features/preset": features.get("preset", "basic"),
        "Features/numeric_impute_strategy": features.get("numeric_impute_strategy", "median"),
        "Features/categorical_impute_strategy": features.get("categorical_impute_strategy", "missing_token"),
        "Features/categorical_encoder": features.get("categorical_encoder", "onehot"),
        "Features/scaling": features.get("scaling", "standard"),
        "Features/drop_columns": _json(features.get("drop_columns", []) or []),
        "Features/passthrough_columns": _json(features.get("passthrough_columns", []) or []),
        "Model/candidates": _json(SUPPORTED_MODELS),
        "Model/model_params_by_name": _json(model.get("params", {}) or {}),
        "Model/evaluation_metrics": _json(metrics.get("names", []) or []),
        "Model/selection_metric": model.get("selection_metric", "rmse"),
        "Model/ensemble_enabled": "",
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
    execution_queue: str,
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
        "execution_queue": execution_queue,
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
    stage_queue = str(clearml_cfg.get("stage_queue") or clearml_cfg.get("queue") or "default")
    controller_queue = str(clearml_cfg.get("controller_queue") or clearml_cfg.get("pipeline_queue") or stage_queue)
    default_params = _training_pipeline_ui_params(pipeline_cfg, profile)
    raw_ui_params = ui_params or {}
    explicit_params = {
        key: value
        for key, value in raw_ui_params.items()
        if key not in default_params or value != default_params.get(key)
    }
    effective_params = {**default_params, **(ui_params or {})}
    run_name = str(effective_params.get("Run/name") or pipeline_cfg.get("run", {}).get("name") or "run")
    model_suite = _basic_model_suite(effective_params)
    quality_mode = _basic_quality_mode(effective_params)
    model_cfg = _model_cfg_for_pipeline(pipeline_cfg, effective_params, explicit_params)
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
            execution_queue=stage_queue,
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
                execution_queue=stage_queue,
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
                    execution_queue=stage_queue,
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
            execution_queue=stage_queue,
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
        raise ValueError("ClearML pipeline planning requires a stage-based tabular_pipeline config with a data section.")
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
        task_type = getattr(task, "task_type", None) or getattr(task, "type", None) or getattr(getattr(task, "data", None), "type", None)
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
        task_type = getattr(task, "task_type", None) or getattr(task, "type", None) or getattr(getattr(task, "data", None), "type", None)
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
    params = pipeline_ui_params(task_path, profile_path)
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
