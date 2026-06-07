import numpy as np
import pandas as pd
import pytest

from ml_platform_core.config import load_run_config
from ml_platform_core.io import read_json
from ml_platform_tabular.infer import run_infer
from ml_platform_tabular.pipeline import run_pipeline


def _write_training_data(tmp_path, *, rows=80):
    rng = np.random.default_rng(2)
    df = pd.DataFrame(
        {
            "id": range(rows),
            "x1": rng.normal(size=rows),
            "x2": rng.normal(size=rows),
        }
    )
    df["target"] = 1.5 * df["x1"] + 0.5 * df["x2"] + rng.normal(scale=0.1, size=rows)
    train_path = tmp_path / "train.csv"
    infer_path = tmp_path / "infer.csv"
    df.to_csv(train_path, index=False)
    df.drop(columns=["target"]).head(8).to_csv(infer_path, index=False)
    return train_path, infer_path


def _old_style_pipeline_cfg(tmp_path, train_path, infer_path):
    cfg = {
        "task": "tabular_pipeline",
        "runtime": {"output_dir": str(tmp_path / "outputs_compat"), "use_clearml": False},
        "run": {"name": "compat_pipeline", "seed": 42, "pipeline_mode": "single"},
        "train": {
            "task_config": "config/tasks/tabular_train.yaml",
            "data": {"local_path": str(train_path), "target_column": "target", "feature_columns": None, "id_columns": ["id"]},
            "model": {"name": "ridge", "params": {"alpha": 1.0}},
        },
        "eval": {
            "task_config": "config/tasks/tabular_eval.yaml",
            "data": {"local_path": str(train_path), "target_column": "target", "feature_columns": None, "id_columns": ["id"]},
        },
        "infer": {
            "task_config": "config/tasks/tabular_infer.yaml",
            "data": {"local_path": str(infer_path), "target_column": None, "feature_columns": None, "id_columns": ["id"]},
        },
    }
    return cfg


def test_local_training_pipeline_default_graph_and_artifacts(tmp_path):
    train_path, _ = _write_training_data(tmp_path)
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)

    result = run_pipeline(cfg)

    assert result.extra["pipeline_kind"] == "training"
    assert result.extra["stages"][0] == "preprocess_features"
    assert result.extra["stages"][-1] == "evaluate_models"
    assert "infer_predictions" not in result.tables
    assert (result.run_dir / "preprocess_features").is_dir()
    assert (result.run_dir / "train_linear").is_dir()
    assert (result.run_dir / "train_ridge").is_dir()
    assert (result.run_dir / "train_random_forest").is_dir()
    assert (result.run_dir / "train_gradient_boosting").is_dir()
    assert (result.run_dir / "build_ensemble").is_dir()
    assert (result.run_dir / "evaluate_models").is_dir()

    for artifact in [
        "preprocess_bundle",
        "feature_spec",
        "leaderboard",
        "best_model",
        "best_model_json",
        "evaluation_report",
        "metrics",
        "manifest",
        "config",
        "ensemble",
        "ensemble_info",
    ]:
        assert result.artifacts[artifact].exists()
    for table in [
        "processed_train",
        "processed_valid",
        "train_features",
        "valid_features",
        "leaderboard",
        "validation_predictions_linear",
        "validation_predictions_ridge",
        "validation_predictions_random_forest",
        "validation_predictions_gradient_boosting",
        "ensemble_predictions",
    ]:
        assert result.tables[table].exists()

    leaderboard = pd.read_csv(result.tables["leaderboard"])
    assert {"linear", "ridge", "random_forest", "gradient_boosting", "mean_topk"} <= set(leaderboard["model_name"])
    assert list(leaderboard["rank"]) == list(range(1, len(leaderboard) + 1))

    best_model = read_json(result.artifacts["best_model_json"])
    assert best_model["best_model_artifact"] == str(result.artifacts["best_model"])
    assert result.artifacts["best_model"].exists()
    assert result.extra["best_model"]["model_name"] == best_model["model_name"]

    manifest = read_json(result.artifacts["manifest"])
    assert manifest["extra"]["pipeline_kind"] == "training"
    assert "infer_predictions" not in manifest["tables"]
    assert (tmp_path / "outputs" / "latest_training_pipeline" / "manifest.json").exists()
    assert not (tmp_path / "outputs" / "latest_train").exists()


def test_local_optimization_pipeline_grid_search_graph_and_artifacts(tmp_path):
    train_path, _ = _write_training_data(tmp_path, rows=40)
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["model"]["name"] = "ridge"
    cfg["model"]["params"] = {}
    cfg["model"]["candidates"] = []
    cfg["model"]["ensemble"]["enabled"] = False
    cfg["model"]["search"] = {
        "enabled": True,
        "method": "grid",
        "max_trials": 2,
        "search_space": {"alpha": [0.1, 1.0]},
    }

    result = run_pipeline(cfg)

    assert result.extra["pipeline_kind"] == "optimization"
    assert result.extra["stages"] == ["preprocess_features", "search_trials", "retrain_best", "evaluate_best"]
    assert "infer_predictions" not in result.tables
    assert (result.run_dir / "preprocess_features").is_dir()
    assert (result.run_dir / "search_trials").is_dir()
    assert (result.run_dir / "retrain_best").is_dir()
    assert (result.run_dir / "evaluate_best").is_dir()

    for artifact in [
        "preprocess_bundle",
        "feature_spec",
        "optimization_summary",
        "best_params",
        "model",
        "model_info",
        "best_model",
        "best_model_json",
        "evaluation_report",
        "metrics",
        "manifest",
    ]:
        assert result.artifacts[artifact].exists()
    assert result.tables["optimization_trials"].exists()
    trials = pd.read_csv(result.tables["optimization_trials"])
    assert len(trials) == 2
    assert set(trials["model_name"]) == {"ridge"}
    best = read_json(result.artifacts["best_model_json"])
    assert best["metric_source"] == "search_trials_validation"
    assert best["best_model_artifact"] == str(result.artifacts["best_model"])
    assert (tmp_path / "outputs" / "latest_optimization_pipeline" / "manifest.json").exists()
    assert (tmp_path / "outputs" / "latest_training_pipeline" / "manifest.json").exists()


def test_local_optimization_pipeline_rejects_search_and_ensemble(tmp_path):
    train_path, _ = _write_training_data(tmp_path, rows=40)
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["model"]["search"]["enabled"] = True

    with pytest.raises(ValueError, match="cannot be combined"):
        run_pipeline(cfg)


def test_local_optimization_pipeline_candidate_keyed_random_search(tmp_path):
    train_path, _ = _write_training_data(tmp_path, rows=50)
    rows = []
    for index in range(2):
        cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
        cfg["runtime"]["output_dir"] = str(tmp_path / f"outputs_{index}")
        cfg["data"]["local_path"] = str(train_path)
        cfg["run"]["seed"] = 123
        cfg["model"]["params"] = {}
        cfg["model"]["candidates"] = ["linear", "ridge"]
        cfg["model"]["ensemble"]["enabled"] = False
        cfg["model"]["search"] = {
            "enabled": True,
            "method": "random",
            "max_trials": 2,
            "search_space": {"ridge": {"alpha": [0.1, 1.0, 10.0]}},
        }
        result = run_pipeline(cfg)
        trials = pd.read_csv(result.tables["optimization_trials"])
        rows.append(trials["model_params"].tolist())
        assert set(trials["model_name"]) <= {"linear", "ridge"}

    assert len(rows[0]) == 2
    assert rows[0] == rows[1]


def test_local_training_pipeline_without_ensemble(tmp_path):
    train_path, _ = _write_training_data(tmp_path, rows=50)
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    cfg["model"]["candidates"] = ["linear", "ridge"]
    cfg["model"]["params"] = {"ridge": {"alpha": 1.0}}
    cfg["model"]["ensemble"]["enabled"] = False

    result = run_pipeline(cfg)

    assert "build_ensemble" not in result.extra["stages"]
    assert "ensemble" not in result.artifacts
    leaderboard = pd.read_csv(result.tables["leaderboard"])
    assert set(leaderboard["model_name"]) == {"linear", "ridge"}


def test_infer_can_reference_local_training_pipeline_best_and_ensemble(tmp_path):
    train_path, infer_path = _write_training_data(tmp_path, rows=60)
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    pipeline_result = run_pipeline(cfg)

    infer_cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")
    infer_cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    infer_cfg["data"]["local_path"] = str(infer_path)
    infer_cfg["model"]["source_type"] = "local_path"
    infer_cfg["model"]["local_model_path"] = str(pipeline_result.run_dir)
    infer_cfg["model"]["model_selector"] = "best"
    best_result = run_infer(infer_cfg)

    best_manifest = read_json(best_result.artifacts["manifest"])
    assert best_manifest["extra"]["source_type"] == "local_path"
    assert best_manifest["extra"]["model_selector"] == "best"
    assert best_manifest["extra"]["resolved_model_path"].endswith("evaluate_models\\best_model.joblib") or best_manifest["extra"][
        "resolved_model_path"
    ].endswith("evaluate_models/best_model.joblib")
    assert best_result.tables["predictions"].exists()

    infer_cfg["model"]["model_selector"] = "ensemble"
    ensemble_result = run_infer(infer_cfg)
    ensemble_manifest = read_json(ensemble_result.artifacts["manifest"])
    assert ensemble_manifest["extra"]["model_selector"] == "ensemble"
    assert ensemble_manifest["extra"]["artifact_kind"] == "ensemble"
    assert ensemble_manifest["extra"]["resolved_model_path"].endswith("build_ensemble\\model.joblib") or ensemble_manifest["extra"][
        "resolved_model_path"
    ].endswith("build_ensemble/model.joblib")


def test_infer_rejects_unknown_local_training_pipeline_selector(tmp_path):
    train_path, infer_path = _write_training_data(tmp_path, rows=40)
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    cfg["data"]["local_path"] = str(train_path)
    pipeline_result = run_pipeline(cfg)

    infer_cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")
    infer_cfg["runtime"]["output_dir"] = str(tmp_path / "outputs")
    infer_cfg["data"]["local_path"] = str(infer_path)
    infer_cfg["model"]["source_type"] = "local_path"
    infer_cfg["model"]["local_model_path"] = str(pipeline_result.run_dir)
    infer_cfg["model"]["model_selector"] = "does_not_exist"

    with pytest.raises(ValueError, match="Could not resolve model_selector"):
        run_infer(infer_cfg)


def test_deprecated_train_eval_infer_fallback_still_runs(tmp_path):
    train_path, infer_path = _write_training_data(tmp_path, rows=50)
    cfg = _old_style_pipeline_cfg(tmp_path, train_path, infer_path)

    result = run_pipeline(cfg)

    assert result.extra["pipeline_kind"] == "compatibility_train_eval_infer"
    assert result.extra["pipeline_mode"] == "single"
    assert result.tables["infer_predictions"].exists()
    assert result.artifacts["model"].exists()
