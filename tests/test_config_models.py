import pytest

from ml_platform_core.config import load_run_config, load_typed_run_config
from ml_platform_core.config_models import ConfigValidationError, parse_run_config


def test_parse_run_config_accepts_valid_minimal_config():
    cfg = parse_run_config({"task": "tabular_pipeline", "run": {"name": "demo"}})

    assert cfg.task == "tabular_pipeline"
    assert cfg.run.name == "demo"
    assert cfg.runtime.output_dir == "outputs"
    assert cfg.runtime.use_clearml is False
    assert cfg.split.method == "random"
    assert cfg.split.valid_size == 0.2
    assert cfg.model.ensemble.method == "mean_topk"
    assert cfg.model.ensemble.top_k == 3


def test_parse_run_config_rejects_wrong_known_section_types():
    with pytest.raises(ConfigValidationError, match="runtime.use_clearml must be a boolean"):
        parse_run_config({"task": "tabular_pipeline", "runtime": {"use_clearml": "true"}})

    with pytest.raises(ConfigValidationError, match="model.params must be a mapping"):
        parse_run_config({"task": "tabular_pipeline", "model": {"params": "ridge"}})

    with pytest.raises(ConfigValidationError, match="Unsupported tabular stage"):
        parse_run_config({"task": "tabular_stage", "run": {"stage": "unknown_stage"}})


def test_parse_run_config_preserves_unknown_keys_as_extras():
    cfg = parse_run_config(
        {
            "task": "tabular_pipeline",
            "owner": "team-a",
            "runtime": {"output_dir": "out", "custom_runtime": 1},
            "data": {"local_path": "train.csv", "custom_data": True},
        }
    )

    assert cfg.extras == {"owner": "team-a"}
    assert cfg.runtime.extras == {"custom_runtime": 1}
    assert cfg.data.extras == {"custom_data": True}
    assert cfg.to_dict()["owner"] == "team-a"
    assert cfg.to_dict()["runtime"]["custom_runtime"] == 1
    assert cfg.to_dict()["data"]["custom_data"] is True


def test_load_typed_run_config_parses_after_overrides():
    cfg = load_typed_run_config(
        "config/tasks/tabular_pipeline.yaml",
        "config/profiles/local.yaml",
        overrides=[
            "run.seed=7",
            "split.valid_size=0.3",
            "runtime.use_clearml=true",
            "model.ensemble.top_k=2",
        ],
    )

    assert cfg.run.seed == 7
    assert cfg.split.valid_size == 0.3
    assert cfg.runtime.use_clearml is True
    assert cfg.model.ensemble.top_k == 2
    assert cfg.meta["overrides"]["run"]["seed"] == 7


def test_load_run_config_keeps_dict_compatibility():
    cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")

    assert isinstance(cfg, dict)
    assert cfg["task"] == "tabular_infer"
    assert cfg["model"]["source_type"] == "local_path"
    assert "split" not in cfg
    assert "features" not in cfg
