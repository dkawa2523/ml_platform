from pathlib import Path

import yaml
from ml_platform_clearml.template_spec import remote_packages


def test_execution_image_does_not_bake_repository_code():
    dockerfile = Path("deploy/base/Dockerfile").read_text(encoding="utf-8")

    assert "libgomp1" in dockerfile
    assert "COPY . ." not in dockerfile
    assert "pkgs/tabular" not in dockerfile


def test_agent_uses_isolated_task_environment():
    dockerfile = Path("deploy/base/Dockerfile").read_text(encoding="utf-8")
    manifests = "\n".join(path.read_text(encoding="utf-8") for path in Path("deploy").rglob("*.yaml"))

    assert "system_site_packages" not in dockerfile
    assert "system_site_packages" not in manifests


def test_agent_deployments_separate_controller_and_worker_queues():
    controller = yaml.safe_load(Path("deploy/base/controller.yaml").read_text(encoding="utf-8"))
    worker = yaml.safe_load(Path("deploy/base/worker.yaml").read_text(encoding="utf-8"))

    assert controller["metadata"]["name"] == "ml-platform-clearml-controller"
    assert worker["metadata"]["name"] == "ml-platform-clearml-worker"
    assert controller["spec"]["template"]["spec"]["containers"][0]["env"][0]["value"] == "controller"
    assert worker["spec"]["template"]["spec"]["containers"][0]["env"][0]["value"] == "default"


def test_local_compose_matches_profile_queue_split_without_persistent_agent_home():
    compose = yaml.safe_load(Path("deploy/local/compose.yaml").read_text(encoding="utf-8"))

    assert compose["services"]["controller"]["environment"]["CLEARML_AGENT_QUEUE"] == "controller"
    assert compose["services"]["worker"]["environment"]["CLEARML_AGENT_QUEUE"] == "default"
    assert "volumes" not in compose["services"]["controller"]
    assert "volumes" not in compose["services"]["worker"]


def test_profiles_define_environment_specific_execution_image_reference():
    dev_profile = Path("config/profiles/clearml-dev.yaml").read_text(encoding="utf-8")
    prod_profile = Path("config/profiles/clearml-prod.yaml").read_text(encoding="utf-8")

    assert "execution:" in dev_profile
    assert "image: ml-platform-clearml-agent:dev" in dev_profile
    assert "execution:" in prod_profile
    assert "image: ${ML_PLATFORM_CLEARML_IMAGE}" in prod_profile
    assert "python_binary: python3.11" in dev_profile
    assert "requirements_file: config/requirements/clearml-agent.lock" in dev_profile
    assert "revision: HEAD" in dev_profile


def test_gbm_packages_are_not_required_runtime_dependencies():
    requirements = Path("requirements.txt").read_text(encoding="utf-8").lower()

    assert "lightgbm" not in requirements
    assert "xgboost" not in requirements
    assert "catboost" not in requirements


def test_clearml_remote_packages_install_gbm_into_execution_venv():
    packages = remote_packages()

    assert "clearml==2.1.7" in packages
    assert "lightgbm==4.6.0" in packages
    assert any(package.startswith("xgboost==") for package in packages)
    assert "catboost==1.2.10" in packages
    assert all("==" in package for package in packages)
