import numpy as np
import pandas as pd

from ml_platform_core.config import load_run_config
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
    assert result.tables["infer_predictions"].exists()
