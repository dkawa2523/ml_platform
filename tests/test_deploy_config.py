from pathlib import Path


def test_execution_image_installs_gbm_extras():
    dockerfile = Path("deploy/base/Dockerfile").read_text(encoding="utf-8")

    assert '-e "pkgs/tabular[gbm]"' in dockerfile


def test_profiles_define_pullable_execution_image_reference():
    dev_profile = Path("config/profiles/clearml-dev.yaml").read_text(encoding="utf-8")
    prod_profile = Path("config/profiles/clearml-prod.yaml").read_text(encoding="utf-8")

    assert "execution:" in dev_profile
    assert "image: registry.example.com/ml-platform/clearml-agent:dev" in dev_profile
    assert "execution:" in prod_profile
    assert "image: registry.example.com/ml-platform/clearml-agent:prod" in prod_profile


def test_gbm_packages_are_not_required_runtime_dependencies():
    requirements = Path("requirements.txt").read_text(encoding="utf-8").lower()

    assert "lightgbm" not in requirements
    assert "xgboost" not in requirements
    assert "catboost" not in requirements
