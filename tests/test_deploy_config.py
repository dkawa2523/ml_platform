from pathlib import Path


def test_standard_clearml_agent_image_installs_gbm_extras():
    dockerfile = Path("deploy/base/Dockerfile").read_text(encoding="utf-8")

    assert '-e "pkgs/tabular[gbm]"' in dockerfile


def test_gbm_packages_are_not_required_runtime_dependencies():
    requirements = Path("requirements.txt").read_text(encoding="utf-8").lower()

    assert "lightgbm" not in requirements
    assert "xgboost" not in requirements
    assert "catboost" not in requirements
