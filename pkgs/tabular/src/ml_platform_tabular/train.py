from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ml_platform_core.artifacts import (
    prepare_run_dir,
    update_latest,
    write_config_snapshot,
    write_manifest,
)
from ml_platform_core.io import dump_joblib, write_json, write_table
from ml_platform_core.result import RunResult

from .data import load_dataset, split_xy, train_valid_split
from .ensemble import ensemble_config as _ensemble_cfg
from .ensemble import ensemble_weights as _ensemble_weights
from .ensemble import metric_value as _metric_value
from .features import build_feature_pipeline
from .metrics import DEFAULT_REGRESSION_METRICS, regression_metrics, regression_prediction_frame, write_regression_plot_artifacts
from .model_artifact import write_model_info
from .models import MeanTopKEnsemble, TabularEstimator, build_model, model_candidates
from .search import optimization_trial_rows, search_config, search_trials

LEADERBOARD_METRICS = ["rmse", "mae", "r2"]
SELECTION_METRICS = {"rmse", "mae", "r2"}


def _metric_name(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _metric_names_for_training(metric_names: Any, selection_metric: str, *, comparison: bool = False) -> list[str] | str | None:
    if metric_names is None:
        names = list(DEFAULT_REGRESSION_METRICS)
        if selection_metric not in names:
            names.append(selection_metric)
        return names
    if isinstance(metric_names, str):
        names = [_metric_name(name) for name in metric_names.split(",") if name.strip()]
    else:
        names = [_metric_name(name) for name in metric_names]
    if comparison:
        for name in LEADERBOARD_METRICS:
            if name not in names:
                names.append(name)
    if selection_metric not in names:
        names.append(selection_metric)
    return names


def _selection_sort_value(metrics: dict[str, float], selection_metric: str) -> float:
    value = _metric_value(metrics, selection_metric)
    return -value if selection_metric == "r2" else value


def _ranked_candidates(candidate_results: list[dict[str, Any]], selection_metric: str) -> list[dict[str, Any]]:
    return sorted(candidate_results, key=lambda item: _selection_sort_value(item["metrics"], selection_metric))


def _leaderboard_rows(
    ranked_results: list[dict[str, Any]],
    *,
    selection_metric: str,
    artifact_names: dict[str, str],
) -> list[dict[str, Any]]:
    rows = []
    for rank, item in enumerate(ranked_results, start=1):
        metrics = item["metrics"]
        row = {
            "rank": rank,
            "model_name": item["model_name"],
            "selection_metric": selection_metric,
        }
        for name in LEADERBOARD_METRICS:
            row[name] = metrics.get(name)
        row["model_params"] = json.dumps(item["model_params"], sort_keys=True, default=str)
        row["artifact_name"] = artifact_names.get(item["model_name"], "")
        rows.append(row)
    return rows


def _base_model_path(base_dir: Path, rank: int, model_name: str) -> Path:
    safe_name = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in model_name)
    return base_dir / f"{rank:02d}_{safe_name}.joblib"


def run_train(cfg: dict[str, Any]) -> RunResult:
    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    run_name = cfg.get("run", {}).get("name", "tabular_train")
    run_dir = prepare_run_dir(output_dir, run_name)

    df = load_dataset(cfg)
    X, y, feature_names = split_xy(df, cfg)
    X_train, X_valid, y_train, y_valid = train_valid_split(X, y, cfg)

    feature_cfg = cfg.get("features", {})
    feature_preset = feature_cfg.get("preset", "basic")
    transformer = build_feature_pipeline(feature_preset, X_train, feature_cfg.get("params") or {})

    model_cfg = cfg.get("model", {})
    metric_names = cfg.get("metrics", {}).get("names")
    selection_metric = _metric_name(model_cfg.get("selection_metric") or "rmse")
    candidates = model_candidates(model_cfg)
    comparison = bool(model_cfg.get("candidates"))
    ensemble_cfg = _ensemble_cfg(model_cfg)
    ensemble_enabled = bool(ensemble_cfg["enabled"])
    search_cfg = search_config(model_cfg)
    search_enabled = bool(search_cfg["enabled"])
    if ensemble_enabled and not comparison:
        raise ValueError("model.ensemble.enabled=true requires model.candidates.")
    if search_enabled and ensemble_enabled:
        raise ValueError("model.search.enabled=true cannot be combined with model.ensemble.enabled=true in V2.1.")
    if selection_metric not in SELECTION_METRICS:
        raise ValueError("model.selection_metric must be one of: mae, rmse, r2.")
    train_metric_names = _metric_names_for_training(metric_names, selection_metric, comparison=comparison or search_enabled)

    candidate_results = []
    trials = search_trials(
        candidates,
        search_cfg,
        comparison=comparison,
        seed=int(cfg.get("run", {}).get("seed", 42)),
    )
    for trial in trials:
        model = build_model(trial["model_name"], trial["model_params"])
        estimator = TabularEstimator(transformer=transformer, model=model, feature_columns=feature_names)
        estimator.fit(X_train, y_train)
        y_pred = estimator.predict(X_valid)
        metrics = regression_metrics(y_valid, y_pred, metrics=train_metric_names)
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

    ranked_results = _ranked_candidates(candidate_results, selection_metric)
    best = ranked_results[0]
    base_model_artifacts: dict[str, Path] = {}
    selected_base_models: list[dict[str, Any]] = []
    artifact_names: dict[str, str] = {best["model_name"]: "model"}

    if ensemble_enabled:
        selected_results = ranked_results[: min(int(ensemble_cfg["top_k"]), len(ranked_results))]
        weights = _ensemble_weights(selected_results, ensemble_cfg["method"], selection_metric)
        base_model_dir = run_dir / "base_models"
        base_model_dir.mkdir(parents=True, exist_ok=True)
        artifact_names = {}
        for rank, item in enumerate(selected_results, start=1):
            base_path = dump_joblib(item["estimator"], _base_model_path(base_model_dir, rank, item["model_name"]))
            artifact_key = f"base_model_{rank}_{item['model_name']}"
            base_model_artifacts[artifact_key] = base_path
            artifact_names[item["model_name"]] = str(base_path.relative_to(run_dir))
            selected_base_models.append(
                {
                    "rank": rank,
                    "model_name": item["model_name"],
                    "model_params": item["model_params"],
                    "artifact_name": artifact_key,
                    "artifact_path": str(base_path),
                    "weight": weights[rank - 1],
                }
            )
        estimator = MeanTopKEnsemble([item["estimator"] for item in selected_results], weights=weights)
        y_pred = estimator.predict(X_valid)
        metrics = regression_metrics(y_valid, y_pred, metrics=train_metric_names)
        model_name = "mean_topk"
        if ensemble_cfg["method"] == "weighted":
            model_name = "weighted"
        model_params = {
            "method": ensemble_cfg["method"],
            "top_k": len(selected_results),
            "selection_metric": selection_metric,
        }
    else:
        model_name = best["model_name"]
        model_params = best["model_params"]
        estimator = best["estimator"]
        y_pred = best["predictions"]
        metrics = best["metrics"]

    retrained_on_full_data = False
    if search_enabled and bool(search_cfg["retrain_best"]):
        final_transformer = build_feature_pipeline(feature_preset, X, feature_cfg.get("params") or {})
        final_model = build_model(model_name, model_params)
        estimator = TabularEstimator(transformer=final_transformer, model=final_model, feature_columns=feature_names)
        estimator.fit(X, y)
        retrained_on_full_data = True

    validation_predictions_path = write_table(
        regression_prediction_frame(X_valid, y_valid, y_pred, model_name=model_name),
        run_dir / "validation_predictions.csv",
    )
    plots = write_regression_plot_artifacts(y_valid, y_pred, run_dir, prefix="validation")
    predictions_path = validation_predictions_path
    ensemble_predictions_path = None
    if ensemble_enabled:
        ensemble_predictions_path = write_table(
            regression_prediction_frame(X_valid, y_valid, y_pred, model_name=model_name),
            run_dir / "ensemble_predictions.csv",
        )
    model_path = dump_joblib(estimator, run_dir / "model.joblib")
    model_info_path = write_model_info(
        run_dir / "model_info.json",
        feature_columns=feature_names,
        target_column=cfg.get("data", {}).get("target_column"),
        feature_preset=feature_preset,
        model_name=model_name,
        model_params=model_params,
        artifact_kind="ensemble" if ensemble_enabled else "model",
        extra=(
            {
                "ensemble_method": ensemble_cfg["method"],
                "top_k": model_params["top_k"],
                "selection_metric": selection_metric,
                "selected_base_models": selected_base_models,
                "weights": [item["weight"] for item in selected_base_models],
            }
            if ensemble_enabled
            else None
        ),
    )
    ensemble_info_path = None
    if ensemble_enabled:
        ensemble_info_path = write_json(
            {
                "enabled": True,
                "method": ensemble_cfg["method"],
                "top_k": model_params["top_k"],
                "selection_metric": selection_metric,
                "produced_model_name": model_name,
                "selected_base_models": selected_base_models,
                "weights": [item["weight"] for item in selected_base_models],
            },
            run_dir / "ensemble_info.json",
        )
    if search_enabled:
        model_info = {
            "search": {
                "enabled": True,
                "method": search_cfg["method"],
                "max_trials": search_cfg["max_trials"],
                "completed_trials": len(candidate_results),
                "selection_metric": selection_metric,
                "best_trial": int(best["trial"]),
                "retrain_best": search_cfg["retrain_best"],
                "retrained_on_full_data": retrained_on_full_data,
            }
        }
        current_info = json.loads(model_info_path.read_text(encoding="utf-8"))
        current_info.update(model_info)
        model_info_path.write_text(json.dumps(current_info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    metrics_payload: dict[str, Any] = dict(metrics)
    config_path = write_config_snapshot(cfg, run_dir)

    artifacts = {
        "model": model_path,
        "model_info": model_info_path,
        "config": config_path,
        **base_model_artifacts,
    }
    if ensemble_info_path is not None:
        artifacts["ensemble_info"] = ensemble_info_path
    tables = {"validation_predictions": validation_predictions_path}
    if ensemble_predictions_path is not None:
        tables["ensemble_predictions"] = ensemble_predictions_path
    if search_enabled:
        optimization_trials_path = write_table(
            pd.DataFrame(optimization_trial_rows(candidate_results, selection_metric)),
            run_dir / "optimization_trials.csv",
        )
        optimization_summary = {
            "enabled": True,
            "method": search_cfg["method"],
            "max_trials": search_cfg["max_trials"],
            "completed_trials": len(candidate_results),
            "selection_metric": selection_metric,
            "best_trial": int(best["trial"]),
            "best_model_name": model_name,
            "best_model_params": model_params,
            "optimization_trials": str(optimization_trials_path),
            "retrain_best": search_cfg["retrain_best"],
            "retrained_on_full_data": retrained_on_full_data,
        }
        best_params_payload = {
            "model_name": model_name,
            "model_params": model_params,
            "selection_metric": selection_metric,
            "selection_value": _metric_value(metrics, selection_metric),
            "best_trial": int(best["trial"]),
            "retrain_best": search_cfg["retrain_best"],
            "retrained_on_full_data": retrained_on_full_data,
        }
        best_params_path = write_json(best_params_payload, run_dir / "best_params.json")
        optimization_summary["best_params"] = str(best_params_path)
        optimization_summary_path = write_json(optimization_summary, run_dir / "optimization_summary.json")
        tables["optimization_trials"] = optimization_trials_path
        artifacts["best_params"] = best_params_path
        artifacts["optimization_summary"] = optimization_summary_path
        metrics_payload["search"] = optimization_summary
    if comparison:
        leaderboard_results = ranked_results
        leaderboard_artifact_names = dict(artifact_names)
        if ensemble_enabled:
            leaderboard_results = _ranked_candidates(
                [
                    *ranked_results,
                    {
                        "model_name": model_name,
                        "model_params": model_params,
                        "metrics": metrics,
                    },
                ],
                selection_metric,
            )
            leaderboard_artifact_names[model_name] = "model"
        leaderboard_path = write_table(
            pd.DataFrame(
                _leaderboard_rows(
                    leaderboard_results,
                    selection_metric=selection_metric,
                    artifact_names=leaderboard_artifact_names,
                )
            ),
            run_dir / "leaderboard.csv",
        )
        tables["leaderboard"] = leaderboard_path
        metrics_payload["comparison"] = {
            "enabled": True,
            "selection_metric": selection_metric,
            "best_model_name": model_name,
            "candidate_count": len(candidates),
            "leaderboard": str(leaderboard_path),
        }
        if ensemble_enabled:
            metrics_payload["comparison"]["ensemble"] = {
                "enabled": True,
                "method": ensemble_cfg["method"],
                "top_k": model_params["top_k"],
                "selected_base_models": [item["model_name"] for item in selected_base_models],
            }
    metrics_path = write_json(metrics_payload, run_dir / "metrics.json")
    artifacts["metrics"] = metrics_path
    manifest_path = write_manifest(run_dir, config=cfg, metrics=metrics_payload, artifacts=artifacts, tables=tables)
    artifacts["manifest"] = manifest_path

    update_latest(run_dir, output_dir / "latest_train")
    update_latest(run_dir, output_dir / "latest")

    return RunResult(
        run_dir=run_dir,
        metrics=metrics,
        artifacts=artifacts,
        tables=tables,
        plots=plots,
        extra={"feature_columns": feature_names},
    )
