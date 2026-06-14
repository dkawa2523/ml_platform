from pathlib import Path
import importlib.util


def test_execution_image_installs_gbm_extras():
    dockerfile = Path("deploy/base/Dockerfile").read_text(encoding="utf-8")

    assert '-e "pkgs/tabular[gbm]"' in dockerfile


def test_agent_config_exposes_execution_image_site_packages():
    configmap = Path("deploy/base/configmap.yaml").read_text(encoding="utf-8")

    assert "CLEARML_AGENT_FORCE_SYSTEM_SITE_PACKAGES" in configmap
    assert '"true"' in configmap


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


def test_clearml_remote_packages_install_gbm_into_execution_venv():
    spec = importlib.util.spec_from_file_location("ml_platform_clearml_templates", Path("clearml/templates.py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    packages = module._remote_packages()

    assert "lightgbm>=4.0" in packages
    assert "xgboost>=2.0" in packages
    assert "catboost>=1.2" in packages
