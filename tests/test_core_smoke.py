from ml_platform_core.artifacts import prepare_run_dir, write_config_snapshot, write_manifest
from ml_platform_core.config import apply_overrides, load_run_config


def test_core_smoke(tmp_path):
    cfg = load_run_config("config/tasks/tabular_train.yaml", "config/profiles/local.yaml")
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
