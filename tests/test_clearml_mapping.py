import pytest

from ml_platform_core.config import load_run_config, load_yaml

from clearml_test_utils import (
    load_clearml_adapter_module,
    load_clearml_app_module,
    load_clearml_execution_module,
)


def test_clearml_mapping_shape():
    cfg = load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml")
    assert cfg["runtime"]["use_clearml"] is True
    assert cfg["task"] == "tabular_pipeline"
    assert "clearml" in cfg
    assert cfg["clearml"]["project_root"] == "MLPlatform/Dev"
    assert cfg["clearml"]["execution"]["image"] == "ml-platform-clearml-agent:dev"
    assert cfg["clearml"]["projects"] == {
        "templates": "MLPlatform/Dev/Templates/Tabular",
        "pipelines": "MLPlatform/Dev/Pipelines/Tabular",
        "preprocess": "MLPlatform/Dev/Runs/Tabular/Preprocess",
        "train": "MLPlatform/Dev/Runs/Tabular/Train",
        "ensemble": "MLPlatform/Dev/Runs/Tabular/Ensemble",
        "evaluate": "MLPlatform/Dev/Runs/Tabular/Evaluate",
        "infer": "MLPlatform/Dev/Runs/Tabular/Infer",
        "stages": "MLPlatform/Dev/Runs/Tabular/Stages",
        "tasks": "MLPlatform/Dev/Runs/Tabular/Tasks",
        "experiments": "MLPlatform/Dev/Experiments/Tabular",
    }


def test_clearml_project_layout_prefers_explicit_projects():
    adapter = load_clearml_adapter_module()

    assert adapter.clearml_projects(
        {
            "project_root": "Root",
            "projects": {
                "templates": "Custom/Templates",
                "pipelines": "Custom/Pipelines",
            },
        }
    ) == {
        "templates": "Custom/Templates",
        "pipelines": "Custom/Pipelines",
        "preprocess": "Root/Runs/Tabular/Preprocess",
        "train": "Root/Runs/Tabular/Train",
        "ensemble": "Root/Runs/Tabular/Ensemble",
        "evaluate": "Root/Runs/Tabular/Evaluate",
        "infer": "Root/Runs/Tabular/Infer",
        "stages": "Root/Runs/Tabular/Stages",
        "tasks": "Root/Runs/Tabular/Tasks",
        "experiments": "Root/Experiments/Tabular",
    }
    assert (
        adapter.clearml_projects(
            {
                "project_root": "Root",
                "projects": {
                    "stages": "Legacy/Stages",
                    "tasks": "Legacy/Tasks",
                },
            }
        )["train"]
        == "Legacy/Stages"
    )
    assert (
        adapter.clearml_projects(
            {
                "project_root": "Root",
                "projects": {
                    "stages": "Legacy/Stages",
                    "tasks": "Legacy/Tasks",
                },
            }
        )["infer"]
        == "Legacy/Tasks"
    )


def test_clearml_execution_is_applied_to_task():
    execution = load_clearml_execution_module()

    class FakeTask:
        def __init__(self):
            self.base_docker = None
            self.params = {}

        def set_base_docker(self, docker_image=None, **_kwargs):
            self.base_docker = docker_image

        def update_parameters(self, params):
            self.params.update(params)

    task = FakeTask()
    spec = execution.ExecutionSpec(
        repository="https://example.invalid/repo.git",
        commit="a" * 40,
        working_dir=".",
        image="registry/image:tag",
        python_binary="python3.11",
    )
    execution.apply_task_execution(task, spec)

    assert task.base_docker == "registry/image:tag"
    assert task.params == {
        "Execution/image": "registry/image:tag",
        "Execution/revision": "a" * 40,
        "Execution/python": "python3.11",
    }


def test_clearml_execution_profile_resolves_head_to_immutable_commit():
    execution = load_clearml_execution_module()

    spec = execution.load_execution_spec(load_yaml("config/profiles/clearml-dev.yaml"))

    assert spec.repository == "https://github.com/dkawa2523/ml_platform.git"
    assert len(spec.commit) == 40
    assert spec.image == "ml-platform-clearml-agent:dev"
    assert spec.python_binary == "python3.11"


def test_clearml_prod_execution_image_comes_from_environment(monkeypatch):
    execution = load_clearml_execution_module()
    image = "registry.example/ml-platform/clearml-agent@sha256:" + "a" * 64
    monkeypatch.setenv("ML_PLATFORM_CLEARML_IMAGE", image)

    spec = execution.load_execution_spec(load_yaml("config/profiles/clearml-prod.yaml"))

    assert spec.image == image


def test_clearml_prod_execution_image_is_explicitly_required(monkeypatch):
    execution = load_clearml_execution_module()
    monkeypatch.delenv("ML_PLATFORM_CLEARML_IMAGE", raising=False)

    with pytest.raises(ValueError, match="ML_PLATFORM_CLEARML_IMAGE"):
        execution.load_execution_spec(load_yaml("config/profiles/clearml-prod.yaml"))


def test_clearml_runtime_validation_checks_expected_sdk_contract():
    adapter = load_clearml_adapter_module()
    FakeSdk = type("FakeSdk", (), {"__version__": "2.1.7", "Task": object, "StorageManager": object})
    FakeAutomation = type("FakeAutomation", (), {"PipelineController": object})

    adapter.import_clearml_sdk = lambda: FakeSdk
    adapter.import_clearml_automation = lambda: FakeAutomation
    adapter.validate_clearml_runtime()
    adapter.validate_clearml_runtime(require_automation=True)

    FakeSdk.__version__ = "2.0.0"
    with pytest.raises(adapter.ClearMLUnavailable, match="2.1"):
        adapter.validate_clearml_runtime()


def test_clearml_stage_names_are_validated():
    adapter = load_clearml_adapter_module()
    projects = {
        "preprocess": "Preprocess",
        "train": "Train",
        "ensemble": "Ensemble",
        "evaluate": "Evaluate",
    }

    assert adapter.clearml_stage_project(projects, "train_model") == "Train"
    assert adapter.stage_task_label("build_ensemble", ensemble_method="weighted") == "build_ensemble_weighted"
    with pytest.raises(ValueError, match="Unsupported tabular stage"):
        adapter.clearml_stage_project(projects, "unknown")


def test_clearml_app_routes_primary_tasks_to_named_projects():
    app = load_clearml_app_module()
    base_clearml = {
        "projects": {
            "templates": "Templates",
            "pipelines": "Pipelines",
            "preprocess": "Preprocess",
            "train": "Train",
            "ensemble": "Ensemble",
            "evaluate": "Evaluate",
            "infer": "Infer",
            "experiments": "Experiments",
        }
    }

    infer_project, infer_name, infer_tags, _ = app._initial_clearml_target(
        {"task": "tabular_infer", "run": {"name": "score_run"}, "clearml": base_clearml}
    )
    assert infer_project == "Infer"
    assert infer_name == "task/tabular_infer/score_run"
    assert infer_tags == ["domain:tabular", "run_type:task", "user_facing:true"]

    stage_project, stage_name, stage_tags, _ = app._initial_clearml_target(
        {
            "task": "tabular_stage",
            "run": {"name": "train_run", "stage": "train_model"},
            "model": {"name": "ridge"},
            "clearml": base_clearml,
        }
    )
    assert stage_project == "Train"
    assert stage_name == "stage/train_ridge/train_run"
    assert stage_tags == [
        "domain:tabular",
        "run_type:stage",
        "internal:true",
        "stage:train_model",
        "model:ridge",
    ]
    ensemble_project, ensemble_name, ensemble_tags, _ = app._initial_clearml_target(
        {
            "task": "tabular_stage",
            "run": {"name": "ensemble_run", "stage": "build_ensemble"},
            "model": {"ensemble": {"methods": ["weighted"]}},
            "clearml": base_clearml,
        }
    )
    assert ensemble_project == "Ensemble"
    assert ensemble_name == "stage/build_ensemble_weighted/ensemble_run"
    assert ensemble_tags == [
        "domain:tabular",
        "run_type:stage",
        "internal:true",
        "stage:build_ensemble",
        "ensemble:weighted",
    ]


def test_clearml_connect_params_uses_named_groups():
    adapter = load_clearml_adapter_module()

    class FakeTask:
        def __init__(self):
            self.calls = []

        def connect(self, values, name=None):
            self.calls.append((name, dict(values)))
            return values

    task = FakeTask()
    connected = adapter.ClearMLAdapter(task).connect_params(
        {
            "Run/task": "tabular_stage",
            "Input/local_path": "data/sample_train.csv",
            "Model/name": "ridge",
        }
    )

    assert connected == {
        "Run/task": "tabular_stage",
        "Input/local_path": "data/sample_train.csv",
        "Model/name": "ridge",
    }
    assert ("Run", {"task": "tabular_stage"}) in task.calls
    assert ("Input", {"local_path": "data/sample_train.csv"}) in task.calls
    assert ("Model", {"name": "ridge"}) in task.calls


def test_clearml_apply_metadata_can_move_runtime_task_project():
    adapter = load_clearml_adapter_module()

    class FakeTaskForMetadata:
        def __init__(self):
            self.project = None
            self.name = None
            self.tags = []
            self.comment = None

        def move_to_project(self, new_project_name=None, **_kwargs):
            self.project = new_project_name

        def set_name(self, name):
            self.name = name

        def add_tags(self, tags):
            self.tags.extend(tags)

        def set_comment(self, comment):
            self.comment = comment

    task = FakeTaskForMetadata()
    adapter.ClearMLAdapter(task).apply_metadata(
        project_name="Runs/Tabular/Train",
        task_name="stage/train_ridge/run",
        tags=["domain:tabular", "run_type:stage", "model:ridge"],
        comment="stage task",
    )

    assert task.project == "Runs/Tabular/Train"
    assert task.name == "stage/train_ridge/run"
    assert task.tags == ["domain:tabular", "run_type:stage", "model:ridge"]
    assert task.comment == "stage task"


def test_clearml_apply_metadata_can_replace_stale_runtime_tags():
    adapter = load_clearml_adapter_module()

    class FakeTaskForMetadata:
        def __init__(self):
            self.tags = ["domain:tabular", "run_type:stage", "stage:preprocess_features"]

        def set_tags(self, tags):
            self.tags = list(tags)

    task = FakeTaskForMetadata()
    adapter.ClearMLAdapter(task).apply_metadata(
        tags=["domain:tabular", "run_type:stage", "stage:evaluate_models", "internal:true"],
        replace_tags=True,
    )

    assert "stage:evaluate_models" in task.tags
    assert "stage:preprocess_features" not in task.tags
    assert task.tags == sorted({"domain:tabular", "run_type:stage", "stage:evaluate_models", "internal:true"})
