import pytest

from ml_platform_core.config import load_run_config, parse_overrides
from ml_platform_core.value_coercion import as_bool


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


def test_config_override_is_validated_after_application():
    with pytest.raises(ValueError, match="runtime.use_clearml must be a boolean"):
        load_run_config(
            "config/tasks/tabular_pipeline.yaml",
            "config/profiles/local.yaml",
            overrides=["runtime.use_clearml=not-a-boolean"],
        )


def test_boolean_coercion_rejects_unknown_text():
    with pytest.raises(ValueError, match="Cannot convert value to boolean"):
        as_bool("not-a-boolean")
