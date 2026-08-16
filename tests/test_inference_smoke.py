import numpy as np
import pandas as pd
import pytest
from ml_platform_core.config import load_run_config
from ml_platform_core.io import read_json
from ml_platform_tabular.inference import run_infer
from ml_platform_tabular.training import run_pipeline


def _write_training_frame(tmp_path, *, rows=40, categorical=False):
    rng = np.random.default_rng(1)
    frame = pd.DataFrame(
        {
            "id": range(rows),
            "x1": rng.normal(size=rows),
            "x2": rng.normal(size=rows),
        }
    )
    if categorical:
        frame["segment"] = ["a" if index % 2 == 0 else "b" for index in range(rows)]
    frame["target"] = 2.0 * frame["x1"] - frame["x2"] + rng.normal(scale=0.1, size=rows)
    train_path = tmp_path / "train.csv"
    frame.to_csv(train_path, index=False)
    return frame, train_path


def _run_small_pipeline(tmp_path, train_path, *, id_columns=None, candidates=None, params=None):
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["data"]["target_column"] = "target"
    cfg["data"]["id_columns"] = list(id_columns or [])
    cfg["model"]["candidates"] = list(candidates or ["linear"])
    cfg["model"]["params"] = params or {}
    cfg["model"]["ensemble"]["enabled"] = False
    return run_pipeline(cfg)


def _infer_config(tmp_path, infer_path):
    cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(infer_path)
    cfg["data"]["id_columns"] = ["id"]
    return cfg


def test_infer_custom_prediction_name_and_reserved_columns(tmp_path):
    frame, train_path = _write_training_frame(tmp_path, rows=30)
    infer_path = tmp_path / "infer.csv"
    conflict_path = tmp_path / "infer_conflict.csv"
    frame.drop(columns=["target"]).head(4).to_csv(infer_path, index=False)
    frame.drop(columns=["target"]).head(4).assign(prediction="existing").to_csv(conflict_path, index=False)
    _run_small_pipeline(tmp_path, train_path, id_columns=["id"], candidates=["linear"])

    infer_cfg = _infer_config(tmp_path, infer_path)
    infer_cfg["output"]["prediction_name"] = "scored.csv"
    infer_result = run_infer(infer_cfg)
    predictions = pd.read_csv(infer_result.tables["predictions"])

    assert infer_result.tables["predictions"].name == "scored.csv"
    assert (tmp_path / "outputs" / "latest_infer" / "scored.csv").exists()
    assert list(predictions.columns) == ["row_index", "id", "prediction"]
    assert len(predictions) == 4
    assert predictions["prediction"].notna().all()
    infer_cfg["data"]["local_path"] = str(conflict_path)
    with pytest.raises(ValueError, match="reserved prediction output columns"):
        run_infer(infer_cfg)


def test_infer_schema_check_warns_for_extra_and_unseen_category(tmp_path):
    _frame, train_path = _write_training_frame(tmp_path, rows=24, categorical=True)
    infer_path = tmp_path / "infer.csv"
    pd.DataFrame(
        {
            "id": [10, 11],
            "x1": [0.7, 0.8],
            "x2": [0.1, 0.2],
            "segment": ["new_segment", "a"],
            "extra_note": ["keep out", "keep out"],
        }
    ).to_csv(infer_path, index=False)
    _run_small_pipeline(
        tmp_path,
        train_path,
        id_columns=["id"],
        candidates=["ridge"],
        params={"ridge": {"alpha": 1.0}},
    )

    infer_result = run_infer(_infer_config(tmp_path, infer_path))
    schema_check = read_json(infer_result.artifacts["schema_check_summary"])
    predictions = pd.read_csv(infer_result.tables["predictions"])

    assert schema_check["status"] == "warning"
    assert schema_check["extra_columns"] == ["extra_note"]
    assert schema_check["unknown_or_unseen_category_warning"] is True
    assert schema_check["unseen_category_columns"] == ["segment"]
    assert list(predictions.columns) == ["row_index", "id", "prediction"]


def test_infer_schema_check_errors_for_missing_required_feature(tmp_path):
    frame, train_path = _write_training_frame(tmp_path, rows=24)
    infer_path = tmp_path / "infer_missing.csv"
    frame.drop(columns=["target", "x2"]).head(2).to_csv(infer_path, index=False)
    _run_small_pipeline(tmp_path, train_path, id_columns=["id"], candidates=["linear"])
    infer_cfg = _infer_config(tmp_path, infer_path)
    infer_cfg["run"]["name"] = "missing_feature_infer"

    with pytest.raises(ValueError, match="Missing required inference features"):
        run_infer(infer_cfg)

    run_dirs = sorted((tmp_path / "outputs").glob("missing_feature_infer_*"))
    assert run_dirs
    schema_check = read_json(run_dirs[-1] / "schema_check_summary.json")
    assert schema_check["status"] == "error"
    assert schema_check["missing_features"] == ["x2"]
