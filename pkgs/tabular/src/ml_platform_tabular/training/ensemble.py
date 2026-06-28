from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from ml_platform_core.io import dump_joblib, write_json, write_table

from ..ensemble import as_bool, ensemble_config, ensemble_weights, metric_value
from ..metrics import regression_metrics, regression_prediction_frame
from ..model_artifact import write_model_info
from ..models import MeanTopKEnsemble, MedianEnsemble
from ..plotting import (
    write_metrics_bar_plot,
    write_regression_plot_artifacts,
)
from .artifacts import _model_ref_payload
from .ranking import _ranked_results


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
                [
                    (item["model_name"], float(item["weight"]))
                    for item in selected_base_models
                    if item["weight"] is not None
                ],
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
        method_plots = write_regression_plot_artifacts(
            preprocess["y_valid"], y_pred, stage_dir, prefix=f"ensemble_{method}"
        )
        plots.update(method_plots)
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
    ensemble_metrics_table_path = write_table(
        pd.DataFrame(ensemble_metrics_rows), stage_dir / "ensemble_metrics_table.csv"
    )
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


__all__ = ["_build_ensemble", "as_bool"]
