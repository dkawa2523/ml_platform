from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


PREDICTION_SCHEMA_VERSION = "v2.3"
RESERVED_PREDICTION_COLUMNS = {
    "row_index",
    "prediction",
    "model_name",
    "artifact_kind",
    "model_artifact_id",
    "prediction_run_id",
}


def _model_artifact_id(model_info: dict[str, Any], model_path: Path) -> str:
    if model_info:
        payload = {
            "artifact_kind": model_info.get("artifact_kind"),
            "model_name": model_info.get("model_name") or model_info.get("best_model_name"),
            "model_params": model_info.get("model_params") or model_info.get("best_model_params"),
            "produced_model_name": model_info.get("produced_model_name"),
            "ensemble_method": model_info.get("ensemble_method"),
            "selected_base_models": model_info.get("selected_base_models"),
        }
    else:
        payload = {"model_path": str(model_path)}
    text = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _prediction_frame(
    df,
    y_pred,
    *,
    id_columns: list[str],
    model_info: dict[str, Any],
    run_id: str,
    model_artifact_id: str,
):
    conflicts = [column for column in RESERVED_PREDICTION_COLUMNS if column in df.columns]
    if conflicts:
        raise ValueError(f"Input table contains reserved prediction output columns: {conflicts}")
    model_name = str(model_info.get("model_name") or model_info.get("best_model_name") or "unknown")
    artifact_kind = str(model_info.get("artifact_kind") or "model")
    out = pd.DataFrame({"row_index": df.index.to_list()})
    for column in id_columns:
        if column in df.columns and column not in out.columns:
            out[column] = df[column].to_list()
    out["prediction"] = y_pred
    out["model_name"] = model_name
    out["artifact_kind"] = artifact_kind
    out["model_artifact_id"] = model_artifact_id
    out["prediction_run_id"] = str(run_id)
    return out
