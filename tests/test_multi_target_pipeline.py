import json

import numpy as np
import pandas as pd
from ml_platform_core.config import load_run_config
from ml_platform_core.io import load_joblib, read_json
from ml_platform_tabular.inference import run_infer
from ml_platform_tabular.stage_inputs import load_preprocess
from ml_platform_tabular.target_model_bundle import TargetModelBundle
from ml_platform_tabular.target_sources import TARGET_COLUMN
from ml_platform_tabular.training import run_pipeline


def _manifest(*targets):
    return {
        "schema_version": 1,
        "defaults": {"columns": {"x": "x", "time": "t", "value": "f"}},
        "targets": list(targets),
    }


def _write_collection(root):
    root.mkdir()
    temperature = pd.DataFrame({"x": range(30), "t": range(30)})
    temperature["temperature"] = 2.0 * temperature["x"] + 0.5
    temperature.to_csv(root / "temperature.csv", index=False)

    pressure = pd.DataFrame({"X": range(5, 35), "timestamp": range(5, 35)})
    pressure["pressure"] = -3.0 * pressure["X"] + 100.0
    pressure.to_csv(root / "pressure.csv", index=False)

    manifest = _manifest(
        {"name": "temperature", "file": "temperature.csv", "columns": {"value": "temperature"}},
        {
            "name": "pressure",
            "file": "pressure.csv",
            "columns": {"x": "X", "time": "timestamp", "value": "pressure"},
        },
    )
    (root / "target_sources.json").write_text(json.dumps(manifest), encoding="utf-8")


def _training_config(tmp_path, root):
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"].update(
        {
            "local_path": str(root),
            "dataset_file": None,
            "source_manifest": "target_sources.json",
            "target_column": None,
            "feature_columns": None,
            "id_columns": [],
        }
    )
    cfg["model"]["candidates"] = ["linear", "ridge"]
    cfg["model"]["selection_metric"] = "skill"
    cfg["model"]["ensemble"].update({"enabled": True, "methods": ["mean_topk"], "top_k": 2})
    return cfg


def test_sparse_target_collection_runs_through_training_stage_and_inference(tmp_path):
    train_root = tmp_path / "train"
    _write_collection(train_root)

    result = run_pipeline(_training_config(tmp_path, train_root))

    feature_spec = read_json(result.artifacts["feature_spec"])
    assert feature_spec["target_names"] == ["temperature", "pressure"]
    assert feature_spec["coordinate_columns"] == ["x", "time"]
    assert result.artifacts["target_sources"].exists()

    train = pd.read_csv(result.tables["processed_train"])
    valid = pd.read_csv(result.tables["processed_valid"])
    assert set(train[TARGET_COLUMN]) == {"temperature", "pressure"}
    assert set(valid[TARGET_COLUMN]) == {"temperature", "pressure"}
    assert set(map(tuple, train[["x", "time"]].to_numpy())).isdisjoint(set(map(tuple, valid[["x", "time"]].to_numpy())))

    restored = load_preprocess(
        {
            "stage_inputs": {
                "preprocess_bundle": result.artifacts["preprocess_bundle"],
                "processed_train": result.tables["processed_train"],
                "processed_valid": result.tables["processed_valid"],
            }
        }
    )
    assert TARGET_COLUMN in restored.X_train
    assert restored.target_names == ["temperature", "pressure"]

    metrics = pd.read_csv(result.tables["metrics_table_linear"])
    assert set(metrics["target"]) == {"temperature", "pressure", "__macro__"}
    assert {"relative_rmse", "skill"} <= set(metrics["metric"])
    assert isinstance(load_joblib(result.artifacts["best_model"]), TargetModelBundle)

    query_root = tmp_path / "query"
    query_root.mkdir()
    pd.DataFrame({"x": [1, 7, 20], "t": [40, 41, 42]}).to_csv(query_root / "temperature.csv", index=False)
    pd.DataFrame({"X": [8, 17], "timestamp": [40, 41]}).to_csv(query_root / "pressure.csv", index=False)
    query_manifest = _manifest(
        {"name": "temperature", "file": "temperature.csv", "columns": {"value": "temperature"}},
        {
            "name": "pressure",
            "file": "pressure.csv",
            "columns": {"x": "X", "time": "timestamp", "value": "pressure"},
        },
    )
    (query_root / "target_sources.json").write_text(json.dumps(query_manifest), encoding="utf-8")

    infer_cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")
    infer_cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    infer_cfg["data"].update(
        {
            "local_path": str(query_root),
            "source_manifest": "target_sources.json",
            "target_column": None,
            "feature_columns": None,
            "id_columns": [],
        }
    )
    infer_cfg["model"].update(
        {
            "source_type": "local_path",
            "local_model_path": str(result.run_dir),
            "model_selector": "best",
        }
    )

    infer_result = run_infer(infer_cfg)

    predictions = pd.read_csv(infer_result.tables["predictions"])
    assert predictions[["target", "x", "time"]].to_dict("records") == [
        {"target": "temperature", "x": 1, "time": 40},
        {"target": "temperature", "x": 7, "time": 41},
        {"target": "temperature", "x": 20, "time": 42},
        {"target": "pressure", "x": 8, "time": 40},
        {"target": "pressure", "x": 17, "time": 41},
    ]
    assert np.isfinite(predictions["prediction"]).all()
    summary = pd.read_csv(infer_result.tables["prediction_summary"])
    assert set(summary["target"]) == {"temperature", "pressure"}
    assert infer_result.plots == {}
