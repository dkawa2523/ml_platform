import numpy as np
import pandas as pd
import pytest

from ml_platform_core.config import load_run_config
from ml_platform_core.io import read_json
from ml_platform_tabular import TASK_NAMES, run_task
from ml_platform_tabular.evaluate import run_evaluate
from ml_platform_tabular.infer import run_infer
from ml_platform_tabular.metrics import regression_metrics
from ml_platform_tabular.train import run_train


def test_tabular_train_eval_and_infer_smoke(tmp_path):
    rng = np.random.default_rng(1)
    df = pd.DataFrame(
        {
            "id": range(50),
            "x1": rng.normal(size=50),
            "x2": rng.normal(size=50),
        }
    )
    df["target"] = 2.0 * df["x1"] - df["x2"] + rng.normal(scale=0.1, size=50)
    train_path = tmp_path / "train.csv"
    infer_path = tmp_path / "infer.csv"
    df.to_csv(train_path, index=False)
    df.drop(columns=["target"]).head(10).to_csv(infer_path, index=False)

    cfg = load_run_config("config/tasks/tabular_train.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["data"]["target_column"] = "target"
    cfg["data"]["id_columns"] = ["id"]
    cfg["model"]["name"] = "ridge"
    cfg["model"]["params"] = {"alpha": 1.0}

    train_result = run_train(cfg)
    assert train_result.artifacts["model"].exists()
    assert train_result.artifacts["model_info"].exists()
    assert "rmse" in train_result.metrics
    assert "mse" not in train_result.metrics
    assert (tmp_path / "outputs" / "latest_train" / "model.joblib").exists()
    model_info = read_json(train_result.artifacts["model_info"])
    assert model_info["feature_columns"] == ["x1", "x2"]

    eval_cfg = load_run_config("config/tasks/tabular_eval.yaml", "config/profiles/local.yaml")
    eval_cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    eval_cfg["data"]["local_path"] = str(train_path)
    eval_cfg["data"]["target_column"] = "target"
    cfg["data"]["id_columns"] = ["id"]
    eval_cfg["data"]["id_columns"] = ["id"]
    # Do not pass model.artifact_path to verify default latest_train lookup.
    eval_result = run_evaluate(eval_cfg)
    assert eval_result.tables["evaluation_predictions"].exists()
    assert (tmp_path / "outputs" / "latest_eval" / "metrics.json").exists()

    infer_cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")
    infer_cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    infer_cfg["data"]["local_path"] = str(infer_path)
    infer_cfg["data"]["id_columns"] = ["id"]
    # Do not pass model.artifact_path or feature_columns to verify model_info lookup.
    infer_result = run_infer(infer_cfg)
    assert infer_result.tables["predictions"].exists()
    assert (tmp_path / "outputs" / "latest_infer" / "predictions.csv").exists()


@pytest.mark.parametrize(
    ("model_name", "params"),
    [
        ("random_forest", {"n_estimators": 5, "random_state": 42, "n_jobs": 1}),
        ("gradient_boosting", {"n_estimators": 5, "random_state": 42}),
    ],
)
def test_sklearn_backed_models_train_smoke(tmp_path, model_name, params):
    rng = np.random.default_rng(2)
    df = pd.DataFrame(
        {
            "id": range(40),
            "x1": rng.normal(size=40),
            "x2": rng.normal(size=40),
        }
    )
    df["target"] = 1.5 * df["x1"] + 0.5 * df["x2"] + rng.normal(scale=0.05, size=40)
    train_path = tmp_path / "train.csv"
    df.to_csv(train_path, index=False)

    cfg = load_run_config("config/tasks/tabular_train.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["model"]["name"] = model_name
    cfg["model"]["params"] = params

    result = run_train(cfg)

    assert result.artifacts["model"].exists()
    assert result.artifacts["model_info"].exists()
    assert "rmse" in result.metrics


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


def test_tabular_1d_output_smoke(tmp_path):
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "x1": [3.0, 1.0, 2.0],
            "target": [30.0, 10.0, 20.0],
        }
    )
    input_path = tmp_path / "input.csv"
    df.to_csv(input_path, index=False)

    cfg = load_run_config("config/tasks/tabular_1d_output.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(input_path)

    result = run_task(cfg)

    assert "tabular_1d_output" in TASK_NAMES
    assert result.tables["output_1d"].exists()
    output_df = pd.read_csv(result.tables["output_1d"])
    assert list(output_df.columns) == ["id", "x", "value"]
    assert output_df["x"].tolist() == [1.0, 2.0, 3.0]
    assert result.artifacts["summary"].exists()
    assert (tmp_path / "outputs" / "latest_1d_output" / "tabular_1d_output.csv").exists()
