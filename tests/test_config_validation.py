import pytest
from ml_platform_core.config import load_run_config
from ml_platform_core.config_validation import ConfigValidationError, validate_run_config


def test_validate_run_config_accepts_valid_minimal_config():
    validate_run_config({"task": "tabular_pipeline", "run": {"name": "demo"}})


def test_validate_run_config_rejects_invalid_public_values():
    with pytest.raises(ConfigValidationError, match=r"runtime\.use_clearml must be a boolean"):
        validate_run_config({"task": "tabular_pipeline", "runtime": {"use_clearml": "true"}})

    with pytest.raises(ConfigValidationError, match=r"model\.params must be a mapping"):
        validate_run_config({"task": "tabular_pipeline", "model": {"params": "ridge"}})

    with pytest.raises(ConfigValidationError, match="Unsupported tabular stage"):
        validate_run_config({"task": "tabular_stage", "run": {"stage": "unknown_stage"}})

    with pytest.raises(ConfigValidationError, match=r"split\.selection_size must be between"):
        validate_run_config({"task": "tabular_pipeline", "split": {"selection_size": 1.0}})

    with pytest.raises(ConfigValidationError, match=r"features\.max_dense_cells must be at least 1"):
        validate_run_config({"task": "tabular_pipeline", "features": {"max_dense_cells": 0}})


def test_load_run_config_preserves_effective_dictionary_and_overrides():
    cfg = load_run_config(
        "config/tasks/tabular_pipeline.yaml",
        "config/profiles/local.yaml",
        overrides=[
            "run.seed=7",
            "split.valid_size=0.3",
            "runtime.use_clearml=true",
            "model.ensemble.top_k=2",
        ],
    )

    assert cfg["run"]["seed"] == 7
    assert cfg["split"]["valid_size"] == 0.3
    assert cfg["runtime"]["use_clearml"] is True
    assert cfg["model"]["ensemble"]["top_k"] == 2
    assert cfg["_meta"]["overrides"]["run"]["seed"] == 7


def test_load_run_config_keeps_task_specific_sections():
    cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/local.yaml")

    assert cfg["task"] == "tabular_infer"
    assert cfg["model"]["source_type"] == "local_path"
    assert "split" not in cfg
    assert "features" not in cfg
