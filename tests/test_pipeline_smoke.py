import numpy as np
import pandas as pd
import pytest

from ml_platform_core.config import load_run_config
from ml_platform_core.io import read_json
from ml_platform_tabular.pipeline import run_pipeline


def test_tabular_pipeline_smoke(tmp_path):
    rng = np.random.default_rng(2)
    df = pd.DataFrame({"x1": rng.normal(size=60), "x2": rng.normal(size=60)})
    df["target"] = 1.5 * df["x1"] + 0.5 * df["x2"] + rng.normal(scale=0.1, size=60)
    train_path = tmp_path / "train.csv"
    infer_path = tmp_path / "infer.csv"
    df.to_csv(train_path, index=False)
    df.drop(columns=["target"]).head(8).to_csv(infer_path, index=False)

    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["train"]["data"] = {"local_path": str(train_path), "target_column": "target", "feature_columns": None, "id_columns": []}
    cfg["train"]["model"] = {"name": "ridge", "params": {"alpha": 1.0}}
    cfg["eval"]["data"] = {"local_path": str(train_path), "target_column": "target", "feature_columns": None, "id_columns": []}
    cfg["infer"]["data"] = {"local_path": str(infer_path), "target_column": None, "feature_columns": None, "id_columns": []}

    result = run_pipeline(cfg)
    assert "train_rmse" in result.metrics
    assert "eval_rmse" in result.metrics
    assert result.artifacts["model"].exists()
    assert result.artifacts["train_model_info"].exists()
    assert result.tables["infer_predictions"].exists()
    summary = read_json(result.artifacts["summary"])
    assert summary["pipeline_mode"] == "single"
    assert summary["model_name"] == "ridge"
    assert summary["artifact_kind"] == "model"
    assert summary["model_info"] == str(result.artifacts["train_model_info"])
    manifest = read_json(result.artifacts["manifest"])
    assert "eval_evaluation_predictions" in manifest["tables"]
    assert "infer_predictions" in manifest["tables"]


def test_pipeline_root_model_params_replace_task_defaults(tmp_path):
    rng = np.random.default_rng(3)
    df = pd.DataFrame({"x1": rng.normal(size=40), "x2": rng.normal(size=40)})
    df["target"] = 0.7 * df["x1"] - 0.3 * df["x2"] + rng.normal(scale=0.1, size=40)
    train_path = tmp_path / "train.csv"
    infer_path = tmp_path / "infer.csv"
    df.to_csv(train_path, index=False)
    df.drop(columns=["target"]).head(5).to_csv(infer_path, index=False)

    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["model"] = {"name": "random_forest", "params": {"n_estimators": 5, "random_state": 42, "n_jobs": 1}}
    cfg["train"]["data"] = {"local_path": str(train_path), "target_column": "target", "feature_columns": None, "id_columns": []}
    cfg["eval"]["data"] = {"local_path": str(train_path), "target_column": "target", "feature_columns": None, "id_columns": []}
    cfg["infer"]["data"] = {"local_path": str(infer_path), "target_column": None, "feature_columns": None, "id_columns": []}

    result = run_pipeline(cfg)

    assert result.artifacts["model"].exists()
    assert "eval_rmse" in result.metrics


@pytest.mark.parametrize(
    ("mode", "ensemble"),
    [
        ("compare", {"enabled": False, "method": "mean_topk", "top_k": 2}),
        ("ensemble", {"enabled": True, "method": "mean_topk", "top_k": 2}),
        ("ensemble", {"enabled": True, "method": "weighted", "top_k": 2}),
    ],
)
def test_pipeline_comparison_and_ensemble_artifacts(tmp_path, mode, ensemble):
    rng = np.random.default_rng(4)
    df = pd.DataFrame({"x1": rng.normal(size=80), "x2": rng.normal(size=80)})
    df["target"] = 1.2 * df["x1"] - 0.2 * df["x2"] + rng.normal(scale=0.1, size=80)
    train_path = tmp_path / "train.csv"
    infer_path = tmp_path / "infer.csv"
    df.to_csv(train_path, index=False)
    df.drop(columns=["target"]).head(6).to_csv(infer_path, index=False)

    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["model"] = {
        "name": "ridge",
        "params": {},
        "candidates": [
            {"name": "linear", "params": {}},
            {"name": "ridge", "params": {"alpha": 1.0}},
        ],
        "selection_metric": "rmse",
        "ensemble": ensemble,
    }
    cfg["train"]["data"] = {"local_path": str(train_path), "target_column": "target", "feature_columns": None, "id_columns": []}
    cfg["eval"]["data"] = {"local_path": str(train_path), "target_column": "target", "feature_columns": None, "id_columns": []}
    cfg["infer"]["data"] = {"local_path": str(infer_path), "target_column": None, "feature_columns": None, "id_columns": []}

    result = run_pipeline(cfg)

    assert result.extra["pipeline_mode"] == mode
    assert result.tables["train_leaderboard"].exists()
    assert result.tables["eval_evaluation_predictions"].exists()
    assert result.tables["infer_predictions"].exists()
    assert result.artifacts["train_model_info"].exists()
    model_info = read_json(result.artifacts["train_model_info"])
    if ensemble["enabled"]:
        assert result.extra["artifact_kind"] == "ensemble"
        assert result.artifacts["train_ensemble_info"].exists()
        assert result.tables["train_ensemble_predictions"].exists()
        assert model_info["produced_model_name"] == ensemble["method"]
        assert model_info["selected_base_models"]
    else:
        assert result.extra["artifact_kind"] == "model"
        assert "train_ensemble_predictions" not in result.tables

    manifest = read_json(result.artifacts["manifest"])
    assert "train_leaderboard" in manifest["tables"]
    assert "train_model_info" in manifest["artifacts"]


def test_pipeline_search_artifacts_feed_eval_and_infer(tmp_path):
    rng = np.random.default_rng(5)
    df = pd.DataFrame({"x1": rng.normal(size=70), "x2": rng.normal(size=70)})
    df["target"] = 0.9 * df["x1"] + 0.4 * df["x2"] + rng.normal(scale=0.1, size=70)
    train_path = tmp_path / "train.csv"
    infer_path = tmp_path / "infer.csv"
    df.to_csv(train_path, index=False)
    df.drop(columns=["target"]).head(5).to_csv(infer_path, index=False)

    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["model"] = {
        "name": "ridge",
        "params": {},
        "selection_metric": "rmse",
        "search": {
            "enabled": True,
            "method": "grid",
            "max_trials": 2,
            "search_space": {"alpha": [0.1, 1.0]},
        },
    }
    cfg["train"]["data"] = {"local_path": str(train_path), "target_column": "target", "feature_columns": None, "id_columns": []}
    cfg["eval"]["data"] = {"local_path": str(train_path), "target_column": "target", "feature_columns": None, "id_columns": []}
    cfg["infer"]["data"] = {"local_path": str(infer_path), "target_column": None, "feature_columns": None, "id_columns": []}

    result = run_pipeline(cfg)

    assert result.extra["pipeline_mode"] == "optimize"
    assert result.artifacts["train_optimization_summary"].exists()
    assert result.artifacts["train_best_params"].exists()
    assert result.tables["train_optimization_trials"].exists()
    assert result.tables["eval_evaluation_predictions"].exists()
    assert result.tables["infer_predictions"].exists()
    model_info = read_json(result.artifacts["train_model_info"])
    assert model_info["search"]["enabled"] is True
    assert model_info["search"]["completed_trials"] == 2
    assert model_info["search"]["retrained_on_full_data"] is True


def test_pipeline_accepts_legacy_mode_aliases(tmp_path):
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["run"]["pipeline_mode"] = "comparison"
    cfg["model"] = {"name": "ridge", "params": {}, "candidates": ["linear", "ridge"], "selection_metric": "rmse"}

    rng = np.random.default_rng(7)
    df = pd.DataFrame({"x1": rng.normal(size=50), "x2": rng.normal(size=50)})
    df["target"] = df["x1"] + rng.normal(scale=0.1, size=50)
    train_path = tmp_path / "train.csv"
    infer_path = tmp_path / "infer.csv"
    df.to_csv(train_path, index=False)
    df.drop(columns=["target"]).head(4).to_csv(infer_path, index=False)
    cfg["train"]["data"] = {"local_path": str(train_path), "target_column": "target", "feature_columns": None, "id_columns": []}
    cfg["eval"]["data"] = {"local_path": str(train_path), "target_column": "target", "feature_columns": None, "id_columns": []}
    cfg["infer"]["data"] = {"local_path": str(infer_path), "target_column": None, "feature_columns": None, "id_columns": []}

    result = run_pipeline(cfg)

    assert result.extra["pipeline_mode"] == "compare"
    assert result.tables["train_leaderboard"].exists()


def test_pipeline_explicit_ensemble_mode_enables_ensemble(tmp_path):
    rng = np.random.default_rng(6)
    df = pd.DataFrame({"x1": rng.normal(size=60), "x2": rng.normal(size=60)})
    df["target"] = 0.8 * df["x1"] + 0.2 * df["x2"] + rng.normal(scale=0.1, size=60)
    train_path = tmp_path / "train.csv"
    infer_path = tmp_path / "infer.csv"
    df.to_csv(train_path, index=False)
    df.drop(columns=["target"]).head(5).to_csv(infer_path, index=False)

    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["run"]["pipeline_mode"] = "ensemble"
    cfg["model"] = {
        "name": "ridge",
        "params": {},
        "candidates": ["linear", "ridge"],
        "selection_metric": "rmse",
        "ensemble": {"method": "mean_topk", "top_k": 2},
    }
    cfg["train"]["data"] = {"local_path": str(train_path), "target_column": "target", "feature_columns": None, "id_columns": []}
    cfg["eval"]["data"] = {"local_path": str(train_path), "target_column": "target", "feature_columns": None, "id_columns": []}
    cfg["infer"]["data"] = {"local_path": str(infer_path), "target_column": None, "feature_columns": None, "id_columns": []}

    result = run_pipeline(cfg)

    assert result.extra["pipeline_mode"] == "ensemble"
    assert result.extra["artifact_kind"] == "ensemble"
    assert result.tables["train_leaderboard"].exists()
    assert result.tables["train_ensemble_predictions"].exists()


def test_pipeline_invalid_search_and_ensemble_mode(tmp_path):
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["run"]["pipeline_mode"] = "auto"
    cfg["model"] = {
        "name": "ridge",
        "params": {},
        "candidates": ["linear", "ridge"],
        "search": {"enabled": True, "method": "grid", "search_space": {"alpha": [1.0]}},
        "ensemble": {"enabled": True, "method": "mean_topk", "top_k": 2},
    }

    with pytest.raises(ValueError, match="cannot combine|cannot be combined"):
        run_pipeline(cfg)
