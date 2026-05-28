import numpy as np
import pandas as pd
import pytest

from ml_platform_core.config import load_run_config
from ml_platform_core.io import load_joblib, read_json
from ml_platform_tabular import TASK_NAMES, run_task
from ml_platform_tabular.evaluate import run_evaluate
from ml_platform_tabular.infer import run_infer
from ml_platform_tabular.metrics import regression_metrics
from ml_platform_tabular.train import run_train


def _assert_prediction_output(path, *, input_columns, model_name, artifact_kind):
    predictions = pd.read_csv(path)
    assert list(predictions.columns) == [
        *input_columns,
        "prediction",
        "model_name",
        "artifact_kind",
        "model_artifact_id",
        "prediction_run_id",
    ]
    assert set(predictions["model_name"]) == {model_name}
    assert set(predictions["artifact_kind"]) == {artifact_kind}
    assert predictions["model_artifact_id"].str.len().min() > 0
    assert predictions["prediction_run_id"].str.len().min() > 0
    assert predictions["prediction"].notna().all()
    return predictions


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
    assert model_info["model_name"] == "ridge"
    assert model_info["model_params"] == {"alpha": 1.0}

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
    _assert_prediction_output(
        infer_result.tables["predictions"],
        input_columns=["id", "x1", "x2"],
        model_name="ridge",
        artifact_kind="model",
    )
    assert infer_result.artifacts["model_info"].exists()
    manifest = read_json(infer_result.artifacts["manifest"])
    assert manifest["extra"]["prediction_rows"] == 10
    assert manifest["extra"]["prediction_file"] == "predictions.csv"
    assert manifest["extra"]["model_name"] == "ridge"
    assert manifest["extra"]["artifact_kind"] == "model"
    assert manifest["extra"]["prediction_schema_version"] == "v2.2"
    assert manifest["extra"]["model_artifact_id"]
    assert manifest["extra"]["id_columns"] == ["id"]
    assert manifest["extra"]["target_column"] is None
    assert manifest["extra"]["chunk_size"] is None


@pytest.mark.parametrize(
    ("model_name", "params"),
    [
        ("random_forest", {"n_estimators": 5, "random_state": 42, "n_jobs": 1}),
        ("gradient_boosting", {"n_estimators": 5, "random_state": 42}),
        ("lasso", {"alpha": 0.01, "max_iter": 5000}),
        ("elasticnet", {"alpha": 0.01, "l1_ratio": 0.5, "max_iter": 5000, "random_state": 42}),
        ("extra_trees", {"n_estimators": 5, "random_state": 42, "n_jobs": 1}),
        ("knn", {"n_neighbors": 3, "weights": "distance"}),
        ("svr", {"kernel": "rbf", "C": 1.0, "epsilon": 0.1, "gamma": "scale"}),
        ("mlp", {"hidden_layer_sizes": [16], "solver": "lbfgs", "max_iter": 500, "random_state": 42}),
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
    model_info = read_json(result.artifacts["model_info"])

    assert result.artifacts["model"].exists()
    assert result.artifacts["model_info"].exists()
    assert model_info["model_name"] == model_name
    assert model_info["model_params"] == params
    assert "rmse" in result.metrics


def test_train_candidates_write_leaderboard_and_best_model(tmp_path):
    rng = np.random.default_rng(3)
    df = pd.DataFrame(
        {
            "id": range(50),
            "x1": rng.normal(size=50),
            "x2": rng.normal(size=50),
        }
    )
    df["target"] = 1.2 * df["x1"] - 0.8 * df["x2"] + rng.normal(scale=0.05, size=50)
    train_path = tmp_path / "train.csv"
    infer_path = tmp_path / "infer.csv"
    df.to_csv(train_path, index=False)
    df.drop(columns=["target"]).head(6).to_csv(infer_path, index=False)

    cfg = load_run_config("config/tasks/tabular_train.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["model"]["candidates"] = ["linear", "ridge"]
    cfg["model"]["params"] = {"ridge": {"alpha": 1.0}}
    cfg["model"]["selection_metric"] = "rmse"

    result = run_train(cfg)

    assert result.artifacts["model"].exists()
    assert result.tables["leaderboard"].exists()
    leaderboard = pd.read_csv(result.tables["leaderboard"])
    assert list(leaderboard["rank"]) == [1, 2]
    assert set(leaderboard["model_name"]) == {"linear", "ridge"}
    assert {"rank", "model_name", "selection_metric", "rmse", "mae", "r2", "model_params", "artifact_name"} <= set(
        leaderboard.columns
    )
    assert leaderboard.loc[0, "artifact_name"] == "model"
    model_info = read_json(result.artifacts["model_info"])
    assert model_info["model_name"] == leaderboard.loc[0, "model_name"]
    assert model_info["best_model_name"] == leaderboard.loc[0, "model_name"]
    expected_params = {} if leaderboard.loc[0, "model_params"] == "{}" else {"alpha": 1.0}
    assert model_info["model_params"] == expected_params
    metrics_json = read_json(result.artifacts["metrics"])
    assert metrics_json["comparison"]["enabled"] is True
    assert metrics_json["comparison"]["best_model_name"] == model_info["model_name"]

    infer_cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")
    infer_cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    infer_cfg["data"]["local_path"] = str(infer_path)
    infer_result = run_infer(infer_cfg)
    _assert_prediction_output(
        infer_result.tables["predictions"],
        input_columns=["id", "x1", "x2"],
        model_name=model_info["model_name"],
        artifact_kind="model",
    )


def test_train_grid_search_writes_optimization_artifacts(tmp_path):
    rng = np.random.default_rng(31)
    df = pd.DataFrame({"id": range(50), "x1": rng.normal(size=50), "x2": rng.normal(size=50)})
    df["target"] = 1.1 * df["x1"] - 0.6 * df["x2"] + rng.normal(scale=0.05, size=50)
    train_path = tmp_path / "train.csv"
    infer_path = tmp_path / "infer.csv"
    df.to_csv(train_path, index=False)
    df.drop(columns=["target"]).head(6).to_csv(infer_path, index=False)

    cfg = load_run_config("config/tasks/tabular_train.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["model"]["name"] = "ridge"
    cfg["model"]["params"] = {}
    cfg["model"]["search"] = {
        "enabled": True,
        "method": "grid",
        "max_trials": 3,
        "search_space": {"alpha": [0.1, 1.0, 10.0]},
        "retrain_best": True,
    }

    result = run_train(cfg)

    trials = pd.read_csv(result.tables["optimization_trials"])
    model_info = read_json(result.artifacts["model_info"])
    metrics_json = read_json(result.artifacts["metrics"])
    summary = read_json(result.artifacts["optimization_summary"])
    best_params = read_json(result.artifacts["best_params"])

    assert len(trials) == 3
    assert {"trial", "model_name", "model_params", "selection_metric", "selection_value", "mae", "rmse", "r2", "status"} <= set(
        trials.columns
    )
    assert result.artifacts["model"].exists()
    assert result.artifacts["optimization_summary"].exists()
    assert result.artifacts["best_params"].exists()
    assert model_info["search"]["enabled"] is True
    assert model_info["search"]["method"] == "grid"
    assert model_info["search"]["completed_trials"] == 3
    assert model_info["search"]["retrained_on_full_data"] is True
    assert metrics_json["search"]["best_trial"] == summary["best_trial"]
    assert summary["best_model_name"] == "ridge"
    assert summary["best_params"] == str(result.artifacts["best_params"])
    assert best_params["model_name"] == "ridge"
    assert best_params["best_trial"] == summary["best_trial"]
    assert best_params["retrained_on_full_data"] is True

    infer_cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")
    infer_cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    infer_cfg["data"]["local_path"] = str(infer_path)
    infer_result = run_infer(infer_cfg)
    _assert_prediction_output(
        infer_result.tables["predictions"],
        input_columns=["id", "x1", "x2"],
        model_name="ridge",
        artifact_kind="model",
    )


def test_train_random_search_is_deterministic_and_limited(tmp_path):
    rng = np.random.default_rng(32)
    df = pd.DataFrame({"id": range(45), "x1": rng.normal(size=45), "x2": rng.normal(size=45)})
    df["target"] = 0.9 * df["x1"] + 0.4 * df["x2"] + rng.normal(scale=0.05, size=45)
    train_path = tmp_path / "train.csv"
    df.to_csv(train_path, index=False)

    rows = []
    for index in range(2):
        cfg = load_run_config("config/tasks/tabular_train.yaml", "config/profiles/local.yaml")
        cfg["runtime"]["output_dir"] = str(tmp_path / f"outputs_{index}")
        cfg["data"]["local_path"] = str(train_path)
        cfg["run"]["seed"] = 123
        cfg["model"]["name"] = "ridge"
        cfg["model"]["params"] = {}
        cfg["model"]["search"] = {
            "enabled": True,
            "method": "random",
            "max_trials": 2,
            "search_space": {"alpha": [0.1, 1.0, 10.0, 100.0]},
        }
        result = run_train(cfg)
        rows.append(pd.read_csv(result.tables["optimization_trials"])["model_params"].tolist())

    assert len(rows[0]) == 2
    assert rows[0] == rows[1]


def test_train_candidate_search_uses_model_keyed_space(tmp_path):
    rng = np.random.default_rng(33)
    df = pd.DataFrame({"id": range(50), "x1": rng.normal(size=50), "x2": rng.normal(size=50)})
    df["target"] = df["x1"] - df["x2"] + rng.normal(scale=0.05, size=50)
    train_path = tmp_path / "train.csv"
    df.to_csv(train_path, index=False)

    cfg = load_run_config("config/tasks/tabular_train.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["model"]["candidates"] = ["linear", "ridge"]
    cfg["model"]["params"] = {}
    cfg["model"]["search"] = {
        "enabled": True,
        "method": "grid",
        "max_trials": 4,
        "search_space": {"ridge": {"alpha": [0.1, 1.0]}},
    }

    result = run_train(cfg)

    trials = pd.read_csv(result.tables["optimization_trials"])
    assert len(trials) == 3
    assert set(trials["model_name"]) == {"linear", "ridge"}
    assert result.tables["leaderboard"].exists()


def test_train_search_rejects_unsupported_method(tmp_path):
    rng = np.random.default_rng(34)
    df = pd.DataFrame({"id": range(20), "x1": rng.normal(size=20), "x2": rng.normal(size=20)})
    df["target"] = df["x1"] + df["x2"]
    train_path = tmp_path / "train.csv"
    df.to_csv(train_path, index=False)

    cfg = load_run_config("config/tasks/tabular_train.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["model"]["search"] = {"enabled": True, "method": "bayes", "search_space": {"alpha": [1.0]}}

    with pytest.raises(ValueError, match="model.search.method"):
        run_train(cfg)


def test_train_mean_topk_ensemble_artifact_eval_and_infer(tmp_path):
    rng = np.random.default_rng(4)
    df = pd.DataFrame(
        {
            "id": range(60),
            "x1": rng.normal(size=60),
            "x2": rng.normal(size=60),
        }
    )
    df["target"] = 1.0 * df["x1"] - 0.4 * df["x2"] + rng.normal(scale=0.05, size=60)
    train_path = tmp_path / "train.csv"
    infer_path = tmp_path / "infer.csv"
    df.to_csv(train_path, index=False)
    df.drop(columns=["target"]).head(8).to_csv(infer_path, index=False)

    cfg = load_run_config("config/tasks/tabular_train.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["data"]["id_columns"] = ["id"]
    cfg["model"]["candidates"] = ["linear", "ridge"]
    cfg["model"]["params"] = {"ridge": {"alpha": 1.0}}
    cfg["model"]["ensemble"] = {"enabled": True, "method": "mean_topk", "top_k": 2}

    train_result = run_train(cfg)
    model = load_joblib(train_result.artifacts["model"])
    model_info = read_json(train_result.artifacts["model_info"])

    assert model_info["artifact_kind"] == "ensemble"
    assert model_info["ensemble_method"] == "mean_topk"
    assert len(model_info["selected_base_models"]) == 2
    assert train_result.tables["leaderboard"].exists()
    leaderboard = pd.read_csv(train_result.tables["leaderboard"])
    assert "mean_topk" in set(leaderboard["model_name"])
    assert leaderboard.loc[leaderboard["model_name"] == "mean_topk", "artifact_name"].iloc[0] == "model"
    assert train_result.tables["ensemble_predictions"].exists()
    assert len(list((train_result.run_dir / "base_models").glob("*.joblib"))) == 2
    assert len(model.predict(df.drop(columns=["target"]).head(3))) == 3

    eval_cfg = load_run_config("config/tasks/tabular_eval.yaml", "config/profiles/local.yaml")
    eval_cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    eval_cfg["data"]["local_path"] = str(train_path)
    eval_cfg["data"]["target_column"] = "target"
    eval_result = run_evaluate(eval_cfg)
    assert eval_result.tables["evaluation_predictions"].exists()

    infer_cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")
    infer_cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    infer_cfg["data"]["local_path"] = str(infer_path)
    infer_result = run_infer(infer_cfg)
    assert infer_result.tables["predictions"].exists()
    _assert_prediction_output(
        infer_result.tables["predictions"],
        input_columns=["id", "x1", "x2"],
        model_name="mean_topk",
        artifact_kind="ensemble",
    )


def test_train_weighted_ensemble_artifact_eval_and_infer(tmp_path):
    rng = np.random.default_rng(5)
    df = pd.DataFrame(
        {
            "id": range(60),
            "x1": rng.normal(size=60),
            "x2": rng.normal(size=60),
        }
    )
    df["target"] = 0.8 * df["x1"] + 0.7 * df["x2"] + rng.normal(scale=0.05, size=60)
    train_path = tmp_path / "train.csv"
    infer_path = tmp_path / "infer.csv"
    df.to_csv(train_path, index=False)
    df.drop(columns=["target"]).head(8).to_csv(infer_path, index=False)

    cfg = load_run_config("config/tasks/tabular_train.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["data"]["id_columns"] = ["id"]
    cfg["model"]["candidates"] = ["linear", "ridge"]
    cfg["model"]["params"] = {"ridge": {"alpha": 1.0}}
    cfg["model"]["ensemble"] = {"enabled": True, "method": "weighted", "top_k": 2}

    train_result = run_train(cfg)
    model = load_joblib(train_result.artifacts["model"])
    model_info = read_json(train_result.artifacts["model_info"])

    assert model_info["artifact_kind"] == "ensemble"
    assert model_info["model_name"] == "weighted"
    assert model_info["ensemble_method"] == "weighted"
    assert len(model_info["selected_base_models"]) == 2
    assert len(model_info["weights"]) == 2
    assert sum(model_info["weights"]) == pytest.approx(1.0)
    assert train_result.tables["ensemble_predictions"].exists()
    assert len(list((train_result.run_dir / "base_models").glob("*.joblib"))) == 2
    assert len(model.predict(df.drop(columns=["target"]).head(3))) == 3

    leaderboard = pd.read_csv(train_result.tables["leaderboard"])
    assert "weighted" in set(leaderboard["model_name"])
    assert leaderboard.loc[leaderboard["model_name"] == "weighted", "artifact_name"].iloc[0] == "model"

    eval_cfg = load_run_config("config/tasks/tabular_eval.yaml", "config/profiles/local.yaml")
    eval_cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    eval_cfg["data"]["local_path"] = str(train_path)
    eval_cfg["data"]["target_column"] = "target"
    eval_result = run_evaluate(eval_cfg)
    assert eval_result.tables["evaluation_predictions"].exists()

    infer_cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")
    infer_cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    infer_cfg["data"]["local_path"] = str(infer_path)
    infer_result = run_infer(infer_cfg)
    assert infer_result.tables["predictions"].exists()
    _assert_prediction_output(
        infer_result.tables["predictions"],
        input_columns=["id", "x1", "x2"],
        model_name="weighted",
        artifact_kind="ensemble",
    )


def test_infer_custom_prediction_name_and_reserved_columns(tmp_path):
    rng = np.random.default_rng(6)
    df = pd.DataFrame(
        {
            "id": range(30),
            "x1": rng.normal(size=30),
            "x2": rng.normal(size=30),
        }
    )
    df["target"] = df["x1"] + df["x2"]
    train_path = tmp_path / "train.csv"
    infer_path = tmp_path / "infer.csv"
    conflict_path = tmp_path / "infer_conflict.csv"
    df.to_csv(train_path, index=False)
    df.drop(columns=["target"]).head(4).to_csv(infer_path, index=False)
    df.drop(columns=["target"]).head(4).assign(model_artifact_id="existing").to_csv(conflict_path, index=False)

    cfg = load_run_config("config/tasks/tabular_train.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["data"]["target_column"] = "target"
    cfg["data"]["id_columns"] = ["id"]
    cfg["model"]["name"] = "linear"
    cfg["model"]["params"] = {}
    run_train(cfg)

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
        input_columns=["id", "x1", "x2"],
        model_name="linear",
        artifact_kind="model",
    )
    assert len(predictions) == 4
    manifest = read_json(infer_result.artifacts["manifest"])
    assert manifest["extra"]["chunk_size"] == 2

    infer_cfg["data"]["local_path"] = str(conflict_path)
    with pytest.raises(ValueError, match="reserved prediction output columns"):
        run_infer(infer_cfg)


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
