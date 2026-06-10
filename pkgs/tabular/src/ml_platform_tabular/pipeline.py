"""ClearML-free local training pipeline orchestration.

The official training graph is:
preprocess_features -> train_<model>* -> build_ensemble optional -> evaluate_models.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml_platform_core.artifacts import prepare_run_dir, update_latest, utc_timestamp, write_config_snapshot, write_manifest
from ml_platform_core.io import dump_joblib, write_json, write_table
from ml_platform_core.result import RunResult

from .data import load_dataset, split_xy, train_valid_split
from .ensemble import as_bool, ensemble_config, ensemble_weights, metric_value
from .features import build_feature_pipeline, normalize_feature_config
from .metrics import (
    DEFAULT_REGRESSION_METRICS,
    regression_metrics,
    regression_prediction_frame,
)
from .model_artifact import write_model_info
from .models import MeanTopKEnsemble, MedianEnsemble, TabularEstimator, build_model, model_candidates
from .plots import (
    topk_candidate_predictions,
    transformed_columns_from_transformer,
    write_candidate_prediction_vs_actual_plot,
    write_candidate_residual_histogram,
    write_candidate_residual_vs_predicted_plot,
    write_feature_importance_plot_if_available,
    write_feature_summary_tables,
    write_leaderboard_metric_panel,
    write_leaderboard_pareto_plot,
    write_leaderboard_table,
    write_metrics_bar_plot,
    write_metrics_by_candidate_table,
    write_prediction_vs_actual_plot,
    write_regression_plot_artifacts,
    write_residual_histogram,
    write_residual_vs_predicted_plot,
)

LEADERBOARD_METRICS = ["rmse", "mae", "r2"]
LEADERBOARD_TOP_K = 5
LEADERBOARD_REPORT_SCHEMA_VERSION = "leaderboard_dashboard_v2"
SELECTION_METRICS = {"rmse", "mae", "r2"}


def _path_map(mapping: dict[str, Path]) -> dict[str, str]:
    return {name: str(path) for name, path in mapping.items()}


def _code_version() -> str:
    try:
        root = Path(__file__).resolve().parents[4]
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return "unknown"
    version = completed.stdout.strip()
    return version or "unknown"


def _runtime_task_id() -> str | None:
    for name in ("CLEARML_TASK_ID", "TRAINS_TASK_ID", "TASK_ID"):
        value = os.environ.get(name)
        if value:
            return value
    return None


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
    return transformed_columns_from_transformer(transformer)


def _write_feature_visibility_artifacts(
    *,
    df: pd.DataFrame,
    X: pd.DataFrame,
    X_train: pd.DataFrame,
    X_valid: pd.DataFrame,
    target_column: str,
    feature_columns: list[str],
    transformed_columns: list[str],
    transformer: Any,
    feature_config: dict[str, Any],
    stage_dir: Path,
) -> tuple[dict[str, Path], dict[str, Path]]:
    tables = write_feature_summary_tables(
        df=df,
        X=X,
        X_train=X_train,
        X_valid=X_valid,
        target_column=target_column,
        feature_columns=feature_columns,
        transformed_columns=transformed_columns,
        transformer=transformer,
        feature_config=feature_config,
        output_dir=stage_dir,
    )
    missing_rate = pd.read_csv(tables["missing_rate_by_column"])
    missingness_bar_path = write_metrics_bar_plot(
        [(row.column, row.missing_rate) for row in missing_rate.itertuples(index=False)],
        stage_dir / "missing_rate_by_column_bar.png",
        title="Feature missing rate",
        value_label="missing_rate",
    )
    return tables, {"missing_rate_by_column_bar": missingness_bar_path, "feature_missingness_bar": missingness_bar_path}


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
    feature_config = normalize_feature_config(feature_cfg)
    feature_preset = feature_config["preset"]
    transformer = build_feature_pipeline(feature_preset, X_train, feature_config)
    transformed_columns = _transformed_columns(transformer)
    feature_tables, feature_plots = _write_feature_visibility_artifacts(
        df=df,
        X=X,
        X_train=X_train,
        X_valid=X_valid,
        target_column=cfg.get("data", {}).get("target_column"),
        feature_columns=feature_columns,
        transformed_columns=transformed_columns,
        transformer=transformer,
        feature_config=feature_config,
        stage_dir=stage_dir,
    )
    feature_summary_table_path = feature_tables["feature_summary_table"]
    missing_rate_by_column_path = feature_tables["missing_rate_by_column"]
    feature_type_counts_path = feature_tables["feature_type_counts"]

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
            "feature_params": feature_config.get("params") or {},
            "feature_config": feature_config,
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
            "feature_config": feature_config,
            "drop_columns": feature_config["drop_columns"],
            "passthrough_columns": feature_config["passthrough_columns"],
            "numeric_columns": getattr(transformer, "numeric_cols", []),
            "categorical_columns": getattr(transformer, "categorical_cols", []),
            "categorical_encoder": feature_config["categorical_encoder"],
            "numeric_impute_strategy": feature_config["numeric_impute_strategy"],
            "categorical_impute_strategy": feature_config["categorical_impute_strategy"],
            "scaling": feature_config["scaling"],
            "transformed_columns": transformed_columns,
        },
        stage_dir / "feature_spec.json",
    )
    feature_summary_path = write_json(
        {
            "stage": "preprocess_features",
            "input_rows": int(len(df)),
            "train_rows": int(len(X_train)),
            "valid_rows": int(len(X_valid)),
            "target_column": target_column,
            "feature_count": int(len(feature_columns)),
            "numeric_feature_count": int(len(getattr(transformer, "numeric_cols", []))),
            "categorical_feature_count": int(len(getattr(transformer, "categorical_cols", []))),
            "passthrough_feature_count": int(len(getattr(transformer, "passthrough_cols", []))),
            "dropped_feature_count": int(len(feature_config["drop_columns"])),
            "transformed_feature_count": int(len(transformed_columns)),
            "id_columns": cfg.get("data", {}).get("id_columns", []),
            "feature_columns": feature_columns,
            "feature_preset": feature_preset,
            "feature_config": feature_config,
            "drop_columns": feature_config["drop_columns"],
            "passthrough_columns": feature_config["passthrough_columns"],
            "numeric_impute_strategy": feature_config["numeric_impute_strategy"],
            "categorical_impute_strategy": feature_config["categorical_impute_strategy"],
            "categorical_encoder": feature_config["categorical_encoder"],
            "scaling": feature_config["scaling"],
        },
        stage_dir / "feature_summary.json",
    )

    return {
        "stage": "preprocess_features",
        "stage_dir": stage_dir,
        "transformer": transformer,
        "feature_columns": feature_columns,
        "target_column": target_column,
        "feature_preset": feature_preset,
        "feature_config": feature_config,
        "X_train": X_train,
        "X_valid": X_valid,
        "y_train": y_train,
        "y_valid": y_valid,
        "artifacts": {
            "preprocess_bundle": preprocess_bundle_path,
            "feature_spec": feature_spec_path,
            "feature_summary": feature_summary_path,
        },
        "tables": {
            "feature_summary_table": feature_summary_table_path,
            "feature_summary": feature_summary_table_path,
            "missing_rate_by_column": missing_rate_by_column_path,
            "feature_missingness": missing_rate_by_column_path,
            "feature_type_counts": feature_type_counts_path,
            "train_features": train_features_path,
            "valid_features": valid_features_path,
            "processed_train": processed_train_path,
            "processed_valid": processed_valid_path,
        },
        "plots": feature_plots,
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

    predictions_frame = regression_prediction_frame(
        preprocess["X_valid"],
        preprocess["y_valid"],
        y_pred,
        model_name=model_name,
    )
    validation_predictions_path = write_table(predictions_frame, stage_dir / "validation_predictions.csv")
    metrics_table_path = write_table(
        pd.DataFrame([{"metric": key, "value": value} for key, value in metrics.items()]),
        stage_dir / "metrics_table.csv",
    )
    plots = write_regression_plot_artifacts(preprocess["y_valid"], y_pred, stage_dir, prefix="validation")
    feature_importance_path, feature_importance_bar_path = write_feature_importance_plot_if_available(estimator, stage_dir)
    tables = {"validation_predictions": validation_predictions_path, "metrics_table": metrics_table_path}
    if feature_importance_path is not None:
        tables["feature_importance"] = feature_importance_path
    if feature_importance_bar_path is not None:
        plots["feature_importance"] = feature_importance_bar_path
        plots["feature_importance_bar"] = feature_importance_bar_path
    model_path = dump_joblib(estimator, stage_dir / "model.joblib")
    model_info_path = write_model_info(
        stage_dir / "model_info.json",
        feature_columns=preprocess["feature_columns"],
        target_column=preprocess["target_column"],
        feature_preset=preprocess["feature_preset"],
        model_name=model_name,
        model_params=model_params,
        artifact_kind="model",
        extra={"stage": stage_name, "feature_config": preprocess.get("feature_config", {})},
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
        "tables": tables,
        "plots": plots,
    }


def _model_ref_payload(item: dict[str, Any]) -> dict[str, Any]:
    tables = item.get("tables", {})
    payload = {
        "stage": item["stage"],
        "model_name": item["model_name"],
        "ensemble_method": item.get("ensemble_method"),
        "model_params": item["model_params"],
        "artifact_kind": item["artifact_kind"],
        "model": str(item["artifacts"]["model"]),
        "model_info": str(item["artifacts"]["model_info"]),
        "metrics": str(item["artifacts"]["metrics"]),
    }
    if tables.get("validation_predictions"):
        payload["validation_predictions"] = str(tables["validation_predictions"])
    if tables.get("ensemble_predictions"):
        payload["ensemble_predictions"] = str(tables["ensemble_predictions"])
    payload = {key: value for key, value in payload.items() if value is not None}
    return payload


def _metrics_by_model_payload(
    results: list[dict[str, Any]],
    selection_metric: str,
) -> dict[str, dict[str, Any]]:
    return {
        item["model_name"]: {
            "stage": item["stage"],
            "artifact_kind": item["artifact_kind"],
            "ensemble_method": item.get("ensemble_method"),
            "selection_metric": selection_metric,
            "selection_value": metric_value(item["metrics"], selection_metric),
            "metrics": item["metrics"],
        }
        for item in results
    }


def _train_model_candidates(
    cfg: dict[str, Any],
    preprocess: dict[str, Any],
    pipeline_dir: Path,
    metric_names: list[str] | str | None,
    selection_metric: str,
) -> dict[str, Any]:
    stage_dir = pipeline_dir / "model_candidates"
    stage_dir.mkdir(parents=True, exist_ok=True)

    model_cfg = cfg.get("model", {})
    candidates = model_candidates(model_cfg)
    if not candidates:
        raise ValueError("Training pipeline requires at least one model candidate.")

    model_results = [_train_model(cfg, preprocess, candidate, pipeline_dir, metric_names) for candidate in candidates]
    refs = [_model_ref_payload(item) for item in model_results]
    metrics_by_model = _metrics_by_model_payload(model_results, selection_metric)
    model_refs_path = write_json(
        {
            "stage": "model_candidates",
            "candidate_count": len(model_results),
            "selection_metric": selection_metric,
            "models": refs,
        },
        stage_dir / "model_refs.json",
    )
    metrics_by_model_path = write_json(
        {
            "stage": "model_candidates",
            "candidate_count": len(model_results),
            "selection_metric": selection_metric,
            "metrics_by_model": metrics_by_model,
        },
        stage_dir / "metrics_by_model.json",
    )
    return {
        "stage": "model_candidates",
        "stage_dir": stage_dir,
        "model_results": model_results,
        "model_refs": refs,
        "metrics_by_model": metrics_by_model,
        "artifacts": {
            "model_refs": model_refs_path,
            "metrics_by_model": metrics_by_model_path,
        },
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
    ensemble_results = []
    plots: dict[str, Path] = {}
    for method in ensemble_cfg["methods"]:
        weights = ensemble_weights(selected, method, selection_metric)
        if method == "median":
            estimator = MedianEnsemble([item["estimator"] for item in selected])
        else:
            estimator = MeanTopKEnsemble([item["estimator"] for item in selected], weights=weights)
        y_pred = estimator.predict(preprocess["X_valid"])
        metrics = regression_metrics(preprocess["y_valid"], y_pred, metrics=metric_names)
        model_name = method
        model_params = {
            "method": method,
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
                "weight": (weights[rank - 1] if method != "median" else None),
            }
            for rank, item in enumerate(selected, start=1)
        ]
        ensemble_members_path = write_table(
            pd.DataFrame(selected_base_models),
            stage_dir / f"ensemble_members_{method}.csv",
        )
        weights_frame = pd.DataFrame(
            [
                {
                    "rank": item["rank"],
                    "model_name": item["model_name"],
                    "ensemble_method": method,
                    "weight": item["weight"],
                    "uses_weighted_average": method != "median",
                }
                for item in selected_base_models
            ]
        )
        ensemble_weights_path = write_table(weights_frame, stage_dir / f"ensemble_weights_{method}.csv")
        if method != "median":
            weight_plot_path = write_metrics_bar_plot(
                [(item["model_name"], float(item["weight"])) for item in selected_base_models if item["weight"] is not None],
                stage_dir / f"ensemble_weights_{method}.png",
                title=f"Ensemble weights: {method}",
                value_label="weight",
            )
            plots[f"ensemble_weights_{method}"] = weight_plot_path

        predictions_frame = regression_prediction_frame(
            preprocess["X_valid"],
            preprocess["y_valid"],
            y_pred,
            model_name=model_name,
        )
        ensemble_predictions_path = write_table(predictions_frame, stage_dir / f"ensemble_predictions_{method}.csv")
        method_plots = write_regression_plot_artifacts(preprocess["y_valid"], y_pred, stage_dir, prefix=f"ensemble_{method}")
        plots.update({f"{plot_name}_ensemble_{method}": plot_path for plot_name, plot_path in method_plots.items()})
        model_path = dump_joblib(estimator, stage_dir / f"model_{method}.joblib")
        model_info_path = write_model_info(
            stage_dir / f"model_info_{method}.json",
            feature_columns=preprocess["feature_columns"],
            target_column=preprocess["target_column"],
            feature_preset=preprocess["feature_preset"],
            model_name=model_name,
            model_params=model_params,
            artifact_kind="ensemble",
            extra={
                "stage": "build_ensemble",
                "feature_config": preprocess.get("feature_config", {}),
                "ensemble_method": method,
                "top_k": len(selected),
                "selection_metric": selection_metric,
                "selected_base_models": selected_base_models,
                "weights": ([] if method == "median" else weights),
            },
        )
        ensemble_info_payload = {
            "enabled": True,
            "method": method,
            "top_k": len(selected),
            "selection_metric": selection_metric,
            "produced_model_name": model_name,
            "selected_base_models": selected_base_models,
            "weights": ([] if method == "median" else weights),
            "aggregation": "median" if method == "median" else "weighted_average",
            "model_artifact": str(model_path),
        }
        ensemble_info_path = write_json(ensemble_info_payload, stage_dir / f"ensemble_info_{method}.json")
        metrics_path = write_json(metrics, stage_dir / f"metrics_{method}.json")
        ensemble_results.append(
            {
                "stage": "build_ensemble",
                "stage_dir": stage_dir,
                "model_name": model_name,
                "ensemble_method": method,
                "model_params": model_params,
                "artifact_kind": "ensemble",
                "artifact_name": f"model_{method}",
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
                "tables": {
                    "ensemble_predictions": ensemble_predictions_path,
                    "ensemble_members": ensemble_members_path,
                    "ensemble_weights": ensemble_weights_path,
                },
                "plots": method_plots,
            }
        )

    ranked_ensembles = _ranked_results(ensemble_results, selection_metric)
    ensemble_metrics_rows = []
    for item in ranked_ensembles:
        row = {
            "ensemble_method": item["ensemble_method"],
            "model_name": item["model_name"],
            "selection_metric": selection_metric,
            "selection_value": metric_value(item["metrics"], selection_metric),
        }
        for metric_name, metric in item["metrics"].items():
            row[metric_name] = metric
        ensemble_metrics_rows.append(row)
    ensemble_metrics_table_path = write_table(pd.DataFrame(ensemble_metrics_rows), stage_dir / "ensemble_metrics_table.csv")
    ensemble_metrics_bar_path = write_metrics_bar_plot(
        [(row["ensemble_method"], row.get(selection_metric, row["selection_value"])) for row in ensemble_metrics_rows],
        stage_dir / "ensemble_metrics_bar.png",
        title=f"Ensemble metrics ({selection_metric})",
        value_label=selection_metric,
    )
    plots["ensemble_metrics_bar"] = ensemble_metrics_bar_path
    best_ensemble = ranked_ensembles[0]
    shutil.copy2(best_ensemble["artifacts"]["model"], stage_dir / "model.joblib")
    shutil.copy2(best_ensemble["artifacts"]["model_info"], stage_dir / "model_info.json")
    shutil.copy2(best_ensemble["artifacts"]["ensemble_info"], stage_dir / "ensemble_info.json")
    shutil.copy2(best_ensemble["artifacts"]["metrics"], stage_dir / "metrics.json")
    shutil.copy2(best_ensemble["tables"]["ensemble_predictions"], stage_dir / "ensemble_predictions.csv")

    refs = [_model_ref_payload(item) for item in ensemble_results]
    ensemble_refs_path = write_json(
        {
            "stage": "build_ensemble",
            "selection_metric": selection_metric,
            "methods": ensemble_cfg["methods"],
            "ensembles": refs,
            "best_ensemble": _model_ref_payload(best_ensemble),
        },
        stage_dir / "ensemble_refs.json",
    )
    info_by_method = {}
    for item in ensemble_results:
        info_by_method[item["ensemble_method"]] = json.loads(
            Path(item["artifacts"]["ensemble_info"]).read_text(encoding="utf-8")
        )
    ensemble_info_by_method_path = write_json(
        {
            "stage": "build_ensemble",
            "selection_metric": selection_metric,
            "methods": ensemble_cfg["methods"],
            "best_ensemble_method": best_ensemble["ensemble_method"],
            "ensemble_info_by_method": info_by_method,
        },
        stage_dir / "ensemble_info_by_method.json",
    )
    artifacts: dict[str, Path] = {
        "model": stage_dir / "model.joblib",
        "model_info": stage_dir / "model_info.json",
        "ensemble_info": stage_dir / "ensemble_info.json",
        "metrics": stage_dir / "metrics.json",
        "ensemble_refs": ensemble_refs_path,
        "ensemble_info_by_method": ensemble_info_by_method_path,
    }
    tables: dict[str, Path] = {
        "ensemble_predictions": stage_dir / "ensemble_predictions.csv",
        "ensemble_metrics_table": ensemble_metrics_table_path,
    }
    for item in ensemble_results:
        method = item["ensemble_method"]
        artifacts[f"model_{method}"] = item["artifacts"]["model"]
        artifacts[f"model_info_{method}"] = item["artifacts"]["model_info"]
        artifacts[f"ensemble_info_{method}"] = item["artifacts"]["ensemble_info"]
        artifacts[f"metrics_{method}"] = item["artifacts"]["metrics"]
        tables[f"ensemble_predictions_{method}"] = item["tables"]["ensemble_predictions"]
        tables[f"ensemble_members_{method}"] = item["tables"]["ensemble_members"]
        tables[f"ensemble_weights_{method}"] = item["tables"]["ensemble_weights"]
    return {
        "stage": "build_ensemble",
        "stage_dir": stage_dir,
        "model_name": best_ensemble["model_name"],
        "ensemble_method": best_ensemble["ensemble_method"],
        "model_params": best_ensemble["model_params"],
        "artifact_kind": "ensemble",
        "estimator": best_ensemble["estimator"],
        "predictions": best_ensemble["predictions"],
        "metrics": best_ensemble["metrics"],
        "selected_base_models": best_ensemble.get("selected_base_models", []),
        "ensemble_results": ensemble_results,
        "best_ensemble": best_ensemble,
        "ensemble_refs": refs,
        "artifacts": artifacts,
        "tables": tables,
        "plots": plots,
    }


def _leaderboard_rows(results: list[dict[str, Any]], selection_metric: str) -> list[dict[str, Any]]:
    rows = []
    for rank, item in enumerate(results, start=1):
        artifact_kind = item["artifact_kind"]
        ensemble_method = item.get("ensemble_method")
        infer_target = f"ensemble:{ensemble_method}" if artifact_kind == "ensemble" and ensemble_method else item["model_name"]
        row = {
            "rank": rank,
            "model_name": item["model_name"],
            "artifact_kind": artifact_kind,
            "ensemble_method": ensemble_method,
            "stage": item["stage"],
            "selection_metric": selection_metric,
            "ref_kind": "task_artifact",
            "infer_selector": "Model/model_selector",
            "infer_target": infer_target,
            "model_params": json.dumps(item["model_params"], sort_keys=True, default=str),
            "artifact_name": item.get("artifact_name", "model"),
            "artifact_path": str(item["artifacts"]["model"]),
        }
        for name in LEADERBOARD_METRICS:
            row[name] = item["metrics"].get(name)
        rows.append(row)
    return rows


def _prediction_table_path(item: dict[str, Any]) -> Path | None:
    tables = item.get("tables", {})
    path = tables.get("validation_predictions") or tables.get("ensemble_predictions")
    return Path(path) if path else None


def _write_evaluation_predictions(best: dict[str, Any], stage_dir: Path) -> tuple[Path | None, dict[str, Path]]:
    source = _prediction_table_path(best)
    if source is None or not source.exists():
        return None, {}
    destination = stage_dir / "evaluation_predictions.csv"
    if source != destination:
        shutil.copy2(source, destination)
    frame = pd.read_csv(destination)
    if {"actual", "prediction"} <= set(frame.columns):
        scatter = write_prediction_vs_actual_plot(
            frame["actual"],
            frame["prediction"],
            stage_dir / "best_prediction_vs_actual.png",
            title="Best prediction vs actual",
        )
        residual = write_residual_histogram(
            frame["actual"],
            frame["prediction"],
            stage_dir / "best_residual_histogram.png",
            title="Best residual histogram",
        )
        residual_vs_predicted = write_residual_vs_predicted_plot(
            frame["actual"],
            frame["prediction"],
            stage_dir / "best_residual_vs_predicted.png",
            title="Best residuals vs predicted",
        )
        plots = {
            "best_prediction_vs_actual": scatter,
            "best_residual_histogram": residual,
            "best_residual_vs_predicted": residual_vs_predicted,
        }
    else:
        plots = {}
    return destination, plots


def _write_candidate_predictions(candidates: list[dict[str, Any]], stage_dir: Path) -> tuple[Path | None, dict[str, Path]]:
    frames = []
    for rank, item in enumerate(candidates, start=1):
        source = _prediction_table_path(item)
        if source is None or not source.exists():
            continue
        frame = pd.read_csv(source)
        if not {"actual", "prediction"} <= set(frame.columns):
            continue
        candidate_name = str(item["model_name"])
        frame = frame.copy()
        frame.insert(0, "candidate_rank", rank)
        frame.insert(1, "candidate_name", candidate_name)
        frame.insert(2, "artifact_kind", item["artifact_kind"])
        frame.insert(3, "ensemble_method", item.get("ensemble_method"))
        frame.insert(4, "source_stage", item["stage"])
        if "residual" not in frame.columns:
            frame["residual"] = pd.to_numeric(frame["actual"], errors="coerce") - pd.to_numeric(
                frame["prediction"], errors="coerce"
            )
        if "abs_error" not in frame.columns:
            frame["abs_error"] = frame["residual"].abs()
        frames.append(frame)
    if not frames:
        return None, {}
    combined = pd.concat(frames, ignore_index=True)
    predictions_path = write_table(combined, stage_dir / "candidate_predictions.csv")
    topk = topk_candidate_predictions(combined, top_k=LEADERBOARD_TOP_K)
    plots = {
        "topk_prediction_vs_actual": write_candidate_prediction_vs_actual_plot(
            topk,
            stage_dir / "topk_prediction_vs_actual.png",
            title=f"Top-{LEADERBOARD_TOP_K} prediction vs actual",
        ),
        "topk_residual_histogram": write_candidate_residual_histogram(
            topk,
            stage_dir / "topk_residual_histogram.png",
            title=f"Top-{LEADERBOARD_TOP_K} residual histogram",
        ),
        "topk_residual_vs_predicted": write_candidate_residual_vs_predicted_plot(
            topk,
            stage_dir / "topk_residual_vs_predicted.png",
            title=f"Top-{LEADERBOARD_TOP_K} residuals vs predicted",
        ),
    }
    return predictions_path, plots


def _selector_for_item(item: dict[str, Any]) -> str:
    if item["artifact_kind"] == "ensemble" and item.get("ensemble_method"):
        return f"ensemble:{item['ensemble_method']}"
    return str(item["model_name"])


def _summary_row(summary: str, item: dict[str, Any] | None, selection_metric: str) -> dict[str, Any]:
    if item is None:
        return {
            "summary": summary,
            "model_name": None,
            "artifact_kind": None,
            "ensemble_method": None,
            "selection_metric": selection_metric,
            "selection_value": None,
            "rmse": None,
            "mae": None,
            "r2": None,
            "model_selector": None,
            "infer_target": None,
        }
    return {
        "summary": summary,
        "model_name": item["model_name"],
        "artifact_kind": item["artifact_kind"],
        "ensemble_method": item.get("ensemble_method"),
        "selection_metric": selection_metric,
        "selection_value": metric_value(item["metrics"], selection_metric),
        "rmse": item["metrics"].get("rmse"),
        "mae": item["metrics"].get("mae"),
        "r2": item["metrics"].get("r2"),
        "model_selector": _selector_for_item(item),
        "infer_target": _selector_for_item(item),
    }


def _best_vs_ensemble_rows(
    best_single: dict[str, Any] | None,
    best_ensemble: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    def _optional_metric(item: dict[str, Any] | None, metric_name: str) -> float | None:
        if item is None:
            return None
        value = item.get("metrics", {}).get(metric_name)
        return float(value) if isinstance(value, (int, float)) else None

    rows: list[dict[str, Any]] = []
    for metric_name in LEADERBOARD_METRICS:
        single_value = _optional_metric(best_single, metric_name)
        ensemble_value = _optional_metric(best_ensemble, metric_name)
        delta = None
        improved = None
        if single_value is not None and ensemble_value is not None:
            delta = ensemble_value - single_value
            improved = delta > 0 if metric_name == "r2" else delta < 0
        rows.append(
            {
                "metric": metric_name,
                "best_single_model": best_single.get("model_name") if best_single else None,
                "best_single_value": single_value,
                "best_ensemble_method": best_ensemble.get("ensemble_method") if best_ensemble else None,
                "best_ensemble_value": ensemble_value,
                "ensemble_minus_single": delta,
                "ensemble_improved": improved,
            }
        )
    return rows


def _recommendation_payload(
    *,
    best: dict[str, Any],
    best_single: dict[str, Any] | None,
    best_ensemble: dict[str, Any] | None,
    selection_metric: str,
    leaderboard_rows: list[dict[str, Any]],
    task_id: str | None,
) -> dict[str, Any]:
    selector = _selector_for_item(best)
    recommended = _summary_row("recommended", best, selection_metric)
    return {
        "report_schema_version": LEADERBOARD_REPORT_SCHEMA_VERSION,
        "created_at": utc_timestamp(),
        "code_version": _code_version(),
        "source_task_id": task_id,
        "source_task_hint": "Use this evaluate_models ClearML task id as Input/source_task_id when source_task_id is null.",
        "recommended_ref_kind": "clearml_task_artifact",
        "recommended_infer_key": "Input/source_task_id + Model/model_selector",
        "recommended_infer_value": selector,
        "recommended_assignment": {
            "Input/source_task_id": task_id or "<this evaluate_models task id>",
            "Model/model_selector": selector,
        },
        "recommended": recommended,
        "best_overall": _summary_row("best_overall", best, selection_metric),
        "best_single_model": _summary_row("best_single_model", best_single, selection_metric),
        "best_ensemble": _summary_row("best_ensemble", best_ensemble, selection_metric),
        "top_candidates": leaderboard_rows[:LEADERBOARD_TOP_K],
    }


def _decision_summary_markdown(recommendation: dict[str, Any], leaderboard_rows: list[dict[str, Any]]) -> str:
    assignment = recommendation.get("recommended_assignment") or {}
    top_rows = leaderboard_rows[:LEADERBOARD_TOP_K]
    lines = [
        "# Leaderboard Decision Summary",
        "",
        "## Infer Run Input",
        f"- Input/source_task_id: {assignment.get('Input/source_task_id')}",
        f"- Model/model_selector: {assignment.get('Model/model_selector')}",
        f"- ref_kind: {recommendation.get('recommended_ref_kind')}",
        f"- report_schema_version: {recommendation.get('report_schema_version')}",
        f"- code_version: {recommendation.get('code_version')}",
        "",
        "## Recommendation",
    ]
    recommended = recommendation.get("recommended") or {}
    lines.extend(
        [
            f"- model_name: {recommended.get('model_name')}",
            f"- artifact_kind: {recommended.get('artifact_kind')}",
            f"- ensemble_method: {recommended.get('ensemble_method')}",
            f"- selection_metric: {recommended.get('selection_metric')}",
            f"- selection_value: {recommended.get('selection_value')}",
            "",
            "## Top Candidates",
            "| rank | model_name | artifact_kind | ensemble_method | rmse | mae | r2 | model_selector |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in top_rows:
        lines.append(
            "| {rank} | {model_name} | {artifact_kind} | {ensemble_method} | {rmse} | {mae} | {r2} | {infer_target} |".format(
                rank=row.get("rank"),
                model_name=row.get("model_name"),
                artifact_kind=row.get("artifact_kind"),
                ensemble_method=row.get("ensemble_method") or "",
                rmse=row.get("rmse"),
                mae=row.get("mae"),
                r2=row.get("r2"),
                infer_target=row.get("infer_target"),
            )
        )
    return "\n".join(lines) + "\n"


def _evaluate_models(
    cfg: dict[str, Any],
    model_results: list[dict[str, Any]],
    ensemble_results: list[dict[str, Any]] | dict[str, Any] | None,
    pipeline_dir: Path,
    selection_metric: str,
) -> dict[str, Any]:
    stage_dir = pipeline_dir / "evaluate_models"
    stage_dir.mkdir(parents=True, exist_ok=True)
    if ensemble_results is None:
        ensemble_items: list[dict[str, Any]] = []
    elif isinstance(ensemble_results, dict) and "ensemble_results" in ensemble_results:
        ensemble_items = list(ensemble_results.get("ensemble_results") or [])
    elif isinstance(ensemble_results, dict):
        ensemble_items = [ensemble_results]
    else:
        ensemble_items = list(ensemble_results)
    candidates = [*model_results]
    candidates.extend(ensemble_items)
    ranked = _ranked_results(candidates, selection_metric)
    best = ranked[0]
    ranked_models = _ranked_results(model_results, selection_metric) if model_results else []
    best_single = ranked_models[0] if ranked_models else None
    ranked_ensembles = _ranked_results(ensemble_items, selection_metric) if ensemble_items else []
    best_ensemble = ranked_ensembles[0] if ranked_ensembles else None
    metrics_by_model = _metrics_by_model_payload(ranked, selection_metric)
    task_id = cfg.get("runtime", {}).get("clearml_task_id") or _runtime_task_id()
    code_version = _code_version()

    leaderboard_rows = _leaderboard_rows(ranked, selection_metric)
    leaderboard_path = write_leaderboard_table(leaderboard_rows, stage_dir / "leaderboard.csv")
    leaderboard_topk_path = write_leaderboard_table(
        leaderboard_rows[:LEADERBOARD_TOP_K],
        stage_dir / "leaderboard_topk.csv",
    )
    evaluation_predictions_path, plots = _write_evaluation_predictions(best, stage_dir)
    candidate_predictions_path, candidate_plots = _write_candidate_predictions(ranked, stage_dir)
    plots.update(candidate_plots)
    model_refs_payload = {
        "stage": "evaluate_models",
        "candidate_count": len(model_results),
        "ensemble_enabled": bool(ensemble_items),
        "ensemble_count": len(ensemble_items),
        "selection_metric": selection_metric,
        "models": [_model_ref_payload(item) for item in model_results],
        "ensembles": [_model_ref_payload(item) for item in ensemble_items],
        "ensemble": _model_ref_payload(best_ensemble) if best_ensemble is not None else None,
    }
    model_refs_path = write_json(model_refs_payload, stage_dir / "model_refs.json")
    metrics_payload = {
        "stage": "evaluate_models",
        "candidate_count": len(model_results),
        "ensemble_enabled": bool(ensemble_items),
        "ensemble_count": len(ensemble_items),
        "selection_metric": selection_metric,
        "metrics_by_model": metrics_by_model,
        "metrics_by_candidate": metrics_by_model,
    }
    metrics_by_model_path = write_json(metrics_payload, stage_dir / "metrics_by_model.json")
    metrics_by_candidate_path = write_json(metrics_payload, stage_dir / "metrics_by_candidate.json")
    metrics_by_candidate_table_path = write_metrics_by_candidate_table(
        metrics_by_model,
        stage_dir / "metrics_by_candidate.csv",
    )
    bar_items = []
    for candidate_name, payload in metrics_by_model.items():
        metrics = payload.get("metrics", {})
        if isinstance(metrics, dict) and isinstance(metrics.get(selection_metric), (int, float)):
            bar_items.append((candidate_name, float(metrics[selection_metric])))
    metrics_by_model_bar_path = write_metrics_bar_plot(
        bar_items,
        stage_dir / "metrics_by_model_bar.png",
        title=f"Metrics by candidate ({selection_metric})",
        value_label=selection_metric,
        sort="value_desc" if selection_metric == "r2" else "value_asc",
    )
    metrics_by_candidate_bar_path = write_metrics_bar_plot(
        bar_items,
        stage_dir / "metrics_by_candidate_bar.png",
        title=f"Metrics by candidate ({selection_metric})",
        value_label=selection_metric,
        sort="value_desc" if selection_metric == "r2" else "value_asc",
    )
    leaderboard_topk_score_bar_path = write_metrics_bar_plot(
        [(row["model_name"], row.get(selection_metric)) for row in leaderboard_rows],
        stage_dir / "leaderboard_topk_score_bar.png",
        title=f"Leaderboard top-{LEADERBOARD_TOP_K} ({selection_metric})",
        value_label=selection_metric,
        top_n=LEADERBOARD_TOP_K,
        sort="input",
    )
    leaderboard_metric_panel_path = write_leaderboard_metric_panel(
        leaderboard_rows,
        stage_dir / "leaderboard_metric_panel.png",
        top_k=LEADERBOARD_TOP_K,
    )
    leaderboard_pareto_path = write_leaderboard_pareto_plot(
        leaderboard_rows,
        stage_dir / "leaderboard_pareto_rmse_r2.png",
        top_k=max(LEADERBOARD_TOP_K, 10),
    )
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
        "ensemble_method": best.get("ensemble_method"),
        "source_artifact": str(best["artifacts"]["model"]),
        "best_model_artifact": str(best_model_path),
    }
    best_ensemble_payload = None
    if best_ensemble is not None:
        best_ensemble_payload = {
            "model_name": best_ensemble["model_name"],
            "artifact_kind": best_ensemble["artifact_kind"],
            "ensemble_method": best_ensemble.get("ensemble_method"),
            "stage": best_ensemble["stage"],
            "selection_metric": selection_metric,
            "selection_value": metric_value(best_ensemble["metrics"], selection_metric),
            "metrics": best_ensemble["metrics"],
            "model_params": best_ensemble["model_params"],
            "source_artifact": str(best_ensemble["artifacts"]["model"]),
        }
    best_model_json_path = write_json(best_payload, stage_dir / "best_model.json")
    summary_rows = [
        _summary_row("best_overall", best, selection_metric),
        _summary_row("best_single_model", best_single, selection_metric),
        _summary_row("best_ensemble", best_ensemble, selection_metric),
    ]
    evaluation_summary_path = write_table(pd.DataFrame(summary_rows), stage_dir / "evaluation_summary.csv")
    leaderboard_decision_summary_path = write_table(
        pd.DataFrame(summary_rows),
        stage_dir / "leaderboard_decision_summary.csv",
    )
    best_vs_ensemble_summary_path = write_table(
        pd.DataFrame(_best_vs_ensemble_rows(best_single, best_ensemble)),
        stage_dir / "best_vs_ensemble_summary.csv",
    )
    recommendation = _recommendation_payload(
        best=best,
        best_single=best_single,
        best_ensemble=best_ensemble,
        selection_metric=selection_metric,
        leaderboard_rows=leaderboard_rows,
        task_id=task_id,
    )
    recommendation_path = write_json(recommendation, stage_dir / "recommendation.json")
    decision_summary_md_path = stage_dir / "decision_summary.md"
    decision_summary_md_path.write_text(_decision_summary_markdown(recommendation, leaderboard_rows), encoding="utf-8")
    decision_summary_json_path = write_json(
        {
            "report_schema_version": LEADERBOARD_REPORT_SCHEMA_VERSION,
            "created_at": recommendation["created_at"],
            "code_version": code_version,
            "recommendation": recommendation,
            "leaderboard_topk": leaderboard_rows[:LEADERBOARD_TOP_K],
            "best_vs_ensemble_summary": _best_vs_ensemble_rows(best_single, best_ensemble),
        },
        stage_dir / "decision_summary.json",
    )
    report = {
        "report_schema_version": LEADERBOARD_REPORT_SCHEMA_VERSION,
        "created_at": recommendation["created_at"],
        "code_version": code_version,
        "source_task_id": task_id,
        "stage": "evaluate_models",
        "candidate_count": len(model_results),
        "ensemble_enabled": bool(ensemble_items),
        "ensemble_count": len(ensemble_items),
        "selection_metric": selection_metric,
        "best_model": best_payload,
        "best_single_model": _summary_row("best_single_model", best_single, selection_metric),
        "best_ensemble": best_ensemble_payload,
        "ranked_models": leaderboard_rows,
        "ensemble_metrics": {
            item["model_name"]: {
                "ensemble_method": item.get("ensemble_method"),
                "metrics": item["metrics"],
                "selection_value": metric_value(item["metrics"], selection_metric),
            }
            for item in ranked_ensembles
        },
        "model_refs": model_refs_payload,
        "metrics_by_model": metrics_by_model,
        "metrics_by_candidate": metrics_by_model,
        "evaluation_predictions": str(evaluation_predictions_path) if evaluation_predictions_path else None,
        "leaderboard_topk": str(leaderboard_topk_path),
        "leaderboard_decision_summary": str(leaderboard_decision_summary_path),
        "best_vs_ensemble_summary": str(best_vs_ensemble_summary_path),
        "recommendation": str(recommendation_path),
        "decision_summary": str(decision_summary_md_path),
        "decision_summary_json": str(decision_summary_json_path),
    }
    evaluation_report_path = write_json(report, stage_dir / "evaluation_report.json")
    metrics_payload = {
        **best["metrics"],
        "report_schema_version": LEADERBOARD_REPORT_SCHEMA_VERSION,
        "best_model": best_payload,
        "best_ensemble": best_ensemble_payload,
        "selection_metric": selection_metric,
        "candidate_count": len(model_results),
        "ensemble_enabled": bool(ensemble_items),
        "ensemble_count": len(ensemble_items),
    }
    metrics_path = write_json(metrics_payload, stage_dir / "metrics.json")
    artifacts = {
        "model_refs": model_refs_path,
        "metrics_by_model": metrics_by_model_path,
        "metrics_by_candidate": metrics_by_candidate_path,
        "best_model": best_model_path,
        "best_model_json": best_model_json_path,
        "evaluation_report": evaluation_report_path,
        "recommendation": recommendation_path,
        "decision_summary": decision_summary_md_path,
        "decision_summary_json": decision_summary_json_path,
        "metrics": metrics_path,
    }
    if evaluation_predictions_path is not None:
        artifacts["evaluation_predictions"] = evaluation_predictions_path
    if candidate_predictions_path is not None:
        artifacts["candidate_predictions"] = candidate_predictions_path
    return {
        "stage": "evaluate_models",
        "stage_dir": stage_dir,
        "best": best,
        "metrics": metrics_payload,
        "report": report,
        "artifacts": artifacts,
        "tables": {
            "leaderboard": leaderboard_path,
            "leaderboard_topk": leaderboard_topk_path,
            "metrics_by_candidate": metrics_by_candidate_table_path,
            "evaluation_summary": evaluation_summary_path,
            "leaderboard_decision_summary": leaderboard_decision_summary_path,
            "best_vs_ensemble_summary": best_vs_ensemble_summary_path,
            **({"evaluation_predictions": evaluation_predictions_path} if evaluation_predictions_path else {}),
            **({"candidate_predictions": candidate_predictions_path} if candidate_predictions_path else {}),
        },
        "plots": {
            "metrics_by_model_bar": metrics_by_model_bar_path,
            "metrics_by_candidate_bar": metrics_by_candidate_bar_path,
            "leaderboard_topk_score_bar": leaderboard_topk_score_bar_path,
            "leaderboard_metric_panel": leaderboard_metric_panel_path,
            "leaderboard_pareto_rmse_r2": leaderboard_pareto_path,
            **plots,
        },
    }


def _run_training_pipeline(cfg: dict[str, Any]) -> RunResult:
    model_cfg = cfg.get("model", {})
    search_cfg = model_cfg.get("search") or {}
    if isinstance(search_cfg, dict) and as_bool(search_cfg.get("enabled")):
        raise ValueError(
            "model.search.enabled=true is future/experimental and is not part of the "
            "primary local training pipeline. Remove model.search or set enabled=false for "
            "preprocess_features -> train_<model>* -> build_ensemble -> evaluate_models."
        )

    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    run_name = cfg.get("run", {}).get("name", "tabular_training_pipeline")
    pipeline_dir = prepare_run_dir(output_dir, run_name)
    selection_metric = _metric_name(model_cfg.get("selection_metric") or "rmse")
    if selection_metric not in SELECTION_METRICS:
        raise ValueError("model.selection_metric must be one of: mae, rmse, r2.")
    metric_names = _metric_names(cfg.get("metrics", {}).get("names"), selection_metric)

    preprocess = _preprocess_features(cfg, pipeline_dir)
    trained = _train_model_candidates(cfg, preprocess, pipeline_dir, metric_names, selection_metric)
    model_results = trained["model_results"]
    ranked_models = _ranked_results(model_results, selection_metric)
    ensemble_result = _build_ensemble(cfg, preprocess, ranked_models, pipeline_dir, metric_names, selection_metric)
    evaluation = _evaluate_models(cfg, model_results, ensemble_result, pipeline_dir, selection_metric)
    ensemble_results = list((ensemble_result or {}).get("ensemble_results", [])) if ensemble_result else []

    artifacts: dict[str, Path] = {
        **preprocess["artifacts"],
        **trained["artifacts"],
        "leaderboard": evaluation["tables"]["leaderboard"],
        **evaluation["artifacts"],
    }
    tables: dict[str, Path] = {
        **preprocess["tables"],
        **evaluation["tables"],
    }
    plots: dict[str, Path] = dict(evaluation.get("plots", {}))
    for plot_name, plot_path in preprocess.get("plots", {}).items():
        plots[plot_name] = plot_path
    for item in model_results:
        key = _safe_name(item["model_name"])
        artifacts[f"model_{key}"] = item["artifacts"]["model"]
        artifacts[f"model_info_{key}"] = item["artifacts"]["model_info"]
        artifacts[f"metrics_{key}"] = item["artifacts"]["metrics"]
        tables[f"metrics_table_{key}"] = item["tables"]["metrics_table"]
        tables[f"validation_predictions_{key}"] = item["tables"]["validation_predictions"]
        if item.get("tables", {}).get("feature_importance"):
            tables[f"feature_importance_{key}"] = item["tables"]["feature_importance"]
        for plot_name, plot_path in item.get("plots", {}).items():
            plots[f"{plot_name}_{key}"] = plot_path
    if ensemble_result is not None:
        artifacts["ensemble"] = ensemble_result["artifacts"]["model"]
        artifacts["ensemble_info"] = ensemble_result["artifacts"]["ensemble_info"]
        artifacts["ensemble_model_info"] = ensemble_result["artifacts"]["model_info"]
        artifacts["ensemble_refs"] = ensemble_result["artifacts"]["ensemble_refs"]
        artifacts["ensemble_info_by_method"] = ensemble_result["artifacts"]["ensemble_info_by_method"]
        for table_name, table_path in ensemble_result.get("tables", {}).items():
            tables[table_name] = table_path
        for item in ensemble_results:
            method = item["ensemble_method"]
            artifacts[f"ensemble_{method}"] = item["artifacts"]["model"]
            artifacts[f"ensemble_model_info_{method}"] = item["artifacts"]["model_info"]
            artifacts[f"ensemble_info_{method}"] = item["artifacts"]["ensemble_info"]
            artifacts[f"ensemble_metrics_{method}"] = item["artifacts"]["metrics"]
        for plot_name, plot_path in ensemble_result.get("plots", {}).items():
            plots[plot_name] = plot_path

    summary = {
        "pipeline_kind": "training",
        "report_schema_version": LEADERBOARD_REPORT_SCHEMA_VERSION,
        "code_version": evaluation["report"].get("code_version"),
        "stages": [
            "preprocess_features",
            *[item["stage"] for item in model_results],
            *(["build_ensemble"] if ensemble_result is not None else []),
            "evaluate_models",
        ],
        "candidate_models": [item["model_name"] for item in model_results],
        "selection_metric": selection_metric,
        "model_refs": trained["model_refs"],
        "metrics_by_model": trained["metrics_by_model"],
        "metrics_by_candidate": evaluation["report"]["metrics_by_candidate"],
        "best_model": evaluation["report"]["best_model"],
        "ensemble": (
            {
                "enabled": True,
                "model_name": ensemble_result["model_name"],
                "ensemble_method": ensemble_result.get("ensemble_method"),
                "artifact": str(ensemble_result["artifacts"]["model"]),
                "selected_base_models": ensemble_result.get("selected_base_models", []),
                "methods": [item["ensemble_method"] for item in ensemble_results],
                "best_ensemble": evaluation["report"].get("best_ensemble"),
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
        plots=plots,
        extra=summary,
    )
    artifacts["manifest"] = manifest_path
    update_latest(pipeline_dir, output_dir / "latest_training_pipeline")
    update_latest(pipeline_dir, output_dir / "latest")

    return RunResult(run_dir=pipeline_dir, metrics=evaluation["metrics"], artifacts=artifacts, tables=tables, plots=plots, extra=summary)


def run_pipeline(cfg: dict[str, Any]) -> RunResult:
    if "data" not in cfg:
        raise ValueError(
            "tabular_pipeline now runs only the official training graph: "
            "preprocess_features -> train_<model>* -> build_ensemble -> evaluate_models. "
            "The old train/eval/infer full-run flow is not a product pipeline entrypoint."
        )
    return _run_training_pipeline(cfg)
