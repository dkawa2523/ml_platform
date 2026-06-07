"""ClearML-free local training pipeline orchestration.

The official training graph is:
preprocess_features -> train_<model>* -> build_ensemble optional -> evaluate_models.

The old train/eval/infer full-run remains as a deprecated fallback only for
old-style configs that still contain train/eval/infer sections.
"""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd

from ml_platform_core.artifacts import prepare_run_dir, update_latest, write_config_snapshot, write_manifest
from ml_platform_core.config import deep_merge, load_yaml
from ml_platform_core.io import dump_joblib, read_json, write_json, write_table
from ml_platform_core.result import RunResult

from .data import load_dataset, split_xy, train_valid_split
from .ensemble import ensemble_config, ensemble_weights, metric_value
from .evaluate import run_evaluate
from .features import build_feature_pipeline
from .infer import run_infer
from .metrics import DEFAULT_REGRESSION_METRICS, regression_metrics
from .model_artifact import write_model_info
from .models import MeanTopKEnsemble, TabularEstimator, build_model, model_candidates
from .pipeline_modes import apply_pipeline_mode_defaults
from .search import optimization_trial_rows, ranked_search_results, search_config, search_trials
from .train import run_train

LEADERBOARD_METRICS = ["rmse", "mae", "r2"]
SELECTION_METRICS = {"rmse", "mae", "r2"}


def _load_nested_task(root_cfg: dict[str, Any], section: str) -> dict[str, Any]:
    section_cfg = root_cfg.get(section, {})
    task_path = section_cfg.get("task_config")
    if not task_path:
        raise ValueError(f"{section}.task_config is required for deprecated train/eval/infer compatibility flow.")
    task_cfg = load_yaml(Path(task_path))

    inherited = {k: v for k, v in root_cfg.items() if k not in {"task", "train", "eval", "infer"}}
    section_overrides = {k: v for k, v in section_cfg.items() if k != "task_config"}
    merged = deep_merge(deep_merge(task_cfg, inherited), section_overrides)
    for overrides in (inherited, section_overrides):
        model_overrides = overrides.get("model")
        if isinstance(model_overrides, dict) and "params" in model_overrides:
            merged.setdefault("model", {})["params"] = deepcopy(model_overrides["params"])
    return merged


def _path_map(mapping: dict[str, Path]) -> dict[str, str]:
    return {name: str(path) for name, path in mapping.items()}


def _prefixed_existing(mapping: dict[str, Path], prefix: str, *, exclude: set[str] | None = None) -> dict[str, Path]:
    exclude = exclude or set()
    return {f"{prefix}_{name}": Path(path) for name, path in mapping.items() if name not in exclude and Path(path).exists()}


def _load_model_info(path: Path | None) -> dict[str, Any]:
    if path is not None and path.exists():
        return read_json(path)
    return {}


def _run_compatibility_full_run(cfg: dict[str, Any]) -> RunResult:
    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    run_name = cfg.get("run", {}).get("name", "tabular_pipeline")
    pipeline_dir = prepare_run_dir(output_dir, run_name)

    train_cfg = _load_nested_task(cfg, "train")
    mode, train_cfg = apply_pipeline_mode_defaults(train_cfg)
    train_result = run_train(train_cfg)

    eval_cfg = _load_nested_task(cfg, "eval")
    eval_cfg.setdefault("model", {})
    eval_cfg["model"]["artifact_path"] = str(train_result.artifacts["model"])
    eval_result = run_evaluate(eval_cfg)

    infer_cfg = _load_nested_task(cfg, "infer")
    infer_cfg.setdefault("model", {})
    infer_cfg["model"]["artifact_path"] = str(train_result.artifacts["model"])
    infer_result = run_infer(infer_cfg)

    train_model_info_path = train_result.artifacts.get("model_info")
    train_model_info = _load_model_info(train_model_info_path)
    metrics = {
        **{f"train_{k}": v for k, v in train_result.metrics.items()},
        **{f"eval_{k}": v for k, v in eval_result.metrics.items()},
    }
    artifacts: dict[str, Path] = {
        "model": train_result.artifacts["model"],
        **_prefixed_existing(train_result.artifacts, "train", exclude={"model"}),
        **_prefixed_existing(eval_result.artifacts, "eval"),
        **_prefixed_existing(infer_result.artifacts, "infer"),
    }
    tables: dict[str, Path] = {
        "train_validation_predictions": train_result.tables["validation_predictions"],
        "eval_evaluation_predictions": eval_result.tables["evaluation_predictions"],
        "infer_predictions": infer_result.tables["predictions"],
        **_prefixed_existing(train_result.tables, "train", exclude={"validation_predictions"}),
    }

    summary = {
        "pipeline_kind": "compatibility_train_eval_infer",
        "pipeline_mode": mode,
        "model_name": train_model_info.get("model_name") or train_model_info.get("best_model_name") or "unknown",
        "produced_model_name": train_model_info.get("produced_model_name")
        or train_model_info.get("model_name")
        or train_model_info.get("best_model_name")
        or "unknown",
        "artifact_kind": train_model_info.get("artifact_kind", "model"),
        "selection_metric": train_cfg.get("model", {}).get("selection_metric"),
        "train_run_dir": str(train_result.run_dir),
        "eval_run_dir": str(eval_result.run_dir),
        "infer_run_dir": str(infer_result.run_dir),
        "model": str(train_result.artifacts["model"]),
        "model_info": str(train_model_info_path) if train_model_info_path else None,
        "leaderboard": str(train_result.tables["leaderboard"]) if "leaderboard" in train_result.tables else None,
        "ensemble_info": str(train_result.artifacts["ensemble_info"]) if "ensemble_info" in train_result.artifacts else None,
        "ensemble_predictions": str(train_result.tables["ensemble_predictions"])
        if "ensemble_predictions" in train_result.tables
        else None,
        "evaluation_predictions": str(eval_result.tables["evaluation_predictions"]),
        "predictions": str(infer_result.tables["predictions"]),
        "metrics": metrics,
        "artifacts": _path_map(artifacts),
        "tables": _path_map(tables),
    }

    summary_path = write_json(summary, pipeline_dir / "pipeline_summary.json")
    metrics_path = write_json(metrics, pipeline_dir / "metrics.json")
    config_path = write_config_snapshot(cfg, pipeline_dir)
    artifacts.update({"summary": summary_path, "metrics": metrics_path, "config": config_path})
    manifest_path = write_manifest(
        pipeline_dir,
        config=cfg,
        metrics=metrics,
        artifacts=artifacts,
        tables=tables,
        extra=summary,
    )
    artifacts["manifest"] = manifest_path
    update_latest(pipeline_dir, output_dir / "latest_pipeline")
    update_latest(pipeline_dir, output_dir / "latest")

    return RunResult(run_dir=pipeline_dir, metrics=metrics, artifacts=artifacts, tables=tables, extra=summary)


def _metric_name(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _metric_names(metric_names: Any, selection_metric: str) -> list[str] | str | None:
    if metric_names is None:
        names = list(DEFAULT_REGRESSION_METRICS)
    elif isinstance(metric_names, str):
        names = [_metric_name(name) for name in metric_names.split(",") if name.strip()]
    else:
        names = [_metric_name(name) for name in metric_names]
    for name in [*LEADERBOARD_METRICS, selection_metric]:
        if name not in names:
            names.append(name)
    return names


def _safe_name(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value)
    return safe or "model"


def _selection_sort_value(metrics: dict[str, float], selection_metric: str) -> float:
    value = metric_value(metrics, selection_metric)
    return -value if selection_metric == "r2" else value


def _ranked_results(results: list[dict[str, Any]], selection_metric: str) -> list[dict[str, Any]]:
    return sorted(results, key=lambda item: _selection_sort_value(item["metrics"], selection_metric))


def _transformed_columns(transformer: Any) -> list[str]:
    columns = list(getattr(transformer, "numeric_cols", []))
    for col in getattr(transformer, "categorical_cols", []):
        for level in getattr(transformer, "category_levels", {}).get(col, []):
            columns.append(f"{col}={level}")
    return columns


def _xy_frame(X: pd.DataFrame, y, target_column: str) -> pd.DataFrame:
    frame = X.reset_index(drop=True).copy()
    frame[target_column] = list(pd.Series(y).reset_index(drop=True))
    return frame


def _preprocess_features(cfg: dict[str, Any], pipeline_dir: Path) -> dict[str, Any]:
    stage_dir = pipeline_dir / "preprocess_features"
    stage_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataset(cfg)
    X, y, feature_columns = split_xy(df, cfg)
    X_train, X_valid, y_train, y_valid = train_valid_split(X, y, cfg)

    feature_cfg = cfg.get("features", {})
    feature_preset = feature_cfg.get("preset", "basic")
    transformer = build_feature_pipeline(feature_preset, X_train, feature_cfg.get("params") or {})
    transformed_columns = _transformed_columns(transformer)

    train_features_path = write_table(
        pd.DataFrame(transformer.transform(X_train), columns=transformed_columns),
        stage_dir / "train_features.csv",
    )
    valid_features_path = write_table(
        pd.DataFrame(transformer.transform(X_valid), columns=transformed_columns),
        stage_dir / "valid_features.csv",
    )
    target_column = cfg.get("data", {}).get("target_column")
    processed_train_path = write_table(_xy_frame(X_train, y_train, target_column), stage_dir / "processed_train.csv")
    processed_valid_path = write_table(_xy_frame(X_valid, y_valid, target_column), stage_dir / "processed_valid.csv")
    preprocess_bundle_path = dump_joblib(
        {
            "transformer": transformer,
            "feature_columns": feature_columns,
            "target_column": target_column,
            "feature_preset": feature_preset,
            "feature_params": feature_cfg.get("params") or {},
        },
        stage_dir / "preprocess_bundle.joblib",
    )
    feature_spec_path = write_json(
        {
            "stage": "preprocess_features",
            "input_rows": len(df),
            "train_rows": len(X_train),
            "valid_rows": len(X_valid),
            "target_column": target_column,
            "feature_columns": feature_columns,
            "id_columns": cfg.get("data", {}).get("id_columns", []),
            "feature_preset": feature_preset,
            "numeric_columns": getattr(transformer, "numeric_cols", []),
            "categorical_columns": getattr(transformer, "categorical_cols", []),
            "transformed_columns": transformed_columns,
        },
        stage_dir / "feature_spec.json",
    )

    return {
        "stage": "preprocess_features",
        "stage_dir": stage_dir,
        "transformer": transformer,
        "feature_columns": feature_columns,
        "target_column": target_column,
        "feature_preset": feature_preset,
        "X_train": X_train,
        "X_valid": X_valid,
        "y_train": y_train,
        "y_valid": y_valid,
        "artifacts": {
            "preprocess_bundle": preprocess_bundle_path,
            "feature_spec": feature_spec_path,
        },
        "tables": {
            "train_features": train_features_path,
            "valid_features": valid_features_path,
            "processed_train": processed_train_path,
            "processed_valid": processed_valid_path,
        },
    }


def _train_model(
    cfg: dict[str, Any],
    preprocess: dict[str, Any],
    candidate: dict[str, Any],
    pipeline_dir: Path,
    metric_names: list[str] | str | None,
) -> dict[str, Any]:
    model_name = candidate["name"]
    model_params = candidate["params"]
    stage_name = f"train_{_safe_name(model_name)}"
    stage_dir = pipeline_dir / stage_name
    stage_dir.mkdir(parents=True, exist_ok=True)

    model = build_model(model_name, model_params)
    estimator = TabularEstimator(
        transformer=preprocess["transformer"],
        model=model,
        feature_columns=preprocess["feature_columns"],
    )
    estimator.fit(preprocess["X_train"], preprocess["y_train"])
    y_pred = estimator.predict(preprocess["X_valid"])
    metrics = regression_metrics(preprocess["y_valid"], y_pred, metrics=metric_names)

    predictions_frame = _xy_frame(preprocess["X_valid"], preprocess["y_valid"], preprocess["target_column"])
    predictions_frame["_prediction"] = y_pred
    predictions_frame["_model_name"] = model_name
    validation_predictions_path = write_table(predictions_frame, stage_dir / "validation_predictions.csv")
    model_path = dump_joblib(estimator, stage_dir / "model.joblib")
    model_info_path = write_model_info(
        stage_dir / "model_info.json",
        feature_columns=preprocess["feature_columns"],
        target_column=preprocess["target_column"],
        feature_preset=preprocess["feature_preset"],
        model_name=model_name,
        model_params=model_params,
        artifact_kind="model",
        extra={"stage": stage_name},
    )
    metrics_path = write_json(metrics, stage_dir / "metrics.json")

    return {
        "stage": stage_name,
        "stage_dir": stage_dir,
        "model_name": model_name,
        "model_params": model_params,
        "artifact_kind": "model",
        "estimator": estimator,
        "predictions": y_pred,
        "metrics": metrics,
        "artifacts": {
            "model": model_path,
            "model_info": model_info_path,
            "metrics": metrics_path,
        },
        "tables": {"validation_predictions": validation_predictions_path},
    }


def _build_ensemble(
    cfg: dict[str, Any],
    preprocess: dict[str, Any],
    ranked: list[dict[str, Any]],
    pipeline_dir: Path,
    metric_names: list[str] | str | None,
    selection_metric: str,
) -> dict[str, Any] | None:
    ensemble_cfg = ensemble_config(cfg.get("model", {}))
    if not ensemble_cfg["enabled"]:
        return None

    stage_dir = pipeline_dir / "build_ensemble"
    stage_dir.mkdir(parents=True, exist_ok=True)
    selected = ranked[: min(int(ensemble_cfg["top_k"]), len(ranked))]
    weights = ensemble_weights(selected, ensemble_cfg["method"], selection_metric)
    estimator = MeanTopKEnsemble([item["estimator"] for item in selected], weights=weights)
    y_pred = estimator.predict(preprocess["X_valid"])
    metrics = regression_metrics(preprocess["y_valid"], y_pred, metrics=metric_names)
    model_name = "weighted" if ensemble_cfg["method"] == "weighted" else "mean_topk"
    model_params = {
        "method": ensemble_cfg["method"],
        "top_k": len(selected),
        "selection_metric": selection_metric,
    }
    selected_base_models = [
        {
            "rank": rank,
            "model_name": item["model_name"],
            "model_params": item["model_params"],
            "stage": item["stage"],
            "artifact_path": str(item["artifacts"]["model"]),
            "weight": weights[rank - 1],
        }
        for rank, item in enumerate(selected, start=1)
    ]

    predictions_frame = _xy_frame(preprocess["X_valid"], preprocess["y_valid"], preprocess["target_column"])
    predictions_frame["_prediction"] = y_pred
    predictions_frame["_model_name"] = model_name
    ensemble_predictions_path = write_table(predictions_frame, stage_dir / "ensemble_predictions.csv")
    model_path = dump_joblib(estimator, stage_dir / "model.joblib")
    model_info_path = write_model_info(
        stage_dir / "model_info.json",
        feature_columns=preprocess["feature_columns"],
        target_column=preprocess["target_column"],
        feature_preset=preprocess["feature_preset"],
        model_name=model_name,
        model_params=model_params,
        artifact_kind="ensemble",
        extra={
            "stage": "build_ensemble",
            "ensemble_method": ensemble_cfg["method"],
            "top_k": len(selected),
            "selection_metric": selection_metric,
            "selected_base_models": selected_base_models,
            "weights": weights,
        },
    )
    ensemble_info_path = write_json(
        {
            "enabled": True,
            "method": ensemble_cfg["method"],
            "top_k": len(selected),
            "selection_metric": selection_metric,
            "produced_model_name": model_name,
            "selected_base_models": selected_base_models,
            "weights": weights,
            "model_artifact": str(model_path),
        },
        stage_dir / "ensemble_info.json",
    )
    metrics_path = write_json(metrics, stage_dir / "metrics.json")
    return {
        "stage": "build_ensemble",
        "stage_dir": stage_dir,
        "model_name": model_name,
        "model_params": model_params,
        "artifact_kind": "ensemble",
        "estimator": estimator,
        "predictions": y_pred,
        "metrics": metrics,
        "selected_base_models": selected_base_models,
        "artifacts": {
            "model": model_path,
            "model_info": model_info_path,
            "ensemble_info": ensemble_info_path,
            "metrics": metrics_path,
        },
        "tables": {"ensemble_predictions": ensemble_predictions_path},
    }


def _leaderboard_rows(results: list[dict[str, Any]], selection_metric: str) -> list[dict[str, Any]]:
    rows = []
    for rank, item in enumerate(results, start=1):
        row = {
            "rank": rank,
            "model_name": item["model_name"],
            "artifact_kind": item["artifact_kind"],
            "stage": item["stage"],
            "selection_metric": selection_metric,
            "model_params": json.dumps(item["model_params"], sort_keys=True, default=str),
            "artifact_name": "model",
            "artifact_path": str(item["artifacts"]["model"]),
        }
        for name in LEADERBOARD_METRICS:
            row[name] = item["metrics"].get(name)
        rows.append(row)
    return rows


def _evaluate_models(
    cfg: dict[str, Any],
    model_results: list[dict[str, Any]],
    ensemble_result: dict[str, Any] | None,
    pipeline_dir: Path,
    selection_metric: str,
) -> dict[str, Any]:
    stage_dir = pipeline_dir / "evaluate_models"
    stage_dir.mkdir(parents=True, exist_ok=True)
    candidates = [*model_results]
    if ensemble_result is not None:
        candidates.append(ensemble_result)
    ranked = _ranked_results(candidates, selection_metric)
    best = ranked[0]

    leaderboard_path = write_table(pd.DataFrame(_leaderboard_rows(ranked, selection_metric)), stage_dir / "leaderboard.csv")
    best_model_path = stage_dir / "best_model.joblib"
    shutil.copy2(best["artifacts"]["model"], best_model_path)
    best_payload = {
        "model_name": best["model_name"],
        "artifact_kind": best["artifact_kind"],
        "stage": best["stage"],
        "selection_metric": selection_metric,
        "selection_value": metric_value(best["metrics"], selection_metric),
        "metrics": best["metrics"],
        "model_params": best["model_params"],
        "source_artifact": str(best["artifacts"]["model"]),
        "best_model_artifact": str(best_model_path),
    }
    best_model_json_path = write_json(best_payload, stage_dir / "best_model.json")
    report = {
        "stage": "evaluate_models",
        "candidate_count": len(model_results),
        "ensemble_enabled": ensemble_result is not None,
        "selection_metric": selection_metric,
        "best_model": best_payload,
        "ranked_models": _leaderboard_rows(ranked, selection_metric),
    }
    evaluation_report_path = write_json(report, stage_dir / "evaluation_report.json")
    metrics_payload = {
        **best["metrics"],
        "best_model": best_payload,
        "selection_metric": selection_metric,
        "candidate_count": len(model_results),
        "ensemble_enabled": ensemble_result is not None,
    }
    metrics_path = write_json(metrics_payload, stage_dir / "metrics.json")
    return {
        "stage": "evaluate_models",
        "stage_dir": stage_dir,
        "best": best,
        "metrics": metrics_payload,
        "report": report,
        "artifacts": {
            "best_model": best_model_path,
            "best_model_json": best_model_json_path,
            "evaluation_report": evaluation_report_path,
            "metrics": metrics_path,
        },
        "tables": {"leaderboard": leaderboard_path},
    }


def _run_search_trials(
    cfg: dict[str, Any],
    preprocess: dict[str, Any],
    pipeline_dir: Path,
    metric_names: list[str] | str | None,
    selection_metric: str,
) -> dict[str, Any]:
    model_cfg = cfg.get("model", {})
    search_cfg = search_config(model_cfg)
    if not search_cfg["enabled"]:
        raise ValueError("search_trials stage requires model.search.enabled=true.")

    stage_dir = pipeline_dir / "search_trials"
    stage_dir.mkdir(parents=True, exist_ok=True)
    candidates = model_candidates(model_cfg)
    comparison = bool(model_cfg.get("candidates"))
    trials = search_trials(
        candidates,
        search_cfg,
        comparison=comparison,
        seed=int(cfg.get("run", {}).get("seed", 42)),
    )
    if not trials:
        raise ValueError("model.search produced no trials.")

    candidate_results = []
    for trial in trials:
        model = build_model(trial["model_name"], trial["model_params"])
        estimator = TabularEstimator(
            transformer=preprocess["transformer"],
            model=model,
            feature_columns=preprocess["feature_columns"],
        )
        estimator.fit(preprocess["X_train"], preprocess["y_train"])
        y_pred = estimator.predict(preprocess["X_valid"])
        metrics = regression_metrics(preprocess["y_valid"], y_pred, metrics=metric_names)
        candidate_results.append(
            {
                "trial": trial["trial"],
                "model_name": trial["model_name"],
                "model_params": trial["model_params"],
                "estimator": estimator,
                "predictions": y_pred,
                "metrics": metrics,
            }
        )

    ranked = ranked_search_results(candidate_results, selection_metric)
    best = ranked[0]
    optimization_trials_path = write_table(
        pd.DataFrame(optimization_trial_rows(candidate_results, selection_metric)),
        stage_dir / "optimization_trials.csv",
    )
    best_metrics = dict(best["metrics"])
    best_params_payload = {
        "model_name": best["model_name"],
        "model_params": best["model_params"],
        "selection_metric": selection_metric,
        "selection_value": metric_value(best_metrics, selection_metric),
        "best_trial": int(best["trial"]),
        "retrain_best": search_cfg["retrain_best"],
        "retrained_on_available_data": False,
        "validation_metrics": best_metrics,
    }
    best_params_path = write_json(best_params_payload, stage_dir / "best_params.json")
    optimization_summary = {
        "enabled": True,
        "stage": "search_trials",
        "method": search_cfg["method"],
        "max_trials": search_cfg["max_trials"],
        "completed_trials": len(candidate_results),
        "selection_metric": selection_metric,
        "best_trial": int(best["trial"]),
        "best_model_name": best["model_name"],
        "best_model_params": best["model_params"],
        "best_metrics": best_metrics,
        "optimization_trials": str(optimization_trials_path),
        "best_params": str(best_params_path),
        "retrain_best": search_cfg["retrain_best"],
        "metric_source": "search_trials_validation",
    }
    optimization_summary_path = write_json(optimization_summary, stage_dir / "optimization_summary.json")
    metrics_payload = {
        **best_metrics,
        "search": optimization_summary,
        "metric_source": "search_trials_validation",
    }
    metrics_path = write_json(metrics_payload, stage_dir / "metrics.json")

    return {
        "stage": "search_trials",
        "stage_dir": stage_dir,
        "best": best,
        "search": optimization_summary,
        "metrics": metrics_payload,
        "artifacts": {
            "optimization_summary": optimization_summary_path,
            "best_params": best_params_path,
            "metrics": metrics_path,
        },
        "tables": {"optimization_trials": optimization_trials_path},
    }


def _retrain_best(
    cfg: dict[str, Any],
    preprocess: dict[str, Any],
    best_params_path: Path,
    pipeline_dir: Path,
) -> dict[str, Any]:
    best_params = read_json(best_params_path)
    stage_dir = pipeline_dir / "retrain_best"
    stage_dir.mkdir(parents=True, exist_ok=True)

    model_name = str(best_params.get("model_name") or "")
    model_params = best_params.get("model_params") or {}
    if not model_name:
        raise ValueError("best_params.model_name is required.")
    if not isinstance(model_params, dict):
        raise ValueError("best_params.model_params must be a mapping.")

    X_full = pd.concat([preprocess["X_train"], preprocess["X_valid"]], ignore_index=True)
    y_full = pd.concat(
        [pd.Series(preprocess["y_train"]), pd.Series(preprocess["y_valid"])],
        ignore_index=True,
    )
    estimator = TabularEstimator(
        transformer=preprocess["transformer"],
        model=build_model(model_name, model_params),
        feature_columns=preprocess["feature_columns"],
    )
    estimator.fit(X_full, y_full)

    model_path = dump_joblib(estimator, stage_dir / "model.joblib")
    best_params_copy = stage_dir / "best_params.json"
    shutil.copy2(best_params_path, best_params_copy)
    validation_metrics = dict(best_params.get("validation_metrics") or {})
    model_info_path = write_model_info(
        stage_dir / "model_info.json",
        feature_columns=preprocess["feature_columns"],
        target_column=preprocess["target_column"],
        feature_preset=preprocess["feature_preset"],
        model_name=model_name,
        model_params=model_params,
        artifact_kind="model",
        extra={
            "stage": "retrain_best",
            "search": {
                "enabled": True,
                "best_trial": best_params.get("best_trial"),
                "selection_metric": best_params.get("selection_metric"),
                "selection_value": best_params.get("selection_value"),
                "metric_source": "search_trials_validation",
                "retrained_on_available_data": True,
            },
        },
    )
    metrics_payload = {
        **validation_metrics,
        "best_trial": best_params.get("best_trial"),
        "selection_metric": best_params.get("selection_metric"),
        "metric_source": "search_trials_validation",
        "retrained_on_available_data": True,
    }
    metrics_path = write_json(metrics_payload, stage_dir / "metrics.json")

    return {
        "stage": "retrain_best",
        "stage_dir": stage_dir,
        "model_name": model_name,
        "model_params": model_params,
        "artifact_kind": "model",
        "metrics": metrics_payload,
        "artifacts": {
            "model": model_path,
            "model_info": model_info_path,
            "best_params": best_params_copy,
            "metrics": metrics_path,
        },
    }


def _evaluate_best(
    cfg: dict[str, Any],
    best_params_path: Path,
    optimization_summary_path: Path,
    model_path: Path,
    model_info_path: Path,
    pipeline_dir: Path,
    selection_metric: str,
) -> dict[str, Any]:
    stage_dir = pipeline_dir / "evaluate_best"
    stage_dir.mkdir(parents=True, exist_ok=True)
    best_params = read_json(best_params_path)
    optimization_summary = read_json(optimization_summary_path)
    validation_metrics = dict(best_params.get("validation_metrics") or optimization_summary.get("best_metrics") or {})

    best_model_path = stage_dir / "best_model.joblib"
    shutil.copy2(model_path, best_model_path)
    best_payload = {
        "model_name": best_params["model_name"],
        "artifact_kind": "model",
        "stage": "retrain_best",
        "selection_metric": selection_metric,
        "selection_value": metric_value(validation_metrics, selection_metric),
        "metrics": validation_metrics,
        "model_params": best_params["model_params"],
        "source_artifact": str(model_path),
        "source_model_info": str(model_info_path),
        "best_model_artifact": str(best_model_path),
        "best_trial": best_params.get("best_trial"),
        "metric_source": "search_trials_validation",
    }
    best_model_json_path = write_json(best_payload, stage_dir / "best_model.json")
    report = {
        "stage": "evaluate_best",
        "optimization_enabled": True,
        "selection_metric": selection_metric,
        "metric_source": "search_trials_validation",
        "best_model": best_payload,
        "optimization_summary": optimization_summary,
    }
    evaluation_report_path = write_json(report, stage_dir / "evaluation_report.json")
    metrics_payload = {
        **validation_metrics,
        "best_model": best_payload,
        "selection_metric": selection_metric,
        "metric_source": "search_trials_validation",
        "optimization": optimization_summary,
    }
    metrics_path = write_json(metrics_payload, stage_dir / "metrics.json")
    return {
        "stage": "evaluate_best",
        "stage_dir": stage_dir,
        "metrics": metrics_payload,
        "report": report,
        "artifacts": {
            "best_model": best_model_path,
            "best_model_json": best_model_json_path,
            "evaluation_report": evaluation_report_path,
            "metrics": metrics_path,
        },
    }


def _run_optimization_pipeline(cfg: dict[str, Any]) -> RunResult:
    model_cfg = cfg.get("model", {})
    search_cfg = search_config(model_cfg)
    ensemble_cfg = ensemble_config(model_cfg)
    if not search_cfg["enabled"]:
        raise ValueError("Optimization pipeline requires model.search.enabled=true.")
    if ensemble_cfg["enabled"]:
        raise ValueError("model.search.enabled=true cannot be combined with model.ensemble.enabled=true in Phase E.")

    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    run_name = cfg.get("run", {}).get("name", "tabular_optimization_pipeline")
    pipeline_dir = prepare_run_dir(output_dir, run_name)
    selection_metric = _metric_name(model_cfg.get("selection_metric") or "rmse")
    if selection_metric not in SELECTION_METRICS:
        raise ValueError("model.selection_metric must be one of: mae, rmse, r2.")
    metric_names = _metric_names(cfg.get("metrics", {}).get("names"), selection_metric)

    preprocess = _preprocess_features(cfg, pipeline_dir)
    search = _run_search_trials(cfg, preprocess, pipeline_dir, metric_names, selection_metric)
    retrain = _retrain_best(cfg, preprocess, search["artifacts"]["best_params"], pipeline_dir)
    evaluation = _evaluate_best(
        cfg,
        search["artifacts"]["best_params"],
        search["artifacts"]["optimization_summary"],
        retrain["artifacts"]["model"],
        retrain["artifacts"]["model_info"],
        pipeline_dir,
        selection_metric,
    )

    artifacts: dict[str, Path] = {
        **preprocess["artifacts"],
        "optimization_summary": search["artifacts"]["optimization_summary"],
        "best_params": search["artifacts"]["best_params"],
        "search_metrics": search["artifacts"]["metrics"],
        "model": retrain["artifacts"]["model"],
        "model_info": retrain["artifacts"]["model_info"],
        **evaluation["artifacts"],
    }
    tables: dict[str, Path] = {
        **preprocess["tables"],
        "optimization_trials": search["tables"]["optimization_trials"],
    }
    summary = {
        "pipeline_kind": "optimization",
        "stages": ["preprocess_features", "search_trials", "retrain_best", "evaluate_best"],
        "selection_metric": selection_metric,
        "search": search["search"],
        "best_model": evaluation["report"]["best_model"],
        "artifacts": _path_map(artifacts),
        "tables": _path_map(tables),
    }

    metrics_path = write_json(evaluation["metrics"], pipeline_dir / "metrics.json")
    config_path = write_config_snapshot(cfg, pipeline_dir)
    artifacts.update({"metrics": metrics_path, "config": config_path})
    manifest_path = write_manifest(
        pipeline_dir,
        config=cfg,
        metrics=evaluation["metrics"],
        artifacts=artifacts,
        tables=tables,
        extra=summary,
    )
    artifacts["manifest"] = manifest_path
    update_latest(pipeline_dir, output_dir / "latest_optimization_pipeline")
    update_latest(pipeline_dir, output_dir / "latest_training_pipeline")
    update_latest(pipeline_dir, output_dir / "latest")

    return RunResult(run_dir=pipeline_dir, metrics=evaluation["metrics"], artifacts=artifacts, tables=tables, extra=summary)


def _run_training_pipeline(cfg: dict[str, Any]) -> RunResult:
    model_cfg = cfg.get("model", {})
    search_cfg = search_config(model_cfg)
    if search_cfg["enabled"]:
        return _run_optimization_pipeline(cfg)

    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    run_name = cfg.get("run", {}).get("name", "tabular_training_pipeline")
    pipeline_dir = prepare_run_dir(output_dir, run_name)
    selection_metric = _metric_name(model_cfg.get("selection_metric") or "rmse")
    if selection_metric not in SELECTION_METRICS:
        raise ValueError("model.selection_metric must be one of: mae, rmse, r2.")
    metric_names = _metric_names(cfg.get("metrics", {}).get("names"), selection_metric)

    preprocess = _preprocess_features(cfg, pipeline_dir)
    candidates = model_candidates(model_cfg)
    model_results = [_train_model(cfg, preprocess, candidate, pipeline_dir, metric_names) for candidate in candidates]
    ranked_models = _ranked_results(model_results, selection_metric)
    ensemble_result = _build_ensemble(cfg, preprocess, ranked_models, pipeline_dir, metric_names, selection_metric)
    evaluation = _evaluate_models(cfg, model_results, ensemble_result, pipeline_dir, selection_metric)

    artifacts: dict[str, Path] = {
        **preprocess["artifacts"],
        "leaderboard": evaluation["tables"]["leaderboard"],
        **evaluation["artifacts"],
    }
    tables: dict[str, Path] = {
        **preprocess["tables"],
        "leaderboard": evaluation["tables"]["leaderboard"],
    }
    for item in model_results:
        key = _safe_name(item["model_name"])
        artifacts[f"model_{key}"] = item["artifacts"]["model"]
        artifacts[f"model_info_{key}"] = item["artifacts"]["model_info"]
        artifacts[f"metrics_{key}"] = item["artifacts"]["metrics"]
        tables[f"validation_predictions_{key}"] = item["tables"]["validation_predictions"]
    if ensemble_result is not None:
        artifacts["ensemble"] = ensemble_result["artifacts"]["model"]
        artifacts["ensemble_info"] = ensemble_result["artifacts"]["ensemble_info"]
        artifacts["ensemble_model_info"] = ensemble_result["artifacts"]["model_info"]
        tables["ensemble_predictions"] = ensemble_result["tables"]["ensemble_predictions"]

    summary = {
        "pipeline_kind": "training",
        "stages": [
            "preprocess_features",
            *[item["stage"] for item in model_results],
            *(["build_ensemble"] if ensemble_result is not None else []),
            "evaluate_models",
        ],
        "candidate_models": [item["model_name"] for item in model_results],
        "selection_metric": selection_metric,
        "best_model": evaluation["report"]["best_model"],
        "ensemble": (
            {
                "enabled": True,
                "model_name": ensemble_result["model_name"],
                "artifact": str(ensemble_result["artifacts"]["model"]),
                "selected_base_models": ensemble_result.get("selected_base_models", []),
            }
            if ensemble_result is not None
            else {"enabled": False}
        ),
        "artifacts": _path_map(artifacts),
        "tables": _path_map(tables),
    }

    metrics_path = write_json(evaluation["metrics"], pipeline_dir / "metrics.json")
    config_path = write_config_snapshot(cfg, pipeline_dir)
    artifacts.update({"metrics": metrics_path, "config": config_path})
    manifest_path = write_manifest(
        pipeline_dir,
        config=cfg,
        metrics=evaluation["metrics"],
        artifacts=artifacts,
        tables=tables,
        extra=summary,
    )
    artifacts["manifest"] = manifest_path
    update_latest(pipeline_dir, output_dir / "latest_training_pipeline")
    update_latest(pipeline_dir, output_dir / "latest")

    return RunResult(run_dir=pipeline_dir, metrics=evaluation["metrics"], artifacts=artifacts, tables=tables, extra=summary)


def run_pipeline(cfg: dict[str, Any]) -> RunResult:
    if "data" in cfg:
        return _run_training_pipeline(cfg)
    return _run_compatibility_full_run(cfg)
