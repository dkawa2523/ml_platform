import numpy as np
import pandas as pd
import pytest

from ml_platform_core.config import load_run_config
from ml_platform_core.io import read_json
from ml_platform_tabular import models as model_module
from ml_platform_tabular.features import build_feature_pipeline
from ml_platform_tabular.infer import run_infer
from ml_platform_tabular.metrics import regression_metrics
from ml_platform_tabular.models import (
    AVAILABLE_MODELS,
    DEPENDENCY_FREE_MODELS,
    OPTIONAL_DEPENDENCY_MODELS,
    SUPPORTED_MODELS,
    build_model,
)
from ml_platform_tabular.pipeline import run_pipeline


def _assert_prediction_output(path, *, id_columns, model_name, artifact_kind):
    predictions = pd.read_csv(path)
    assert list(predictions.columns) == [
        "row_index",
        *id_columns,
        "prediction",
        "model_name",
        "artifact_kind",
        "model_artifact_id",
        "prediction_run_id",
    ]
    assert "x1" not in predictions.columns
    assert "x2" not in predictions.columns
    assert set(predictions["model_name"]) == {model_name}
    assert set(predictions["artifact_kind"]) == {artifact_kind}
    assert predictions["model_artifact_id"].str.len().min() > 0
    assert predictions["prediction_run_id"].str.len().min() > 0
    assert predictions["prediction"].notna().all()
    return predictions


def _write_training_frame(tmp_path, *, rows=40, categorical=False):
    rng = np.random.default_rng(1)
    df = pd.DataFrame(
        {
            "id": range(rows),
            "x1": rng.normal(size=rows),
            "x2": rng.normal(size=rows),
        }
    )
    if categorical:
        df["segment"] = ["a" if index % 2 == 0 else "b" for index in range(rows)]
    df["target"] = 2.0 * df["x1"] - df["x2"] + rng.normal(scale=0.1, size=rows)
    train_path = tmp_path / "train.csv"
    df.to_csv(train_path, index=False)
    return df, train_path


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


def test_model_policy_excludes_out_of_scope_models():
    assert DEPENDENCY_FREE_MODELS == [
        "linear",
        "ridge",
        "lasso",
        "elasticnet",
        "random_forest",
        "extra_trees",
        "gradient_boosting",
    ]
    assert OPTIONAL_DEPENDENCY_MODELS == ["lightgbm", "xgboost", "catboost"]
    assert SUPPORTED_MODELS == [*DEPENDENCY_FREE_MODELS, *OPTIONAL_DEPENDENCY_MODELS]
    assert AVAILABLE_MODELS == SUPPORTED_MODELS
    for name in ["knn", "svr", "mlp", "gaussian_process", "tabpfn"]:
        with pytest.raises(ValueError, match="out of current product scope"):
            build_model(name)


def test_feature_transformer_basic_options():
    df = pd.DataFrame(
        {
            "num": [1.0, np.nan, 3.0],
            "cat": ["a", None, "a"],
        }
    )

    transformer = build_feature_pipeline(
        "basic",
        df,
        {
            "numeric_impute_strategy": "mean",
            "categorical_impute_strategy": "mode",
            "scaling": "none",
        },
    )
    transformed = transformer.transform(df)

    assert transformer.numeric_fill_values["num"] == pytest.approx(2.0)
    assert transformer.categorical_fill_values["cat"] == "a"
    assert transformed[:, 0].tolist() == pytest.approx([1.0, 2.0, 3.0])


def test_feature_transformer_drop_and_passthrough_rules():
    df = pd.DataFrame(
        {
            "num": [1.0, 2.0, 3.0],
            "raw": [10.0, 20.0, 30.0],
            "cat": ["a", "b", "a"],
            "unused": [99.0, 99.0, 99.0],
        }
    )

    transformer = build_feature_pipeline(
        "basic",
        df,
        {
            "categorical_encoder": "drop",
            "drop_columns": ["unused"],
            "passthrough_columns": ["raw"],
        },
    )

    assert transformer.categorical_cols == []
    assert transformer.passthrough_cols == ["raw"]
    assert "unused" not in transformer.feature_config["passthrough_columns"]
    assert transformer.transform(df).shape[1] == 2

    with pytest.raises(ValueError, match="must be numeric"):
        build_feature_pipeline("basic", df, {"passthrough_columns": ["cat"]})


def test_optional_dependency_models_fail_cleanly_when_dependency_missing(monkeypatch):
    real_import_module = model_module.importlib.import_module

    def fake_import_module(name):
        if name in {"lightgbm", "xgboost", "catboost"}:
            raise ImportError("missing optional dependency")
        return real_import_module(name)

    monkeypatch.setattr(model_module.importlib, "import_module", fake_import_module)
    for name in ["lightgbm", "xgboost", "catboost"]:
        with pytest.raises(RuntimeError, match=r"optional dependency.*pkgs/tabular\[gbm\]"):
            build_model(name)


def test_infer_custom_prediction_name_and_reserved_columns(tmp_path):
    df, train_path = _write_training_frame(tmp_path, rows=30)
    infer_path = tmp_path / "infer.csv"
    conflict_path = tmp_path / "infer_conflict.csv"
    df.drop(columns=["target"]).head(4).to_csv(infer_path, index=False)
    df.drop(columns=["target"]).head(4).assign(model_artifact_id="existing").to_csv(conflict_path, index=False)

    _run_small_pipeline(tmp_path, train_path, id_columns=["id"], candidates=["linear"])

    infer_cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")
    infer_cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    infer_cfg["data"]["local_path"] = str(infer_path)
    infer_cfg["data"]["id_columns"] = ["id"]
    infer_cfg["output"]["prediction_name"] = "scored.csv"
    infer_cfg["output"]["chunk_size"] = 2
    infer_result = run_infer(infer_cfg)
    assert infer_result.tables["predictions"].name == "scored.csv"
    assert (tmp_path / "outputs" / "latest_infer" / "scored.csv").exists()
    predictions = _assert_prediction_output(
        infer_result.tables["predictions"],
        id_columns=["id"],
        model_name="linear",
        artifact_kind="model",
    )
    assert len(predictions) == 4
    manifest = read_json(infer_result.artifacts["manifest"])
    assert manifest["extra"]["chunk_size"] == 2

    infer_cfg["data"]["local_path"] = str(conflict_path)
    with pytest.raises(ValueError, match="reserved prediction output columns"):
        run_infer(infer_cfg)


def test_infer_schema_check_warns_for_extra_and_unseen_category(tmp_path):
    df, train_path = _write_training_frame(tmp_path, rows=24, categorical=True)
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

    infer_cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")
    infer_cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    infer_cfg["data"]["local_path"] = str(infer_path)
    infer_cfg["data"]["id_columns"] = ["id"]
    infer_result = run_infer(infer_cfg)

    schema_check = read_json(infer_result.artifacts["schema_check_summary"])
    assert schema_check["status"] == "warning"
    assert schema_check["extra_columns"] == ["extra_note"]
    assert schema_check["unknown_or_unseen_category_warning"] is True
    assert schema_check["unseen_category_columns"] == ["segment"]
    predictions = pd.read_csv(infer_result.tables["predictions"])
    assert list(predictions.columns) == [
        "row_index",
        "id",
        "prediction",
        "model_name",
        "artifact_kind",
        "model_artifact_id",
        "prediction_run_id",
    ]
    assert "extra_note" not in predictions.columns
    assert "segment" not in predictions.columns


def test_infer_schema_check_errors_for_missing_required_feature(tmp_path):
    df, train_path = _write_training_frame(tmp_path, rows=24)
    infer_path = tmp_path / "infer_missing.csv"
    df.drop(columns=["target", "x2"]).head(2).to_csv(infer_path, index=False)

    _run_small_pipeline(tmp_path, train_path, id_columns=["id"], candidates=["linear"])

    infer_cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")
    infer_cfg["run"]["name"] = "missing_feature_infer"
    infer_cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    infer_cfg["data"]["local_path"] = str(infer_path)
    infer_cfg["data"]["id_columns"] = ["id"]

    with pytest.raises(ValueError, match="Missing required inference features"):
        run_infer(infer_cfg)

    run_dirs = sorted((tmp_path / "outputs").glob("missing_feature_infer_*"))
    assert run_dirs
    schema_check = read_json(run_dirs[-1] / "schema_check_summary.json")
    assert schema_check["status"] == "error"
    assert schema_check["missing_features"] == ["x2"]


def test_regression_metrics_can_select_mse():
    values = regression_metrics([1.0, 2.0, 3.0], [1.0, 2.0, 5.0], metrics=["mse", "rmse"])
    assert list(values) == ["mse", "rmse"]
    assert values["mse"] == pytest.approx(4.0 / 3.0)

    from_string = regression_metrics([1.0, 2.0], [1.0, 4.0], metrics="mse,rmse")
    assert list(from_string) == ["mse", "rmse"]


def test_regression_metrics_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="same length"):
        regression_metrics([1.0, 2.0], [1.0])

    with pytest.raises(ValueError, match="must not be empty"):
        regression_metrics([], [])

    with pytest.raises(ValueError, match="At least one"):
        regression_metrics([1.0], [1.0], metrics=[])

    with pytest.raises(ValueError, match="Unsupported regression metric"):
        regression_metrics([1.0, 2.0], [1.0, 2.0], metrics=["median-error"])
