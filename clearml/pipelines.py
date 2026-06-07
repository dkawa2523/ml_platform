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

from adapter import as_bool, as_candidates, as_dict, as_list, import_clearml_automation, import_clearml_sdk, import_clearml_symbol
from ml_platform_core.config import apply_overrides, load_yaml
from ml_platform_tabular.models import AVAILABLE_MODELS, candidate_params, model_candidates
from ml_platform_tabular.pipeline_modes import apply_pipeline_mode_defaults


PIPELINE_ARG_PREFIX = "Args/"
STAGE_TASK_CONFIG = "config/tasks/tabular_stage.yaml"
STAGE_TEMPLATE = "tabular_stage_template"
OFFICIAL_SKLEARN_MODELS = ["linear", "ridge", "random_forest", "gradient_boosting"]
IMPLEMENTED_SKLEARN_MODELS = list(AVAILABLE_MODELS)
LEGACY_MODEL_ARTIFACT_REF = "${train.artifacts.model.url}"
LEGACY_TASK_TO_TEMPLATE = {
    "tabular_train": "tabular_train_template",
    "tabular_eval": "tabular_eval_template",
    "tabular_infer": "tabular_infer_template",
}
LEGACY_DEFAULT_STEP_CONFIGS = {
    "train": "config/tasks/tabular_train.yaml",
    "eval": "config/tasks/tabular_eval.yaml",
    "infer": "config/tasks/tabular_infer.yaml",
}


def _artifact_ref(step_name: str, artifact_name: str) -> str:
    return "${" + f"{step_name}.artifacts.{artifact_name}.url" + "}"


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _template_project(profile: dict[str, Any]) -> tuple[str, str, str]:
    clearml_cfg = profile.get("clearml", {})
    project_root = clearml_cfg.get("project_root", "MLPlatform/Dev")
    return project_root, f"{project_root}/Templates", f"{project_root}/Pipelines"


def _is_legacy_full_run_config(cfg: dict[str, Any]) -> bool:
    return "data" not in cfg and all(name in cfg for name in ("train", "eval", "infer"))


def _pipeline_model_cfg(pipeline_cfg: dict[str, Any], ui_params: dict[str, Any] | None = None) -> dict[str, Any]:
    model_cfg = deepcopy(pipeline_cfg.get("model", {}) or {})
    ui_params = ui_params or {}
    if "Model/candidates" in ui_params:
        model_cfg["candidates"] = as_candidates(ui_params.get("Model/candidates"))
    if "Model/params" in ui_params:
        model_cfg["params"] = as_dict(ui_params.get("Model/params"))
    if "Model/selection_metric" in ui_params and ui_params.get("Model/selection_metric"):
        model_cfg["selection_metric"] = ui_params["Model/selection_metric"]
    if "Model/ensemble_enabled" in ui_params:
        model_cfg.setdefault("ensemble", {})["enabled"] = as_bool(ui_params.get("Model/ensemble_enabled"))
    if "Model/ensemble_method" in ui_params and ui_params.get("Model/ensemble_method"):
        model_cfg.setdefault("ensemble", {})["method"] = ui_params["Model/ensemble_method"]
    if "Model/ensemble_top_k" in ui_params and ui_params.get("Model/ensemble_top_k") not in {None, ""}:
        model_cfg.setdefault("ensemble", {})["top_k"] = int(ui_params["Model/ensemble_top_k"])
    if "Model/search_enabled" in ui_params:
        model_cfg.setdefault("search", {})["enabled"] = as_bool(ui_params.get("Model/search_enabled"))
    if "Model/search_method" in ui_params and ui_params.get("Model/search_method"):
        model_cfg.setdefault("search", {})["method"] = str(ui_params["Model/search_method"]).strip().lower()
    if "Model/search_space" in ui_params:
        model_cfg.setdefault("search", {})["search_space"] = as_dict(ui_params.get("Model/search_space"))
    if "Model/max_trials" in ui_params and ui_params.get("Model/max_trials") not in {None, ""}:
        model_cfg.setdefault("search", {})["max_trials"] = int(ui_params["Model/max_trials"])
    return model_cfg


def _training_pipeline_ui_params(pipeline_cfg: dict[str, Any]) -> dict[str, Any]:
    run = pipeline_cfg.get("run", {})
    data = pipeline_cfg.get("data", {})
    model = pipeline_cfg.get("model", {})
    ensemble = model.get("ensemble", {}) or {}
    if not isinstance(ensemble, dict):
        ensemble = {}
    search = model.get("search", {}) or {}
    if not isinstance(search, dict):
        search = {}
    return {
        "Run/task": pipeline_cfg.get("task"),
        "Run/name": run.get("name"),
        "Run/seed": run.get("seed"),
        "Input/local_path": data.get("local_path"),
        "Input/clearml_dataset_id": data.get("clearml_dataset_id"),
        "Input/dataset_file": data.get("dataset_file"),
        "Input/target_column": data.get("target_column"),
        "Input/feature_columns": data.get("feature_columns"),
        "Input/id_columns": data.get("id_columns", []),
        "Model/candidates": _json(model.get("candidates", []) or []),
        "Model/params": _json(model.get("params", {}) or {}),
        "Model/selection_metric": model.get("selection_metric", "rmse"),
        "Model/search_enabled": as_bool(search.get("enabled")),
        "Model/search_method": search.get("method", "grid"),
        "Model/search_space": _json(search.get("search_space", {}) or {}),
        "Model/max_trials": int(search.get("max_trials") or 20),
        "Model/ensemble_enabled": as_bool(ensemble.get("enabled")),
        "Model/ensemble_method": ensemble.get("method", "mean_topk"),
        "Model/ensemble_top_k": int(ensemble.get("top_k") or 3),
        "Model/feature_preset": pipeline_cfg.get("features", {}).get("preset"),
    }


def _legacy_pipeline_ui_params(pipeline_cfg: dict[str, Any]) -> dict[str, Any]:
    train_cfg = load_yaml(pipeline_cfg.get("train", {}).get("task_config", LEGACY_DEFAULT_STEP_CONFIGS["train"]))
    eval_cfg = load_yaml(pipeline_cfg.get("eval", {}).get("task_config", LEGACY_DEFAULT_STEP_CONFIGS["eval"]))
    infer_cfg = load_yaml(pipeline_cfg.get("infer", {}).get("task_config", LEGACY_DEFAULT_STEP_CONFIGS["infer"]))
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
        "Model/params": _json(train_model.get("params", {}) or {}),
        "Model/candidates": _json(train_model.get("candidates", []) or []),
        "Model/selection_metric": train_model.get("selection_metric", "rmse"),
        "Model/search_enabled": bool(train_search.get("enabled", False)),
        "Model/search_method": train_search.get("method", "grid"),
        "Model/search_space": _json(train_search.get("search_space", {}) or {}),
        "Model/max_trials": int(train_search.get("max_trials") or 20),
        "Model/ensemble_enabled": bool(train_ensemble.get("enabled", False)),
        "Model/ensemble_method": train_ensemble.get("method", "mean_topk"),
        "Model/ensemble_top_k": int(train_ensemble.get("top_k") or 3),
        "Model/feature_preset": train_cfg.get("features", {}).get("preset"),
        "Output/prediction_name": infer_output.get("prediction_name"),
        "Output/chunk_size": infer_output.get("chunk_size"),
    }


def pipeline_ui_params(
    task_path: str | Path = "config/tasks/tabular_pipeline.yaml",
    profile_path: str | Path = "config/profiles/clearml-dev.yaml",
) -> dict[str, Any]:
    pipeline_cfg = load_yaml(task_path)
    if _is_legacy_full_run_config(pipeline_cfg):
        return _legacy_pipeline_ui_params(pipeline_cfg)
    return _training_pipeline_ui_params(pipeline_cfg)


def _legacy_effective_pipeline_params(ui_params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
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
            "Model/params": _json(effective_model.get("params", {}) or {}),
            "Model/candidates": _json(effective_model.get("candidates", []) or []),
            "Model/search_enabled": bool(effective_model.get("search", {}).get("enabled", False)),
            "Model/search_method": effective_model.get("search", {}).get("method", "grid"),
            "Model/search_space": _json(effective_model.get("search", {}).get("search_space", {}) or {}),
            "Model/max_trials": int(effective_model.get("search", {}).get("max_trials") or 20),
            "Model/ensemble_enabled": bool(effective_model.get("ensemble", {}).get("enabled", False)),
            "Model/ensemble_method": effective_model.get("ensemble", {}).get("method", "mean_topk"),
            "Model/ensemble_top_k": int(effective_model.get("ensemble", {}).get("top_k") or 3),
        }
    )
    return mode, effective_params


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


def _apply_legacy_overrides(step: dict[str, Any], ui_params: dict[str, Any]) -> None:
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
        for key in (
            "Model/name",
            "Model/params",
            "Model/candidates",
            "Model/selection_metric",
            "Model/search_enabled",
            "Model/search_method",
            "Model/search_space",
            "Model/max_trials",
            "Model/ensemble_enabled",
            "Model/ensemble_method",
            "Model/ensemble_top_k",
            "Model/feature_preset",
        ):
            if key in ui_params and ui_params.get(key) not in {None, ""}:
                step["parameter_override"][key] = ui_params[key]
    if step["name"] == "infer":
        if ui_params.get("Output/prediction_name"):
            step["parameter_override"]["Output/prediction_name"] = ui_params["Output/prediction_name"]
        if "Output/chunk_size" in ui_params and ui_params.get("Output/chunk_size") not in {None, ""}:
            step["parameter_override"]["Output/chunk_size"] = int(ui_params["Output/chunk_size"])


def _load_legacy_step_task_name(task_config: str | Path) -> str:
    task_cfg = load_yaml(task_config)
    task_name = task_cfg.get("task")
    if task_name not in LEGACY_TASK_TO_TEMPLATE:
        raise ValueError(f"Unsupported compatibility pipeline step task: {task_name!r}")
    return task_name


def _build_legacy_plan(
    pipeline_cfg: dict[str, Any],
    profile: dict[str, Any],
    task_path: str | Path,
    profile_path: str | Path,
    ui_params: dict[str, Any] | None,
) -> dict[str, Any]:
    project_root, templates_project, pipelines_project = _template_project(profile)
    clearml_cfg = profile.get("clearml", {})
    default_params = _legacy_pipeline_ui_params(pipeline_cfg)
    mode, effective_params = _legacy_effective_pipeline_params({**default_params, **(ui_params or {})})

    steps = []
    for name, parents in (("train", []), ("eval", ["train"]), ("infer", ["eval"])):
        section = pipeline_cfg.get(name, {})
        task_config = section.get("task_config") or LEGACY_DEFAULT_STEP_CONFIGS[name]
        task_name = _load_legacy_step_task_name(task_config)
        step: dict[str, Any] = {
            "name": name,
            "parents": parents,
            "base_task_project": templates_project,
            "base_task_name": LEGACY_TASK_TO_TEMPLATE[task_name],
            "task_config": task_config,
            "parameter_override": {},
        }
        if name in {"eval", "infer"}:
            step["parameter_override"]["Model/artifact_path"] = LEGACY_MODEL_ARTIFACT_REF
        if ui_params:
            _apply_legacy_overrides(step, effective_params)
        steps.append(step)

    return {
        "kind": "compatibility_train_eval_infer",
        "project": f"{project_root}/Pipelines",
        "name": pipeline_cfg.get("run", {}).get("name", "tabular_pipeline"),
        "version": "0.1.0",
        "pipeline_mode": mode,
        "queue": clearml_cfg.get("queue", "default"),
        "steps": steps,
        "task_config": str(task_path),
        "profile_config": str(profile_path),
    }


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


def _ensemble_ref() -> dict[str, Any]:
    return {
        "stage": "build_ensemble",
        "model_name": "mean_topk",
        "artifact_kind": "ensemble",
        "model": _artifact_ref("build_ensemble", "model"),
        "model_info": _artifact_ref("build_ensemble", "model_info"),
        "ensemble_info": _artifact_ref("build_ensemble", "ensemble_info"),
        "metrics": _artifact_ref("build_ensemble", "metrics"),
        "ensemble_predictions": _artifact_ref("build_ensemble", "ensemble_predictions"),
    }


def _search_refs() -> dict[str, str]:
    return {
        "Input/best_params": _artifact_ref("search_trials", "best_params"),
        "Input/optimization_summary": _artifact_ref("search_trials", "optimization_summary"),
    }


def _retrained_model_refs() -> dict[str, str]:
    return {
        "Input/model": _artifact_ref("retrain_best", "model"),
        "Input/model_info": _artifact_ref("retrain_best", "model_info"),
    }


def _stage_step(
    *,
    name: str,
    stage: str,
    templates_project: str,
    parents: list[str] | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parameter_override = {
        "Run/name": name,
        "Run/stage": stage,
        **(overrides or {}),
    }
    parameter_override = {key: value for key, value in parameter_override.items() if value is not None}
    return {
        "name": name,
        "parents": parents or [],
        "base_task_project": templates_project,
        "base_task_name": STAGE_TEMPLATE,
        "task_config": STAGE_TASK_CONFIG,
        "parameter_override": parameter_override,
    }


def _build_optimization_plan(
    pipeline_cfg: dict[str, Any],
    profile: dict[str, Any],
    task_path: str | Path,
    profile_path: str | Path,
    ui_params: dict[str, Any] | None,
) -> dict[str, Any]:
    project_root, templates_project, pipelines_project = _template_project(profile)
    clearml_cfg = profile.get("clearml", {})
    default_params = _training_pipeline_ui_params(pipeline_cfg)
    effective_params = {**default_params, **(ui_params or {})}
    model_cfg = _pipeline_model_cfg(pipeline_cfg, effective_params)
    ensemble_cfg = model_cfg.get("ensemble", {}) or {}
    if not isinstance(ensemble_cfg, dict):
        ensemble_cfg = {}
    if as_bool(ensemble_cfg.get("enabled")):
        raise ValueError("model.search.enabled=true cannot be combined with model.ensemble.enabled=true in Phase E.")

    search_cfg = model_cfg.get("search", {}) or {}
    if not isinstance(search_cfg, dict):
        search_cfg = {}
    candidates = model_candidates(model_cfg)
    if not candidates:
        raise ValueError("Optimization pipeline requires at least one model candidate.")
    selection_metric = str(model_cfg.get("selection_metric") or "rmse")
    data_overrides = _data_overrides(effective_params)

    steps: list[dict[str, Any]] = [
        _stage_step(
            name="preprocess_features",
            stage="preprocess_features",
            templates_project=templates_project,
            overrides={
                **data_overrides,
                "Model/feature_preset": effective_params.get("Model/feature_preset"),
            },
        ),
        _stage_step(
            name="search_trials",
            stage="search_trials",
            templates_project=templates_project,
            parents=["preprocess_features"],
            overrides={
                **_preprocess_refs(),
                "Model/name": model_cfg.get("name"),
                "Model/params": _json(model_cfg.get("params", {}) or {}),
                "Model/candidates": _json(model_cfg.get("candidates", []) or []),
                "Model/selection_metric": selection_metric,
                "Model/search_enabled": True,
                "Model/search_method": search_cfg.get("method", "grid"),
                "Model/search_space": _json(search_cfg.get("search_space", {}) or {}),
                "Model/max_trials": int(search_cfg.get("max_trials") or 20),
                "Model/ensemble_enabled": False,
            },
        ),
        _stage_step(
            name="retrain_best",
            stage="retrain_best",
            templates_project=templates_project,
            parents=["search_trials"],
            overrides={
                **_preprocess_refs(),
                "Input/best_params": _artifact_ref("search_trials", "best_params"),
                "Model/selection_metric": selection_metric,
            },
        ),
        _stage_step(
            name="evaluate_best",
            stage="evaluate_best",
            templates_project=templates_project,
            parents=["retrain_best"],
            overrides={
                **_search_refs(),
                **_retrained_model_refs(),
                "Model/selection_metric": selection_metric,
            },
        ),
    ]

    return {
        "kind": "optimization",
        "project": pipelines_project,
        "name": pipeline_cfg.get("run", {}).get("name", "tabular_optimization_pipeline"),
        "version": "0.3.0",
        "pipeline_mode": "optimization",
        "queue": clearml_cfg.get("queue", "default"),
        "candidate_models": [candidate["name"] for candidate in candidates],
        "ensemble_enabled": False,
        "steps": steps,
        "task_config": str(task_path),
        "profile_config": str(profile_path),
    }


def _build_training_plan(
    pipeline_cfg: dict[str, Any],
    profile: dict[str, Any],
    task_path: str | Path,
    profile_path: str | Path,
    ui_params: dict[str, Any] | None,
) -> dict[str, Any]:
    project_root, templates_project, pipelines_project = _template_project(profile)
    clearml_cfg = profile.get("clearml", {})
    default_params = _training_pipeline_ui_params(pipeline_cfg)
    effective_params = {**default_params, **(ui_params or {})}
    model_cfg = _pipeline_model_cfg(pipeline_cfg, effective_params)
    search_cfg = model_cfg.get("search", {}) or {}
    if not isinstance(search_cfg, dict):
        search_cfg = {}
    if as_bool(search_cfg.get("enabled")):
        return _build_optimization_plan(pipeline_cfg, profile, task_path, profile_path, effective_params)
    candidates = model_candidates(model_cfg)
    if not candidates:
        raise ValueError("Training pipeline requires at least one model candidate.")

    ensemble_cfg = model_cfg.get("ensemble", {}) or {}
    if not isinstance(ensemble_cfg, dict):
        ensemble_cfg = {}
    ensemble_enabled = as_bool(ensemble_cfg.get("enabled"))
    selection_metric = str(model_cfg.get("selection_metric") or "rmse")
    data_overrides = _data_overrides(effective_params)

    steps: list[dict[str, Any]] = [
        _stage_step(
            name="preprocess_features",
            stage="preprocess_features",
            templates_project=templates_project,
            overrides={
                **data_overrides,
                "Model/feature_preset": effective_params.get("Model/feature_preset"),
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
                parents=["preprocess_features"],
                overrides={
                    **_preprocess_refs(),
                    "Model/name": model_name,
                    "Model/params": _json(model_params),
                    "Model/selection_metric": selection_metric,
                    "Model/feature_preset": effective_params.get("Model/feature_preset"),
                },
            )
        )

    parents_for_evaluate = list(train_steps)
    ensemble_ref = None
    if ensemble_enabled:
        ensemble_ref = _ensemble_ref()
        parents_for_evaluate.append("build_ensemble")
        steps.append(
            _stage_step(
                name="build_ensemble",
                stage="build_ensemble",
                templates_project=templates_project,
                parents=train_steps,
                overrides={
                    **_preprocess_refs(),
                    "Input/model_refs": _json(model_refs),
                    "Model/selection_metric": selection_metric,
                    "Model/ensemble_enabled": True,
                    "Model/ensemble_method": ensemble_cfg.get("method", "mean_topk"),
                    "Model/ensemble_top_k": int(ensemble_cfg.get("top_k") or 3),
                },
            )
        )

    steps.append(
        _stage_step(
            name="evaluate_models",
            stage="evaluate_models",
            templates_project=templates_project,
            parents=parents_for_evaluate,
            overrides={
                "Input/model_refs": _json(model_refs),
                "Input/ensemble_ref": _json(ensemble_ref) if ensemble_ref else None,
                "Model/selection_metric": selection_metric,
            },
        )
    )

    return {
        "kind": "training",
        "project": pipelines_project,
        "name": pipeline_cfg.get("run", {}).get("name", "tabular_train_pipeline"),
        "version": "0.2.0",
        "pipeline_mode": "training_ensemble" if ensemble_enabled else "training",
        "queue": clearml_cfg.get("queue", "default"),
        "candidate_models": [candidate["name"] for candidate in candidates],
        "ensemble_enabled": ensemble_enabled,
        "steps": steps,
        "task_config": str(task_path),
        "profile_config": str(profile_path),
    }


def build_pipeline_plan(
    task_path: str | Path = "config/tasks/tabular_pipeline.yaml",
    profile_path: str | Path = "config/profiles/clearml-dev.yaml",
    ui_params: dict[str, Any] | None = None,
    overrides: list[str] | dict[str, Any] | None = None,
) -> dict[str, Any]:
    pipeline_cfg = apply_overrides(load_yaml(task_path), overrides)
    profile = load_yaml(profile_path)
    if _is_legacy_full_run_config(pipeline_cfg):
        return _build_legacy_plan(pipeline_cfg, profile, task_path, profile_path, ui_params)
    return _build_training_plan(pipeline_cfg, profile, task_path, profile_path, ui_params)


def print_pipeline_plan(plan: dict[str, Any]) -> None:
    print(
        "DRY-RUN pipeline: "
        f"kind={plan['kind']} "
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
    task_path: str | Path = "config/tasks/tabular_train_pipeline.yaml",
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
    existing = _find_pipeline_draft(Task, template_name)
    params = pipeline_ui_params(task_path, profile_path)
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
    return pipe.task


def register_tabular_pipeline(
    task_path: str | Path = "config/tasks/tabular_train_pipeline.yaml",
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
    )
    task = Task.current_task()
    task_params = task.get_parameters() if task else {}
    connected = pipeline_params_from_task(defaults, task_params)
    plan = build_pipeline_plan(task_path=task_path, profile_path=profile_path, ui_params=connected, overrides=overrides)

    _add_plan_steps(pipe, plan)
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
