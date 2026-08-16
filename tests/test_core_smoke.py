import importlib.util
from pathlib import Path

import pytest
from ml_platform_core.artifacts import prepare_run_dir, write_config_snapshot, write_manifest
from ml_platform_core.config import apply_overrides, load_run_config
from ml_platform_core.io import find_table_file


def test_core_smoke(tmp_path):
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/local.yaml")
    cfg["runtime"]["output_dir"] = str(tmp_path)
    run_dir = prepare_run_dir(tmp_path, "smoke")
    config_path = write_config_snapshot(cfg, run_dir)
    manifest_path = write_manifest(run_dir, config=cfg, metrics={"x": 1.0}, artifacts={"config": config_path})
    assert config_path.exists()
    assert manifest_path.exists()


def test_apply_overrides():
    cfg = {"data": {"local_path": "old.csv"}, "model": {"params": {"n_estimators": 5}}}
    updated = apply_overrides(cfg, ["data.local_path=new.csv", "model.params.n_estimators=10", "output.flag=true"])
    assert updated["data"]["local_path"] == "new.csv"
    assert updated["model"]["params"]["n_estimators"] == 10
    assert updated["output"]["flag"] is True
    assert cfg["data"]["local_path"] == "old.csv"


def test_find_table_file_rejects_unsupported_direct_file(tmp_path):
    table = tmp_path / "data.txt"
    table.write_text("x,y\n1,2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported table format"):
        find_table_file(table)


def test_find_table_file_rejects_unsupported_preferred_file(tmp_path):
    table = tmp_path / "data.txt"
    table.write_text("x,y\n1,2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Preferred table file has unsupported table format"):
        find_table_file(tmp_path, preferred_name="data.txt")


def test_find_table_file_uses_common_suffix_filter_for_directory_search(tmp_path):
    ignored = tmp_path / "notes.txt"
    table = tmp_path / "nested" / "data.csv"
    table.parent.mkdir()
    ignored.write_text("not a table", encoding="utf-8")
    table.write_text("x,y\n1,2\n", encoding="utf-8")

    assert find_table_file(tmp_path) == table


def test_core_unused_registry_and_alias_are_removed():
    import ml_platform_core.config as config

    assert not hasattr(config, "set_dotted_path")
    assert importlib.util.find_spec("ml_platform_core.registry") is None
    assert not Path("pkgs/core/src/ml_platform_core/registry.py").exists()
