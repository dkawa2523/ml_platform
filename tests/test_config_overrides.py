from ml_platform_core.config import load_run_config, parse_overrides


def test_cli_override_parser():
    overrides = parse_overrides(
        [
            "model.name=ridge",
            "model.params.ridge.alpha=0.5",
            "data.feature_columns=[x1, x2]",
            "metrics.names=mse,rmse",
        ]
    )
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml", overrides=overrides)
    assert cfg["model"]["name"] == "ridge"
    assert cfg["model"]["params"]["ridge"]["alpha"] == 0.5
    assert cfg["data"]["feature_columns"] == ["x1", "x2"]
    assert cfg["metrics"]["names"] == "mse,rmse"
