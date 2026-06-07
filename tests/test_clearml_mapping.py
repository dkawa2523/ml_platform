import importlib.util
from pathlib import Path

import pytest

from ml_platform_core.config import load_run_config


def load_module(path: str, name: str):
    module_path = Path(path).resolve()
    spec = importlib.util.spec_from_file_location(name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_clearml_adapter_module():
    return load_module("clearml/adapter.py", "ml_platform_clearml_adapter_test")


def load_clearml_templates_module():
    return load_module("clearml/templates.py", "ml_platform_clearml_templates_test")


def load_clearml_pipelines_module():
    return load_module("clearml/pipelines.py", "ml_platform_clearml_pipelines_test")


def write_compat_pipeline_config(tmp_path: Path) -> Path:
    path = tmp_path / "compat_pipeline.yaml"
    path.write_text(
        "\n".join(
            [
                "task: tabular_pipeline",
                "run:",
                "  name: tabular_pipeline",
                "  seed: 42",
                "  pipeline_mode: auto",
                "train:",
                "  task_config: config/tasks/tabular_train.yaml",
                "eval:",
                "  task_config: config/tasks/tabular_eval.yaml",
                "infer:",
                "  task_config: config/tasks/tabular_infer.yaml",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_clearml_mapping_shape():
    cfg = load_run_config("config/tasks/tabular_train.yaml", "config/profiles/clearml-dev.yaml")
    assert cfg["runtime"]["use_clearml"] is True
    assert cfg["task"] == "tabular_train"
    assert "clearml" in cfg
    assert cfg["clearml"]["project_root"] == "MLPlatform/Dev"


def test_clearml_ui_params_are_applied_to_nested_config():
    adapter = load_clearml_adapter_module()
    cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/clearml-dev.yaml")
    connected = {
        "Input/local_path": "data/other.csv",
        "Input/dataset_file": "train.csv",
        "Input/target_column": "y",
        "Run/seed": 7,
        "Model/source_type": "task_id",
        "Model/source_task_id": "train-task-id",
        "Model/model_selector": "best",
        "Model/model_artifact_url": "s3://bucket/model.joblib",
        "Model/clearml_model_id": "model-id",
        "Model/local_model_path": "outputs/latest_training_pipeline",
        "Model/artifact_path": "outputs/latest_train/model.joblib",
        "Model/info_path": "outputs/latest_train/model_info.json",
        "Output/prediction_name": "scored.csv",
        "Output/chunk_size": 500,
    }
    updated = adapter.apply_ui_params(cfg, connected)
    assert updated["data"]["local_path"] == "data/other.csv"
    assert updated["data"]["dataset_file"] == "train.csv"
    assert updated["data"]["target_column"] == "y"
    assert updated["run"]["seed"] == 7
    assert updated["model"]["source_type"] == "task_id"
    assert updated["model"]["source_task_id"] == "train-task-id"
    assert updated["model"]["model_selector"] == "best"
    assert updated["model"]["model_artifact_url"] == "s3://bucket/model.joblib"
    assert updated["model"]["clearml_model_id"] == "model-id"
    assert updated["model"]["local_model_path"] == "outputs/latest_training_pipeline"
    assert updated["model"]["artifact_path"] == "outputs/latest_train/model.joblib"
    assert updated["model"]["info_path"] == "outputs/latest_train/model_info.json"
    assert updated["output"]["prediction_name"] == "scored.csv"
    assert updated["output"]["chunk_size"] == 500


def test_clearml_ui_params_stay_in_four_groups():
    adapter = load_clearml_adapter_module()
    cfg = load_run_config("config/tasks/tabular_train.yaml", "config/profiles/clearml-dev.yaml")
    params = adapter.default_ui_params(cfg)

    assert "Input/dataset_file" in params
    assert params["Model/params"] == '{"alpha": 1.0}'
    assert params["Model/candidates"] == "[]"
    assert params["Model/selection_metric"] == "rmse"
    assert params["Model/search_enabled"] is False
    assert params["Model/search_method"] == "grid"
    assert params["Model/search_space"] == "{}"
    assert params["Model/max_trials"] == 20
    assert params["Model/ensemble_enabled"] is False
    assert params["Model/ensemble_method"] == "mean_topk"
    assert params["Model/ensemble_top_k"] == 3
    assert {key.split("/", 1)[0] for key in params} <= {"Input", "Run", "Model", "Output"}
    assert not [key for key in params if key.startswith("Output/")]


def test_clearml_flat_ensemble_params_apply_to_nested_config():
    adapter = load_clearml_adapter_module()
    cfg = load_run_config("config/tasks/tabular_train.yaml", "config/profiles/clearml-dev.yaml")

    updated = adapter.apply_ui_params(
        cfg,
        {
            "Model/ensemble_enabled": True,
            "Model/ensemble_method": "weighted",
            "Model/ensemble_top_k": 2,
        },
    )

    assert updated["model"]["ensemble"] == {"enabled": True, "method": "weighted", "top_k": 2}


def test_clearml_flat_search_params_apply_to_nested_config():
    adapter = load_clearml_adapter_module()
    cfg = load_run_config("config/tasks/tabular_train.yaml", "config/profiles/clearml-dev.yaml")

    updated = adapter.apply_ui_params(
        cfg,
        {
            "Model/search_enabled": True,
            "Model/search_method": "random",
            "Model/search_space": '{"alpha":[0.1,1.0]}',
            "Model/max_trials": 2,
        },
    )

    assert updated["model"]["search"] == {
        "enabled": True,
        "method": "random",
        "search_space": {"alpha": [0.1, 1.0]},
        "max_trials": 2,
        "retrain_best": True,
    }


def test_clearml_ui_params_are_task_specific():
    adapter = load_clearml_adapter_module()
    train = adapter.default_ui_params(load_run_config("config/tasks/tabular_train.yaml", "config/profiles/clearml-dev.yaml"))
    eval_cfg = adapter.default_ui_params(load_run_config("config/tasks/tabular_eval.yaml", "config/profiles/clearml-dev.yaml"))
    infer = adapter.default_ui_params(load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/clearml-dev.yaml"))
    pipeline = adapter.default_ui_params(load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml"))
    stage = adapter.default_ui_params(load_run_config("config/tasks/tabular_stage.yaml", "config/profiles/clearml-dev.yaml"))

    assert {
        "Model/name",
        "Model/params",
        "Model/candidates",
        "Model/selection_metric",
        "Model/search_enabled",
        "Model/search_method",
        "Model/search_space",
        "Model/max_trials",
        "Model/ensemble_enabled",
        "Model/ensemble_method",
        "Model/ensemble_top_k",
        "Model/feature_preset",
    }.issubset(train)
    assert "Model/name" not in eval_cfg
    assert "Model/params" not in eval_cfg
    assert "Output/prediction_name" in infer
    assert "Output/chunk_size" in infer
    assert {
        "Model/source_type",
        "Model/source_task_id",
        "Model/model_selector",
        "Model/model_artifact_url",
        "Model/clearml_model_id",
        "Model/local_model_path",
        "Model/artifact_path",
        "Model/info_path",
    }.issubset(infer)
    assert {
        "Run/task",
        "Run/name",
        "Run/seed",
        "Input/local_path",
        "Input/target_column",
        "Model/candidates",
        "Model/search_enabled",
        "Model/search_method",
        "Model/search_space",
        "Model/max_trials",
        "Model/ensemble_enabled",
        "Model/ensemble_method",
        "Model/ensemble_top_k",
    }.issubset(pipeline)
    assert "Output/prediction_name" not in pipeline
    assert "Run/stage" in stage
    assert "Input/preprocess_bundle" in stage
    assert "Input/model_refs" in stage


def test_clearml_pipeline_template_has_minimal_training_pipeline_overrides():
    pipelines = load_clearml_pipelines_module()
    params = pipelines.pipeline_ui_params("config/tasks/tabular_train_pipeline.yaml", "config/profiles/clearml-dev.yaml")

    assert {key.split("/", 1)[0] for key in params} <= {"Input", "Run", "Model", "Output"}
    assert {
        "Run/task",
        "Run/name",
        "Input/clearml_dataset_id",
        "Input/local_path",
        "Input/dataset_file",
        "Input/target_column",
        "Input/id_columns",
    }.issubset(params)
    assert {
        "Model/params",
        "Model/candidates",
        "Model/selection_metric",
        "Model/search_enabled",
        "Model/search_method",
        "Model/search_space",
        "Model/max_trials",
        "Model/ensemble_enabled",
        "Model/ensemble_method",
        "Model/ensemble_top_k",
        "Model/feature_preset",
    }.issubset(params)
    assert "Run/pipeline_mode" not in params
    assert not [key for key in params if key.startswith("Output/")]


def test_clearml_pipeline_new_run_args_are_mapped_to_ui_params():
    pipelines = load_clearml_pipelines_module()
    defaults = pipelines.pipeline_ui_params("config/tasks/tabular_train_pipeline.yaml", "config/profiles/clearml-dev.yaml")
    task_params = {
        "Model/candidates": '["linear"]',
        "Args/Model/candidates": '["linear","ridge"]',
        "Args/Input/clearml_dataset_id": "dataset-id",
    }

    args_params = pipelines.pipeline_arg_params(defaults)
    connected = pipelines.pipeline_params_from_task(defaults, task_params)

    assert args_params["Args/Model/candidates"] == defaults["Model/candidates"]
    assert connected["Model/candidates"] == '["linear","ridge"]'
    assert connected["Input/clearml_dataset_id"] == "dataset-id"


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
            "Run/task": "tabular_train",
            "Input/local_path": "data/sample_train.csv",
            "Model/name": "ridge",
        }
    )

    assert connected == {
        "Run/task": "tabular_train",
        "Input/local_path": "data/sample_train.csv",
        "Model/name": "ridge",
    }
    assert ("Run", {"task": "tabular_train"}) in task.calls
    assert ("Input", {"local_path": "data/sample_train.csv"}) in task.calls
    assert ("Model", {"name": "ridge"}) in task.calls


class FakeArtifact:
    def __init__(self, url):
        self.url = url


class FakeTask:
    def __init__(self, task_id, name, *, artifacts=None, params=None, parent=None):
        self.id = task_id
        self.name = name
        self.artifacts = artifacts or {}
        self._params = params or {}
        self.parent = parent

    def get_parameters(self, cast=False):
        return dict(self._params)


def _install_fake_task_api(adapter, tasks):
    by_id = {task.id: task for task in tasks}

    class FakeTaskApi:
        @staticmethod
        def get_task(task_id=None, **_kwargs):
            return by_id[task_id]

        @staticmethod
        def get_tasks(task_filter=None, **_kwargs):
            parent = (task_filter or {}).get("parent")
            return [task for task in tasks if task.parent == parent]

    def fake_import(symbol):
        if symbol == "Task":
            return FakeTaskApi
        raise AssertionError(symbol)

    adapter.import_clearml_symbol = fake_import


def test_clearml_resolves_infer_source_from_pipeline_controller_best_task():
    adapter = load_clearml_adapter_module()
    tasks = [
        FakeTask("pipe", "tabular_train_pipeline_template"),
        FakeTask(
            "preprocess",
            "preprocess_features",
            artifacts={
                "feature_spec": FakeArtifact("feature_spec.json"),
                "preprocess_bundle": FakeArtifact("preprocess_bundle.joblib"),
            },
            params={"Run/stage": "preprocess_features"},
            parent="pipe",
        ),
        FakeTask(
            "eval",
            "evaluate_models",
            artifacts={
                "best_model": FakeArtifact("best_model.joblib"),
                "best_model_json": FakeArtifact("best_model.json"),
            },
            params={"Run/stage": "evaluate_models"},
            parent="pipe",
        ),
    ]
    _install_fake_task_api(adapter, tasks)
    resolver = adapter.ClearMLAdapter(task=None)
    resolver.resolve_artifact_path = lambda value: str(value)

    cfg = {"task": "tabular_infer", "model": {"source_type": "task_id", "source_task_id": "pipe", "model_selector": "best"}}
    resolved = resolver.resolve_infer_model_source(cfg)

    assert resolved["model"]["artifact_path"] == "best_model.joblib"
    assert resolved["model"]["info_path"] == "best_model.json"
    assert resolved["model"]["feature_spec_path"] == "feature_spec.json"
    assert resolved["model"]["preprocess_bundle_path"] == "preprocess_bundle.joblib"
    assert resolved["model"]["resolved_source_task_name"] == "evaluate_models"
    assert resolved["model"]["resolved_source_artifact"] == "best_model"


def test_clearml_resolves_infer_source_from_pipeline_controller_ensemble_task():
    adapter = load_clearml_adapter_module()
    tasks = [
        FakeTask("pipe", "tabular_train_full_ensemble_pipeline_template"),
        FakeTask(
            "build",
            "build_ensemble",
            artifacts={
                "model": FakeArtifact("ensemble.joblib"),
                "model_info": FakeArtifact("ensemble_model_info.json"),
                "ensemble_info": FakeArtifact("ensemble_info.json"),
            },
            params={"Run/stage": "build_ensemble"},
            parent="pipe",
        ),
    ]
    _install_fake_task_api(adapter, tasks)
    resolver = adapter.ClearMLAdapter(task=None)
    resolver.resolve_artifact_path = lambda value: str(value)

    cfg = {"task": "tabular_infer", "model": {"source_type": "task_id", "source_task_id": "pipe", "model_selector": "ensemble"}}
    resolved = resolver.resolve_infer_model_source(cfg)

    assert resolved["model"]["artifact_path"] == "ensemble.joblib"
    assert resolved["model"]["info_path"] == "ensemble_model_info.json"
    assert resolved["model"]["resolved_source_task_name"] == "build_ensemble"


def test_clearml_resolves_infer_source_from_direct_train_stage_task():
    adapter = load_clearml_adapter_module()
    tasks = [
        FakeTask(
            "train-linear",
            "train_linear",
            artifacts={"model": FakeArtifact("linear.joblib"), "model_info": FakeArtifact("linear_model_info.json")},
            params={"Run/stage": "train_model", "Model/name": "linear"},
        )
    ]
    _install_fake_task_api(adapter, tasks)
    resolver = adapter.ClearMLAdapter(task=None)
    resolver.resolve_artifact_path = lambda value: str(value)

    cfg = {
        "task": "tabular_infer",
        "model": {"source_type": "task_id", "source_task_id": "train-linear", "model_selector": "linear"},
    }
    resolved = resolver.resolve_infer_model_source(cfg)

    assert resolved["model"]["artifact_path"] == "linear.joblib"
    assert resolved["model"]["info_path"] == "linear_model_info.json"


def test_clearml_infer_source_resolution_reports_available_tasks_on_failure():
    adapter = load_clearml_adapter_module()
    tasks = [FakeTask("pipe", "pipeline"), FakeTask("train-ridge", "train_ridge", params={"Run/stage": "train_model"}, parent="pipe")]
    _install_fake_task_api(adapter, tasks)
    resolver = adapter.ClearMLAdapter(task=None)

    cfg = {"task": "tabular_infer", "model": {"source_type": "task_id", "source_task_id": "pipe", "model_selector": "linear"}}
    with pytest.raises(ValueError, match="Discovered:"):
        resolver.resolve_infer_model_source(cfg)


def test_clearml_infer_source_resolution_supports_clearml_model_id_minimal():
    adapter = load_clearml_adapter_module()

    class FakeModel:
        def __init__(self, model_id):
            self.model_id = model_id

        def get_local_copy(self):
            return "clearml_model.joblib"

    adapter.import_clearml_symbol = lambda symbol: FakeModel if symbol == "Model" else None
    resolver = adapter.ClearMLAdapter(task=None)

    cfg = {"task": "tabular_infer", "model": {"source_type": "clearml_model_id", "clearml_model_id": "model-id"}}
    resolved = resolver.resolve_infer_model_source(cfg)

    assert resolved["model"]["artifact_path"] == "clearml_model.joblib"


def test_clearml_launch_targets_use_infer_stage_and_training_pipeline_drafts():
    templates = load_clearml_templates_module()
    assert [name for name, _, _ in templates.TEMPLATES] == [
        "tabular_infer_template",
        "tabular_stage_template",
        "tabular_train_pipeline_template",
        "tabular_train_full_pipeline_template",
        "tabular_train_full_ensemble_pipeline_template",
    ]
    assert [name for name, _, _ in templates.TASK_TEMPLATES] == [
        "tabular_infer_template",
        "tabular_stage_template",
    ]
    assert [name for name, _, _ in templates.PIPELINE_TEMPLATES] == [
        "tabular_train_pipeline_template",
        "tabular_train_full_pipeline_template",
        "tabular_train_full_ensemble_pipeline_template",
    ]
    assert templates.LEGACY_PIPELINE_TEMPLATE[0] == "tabular_pipeline_template"
    assert templates._entry_point("tabular_stage_template") == "clearml/app.py"
    assert templates._entry_point("tabular_train_pipeline_template") == "clearml/pipelines.py"


def test_clearml_training_pipeline_plan_is_stage_graph():
    pipelines = load_clearml_pipelines_module()
    plan = pipelines.build_pipeline_plan("config/tasks/tabular_train_pipeline.yaml", "config/profiles/clearml-dev.yaml")

    assert plan["kind"] == "training"
    assert [step["name"] for step in plan["steps"]] == [
        "preprocess_features",
        "train_linear",
        "train_ridge",
        "train_random_forest",
        "train_gradient_boosting",
        "evaluate_models",
    ]
    assert all(step["base_task_name"] == "tabular_stage_template" for step in plan["steps"])
    assert plan["steps"][1]["parents"] == ["preprocess_features"]
    assert plan["steps"][-1]["parents"] == [
        "train_linear",
        "train_ridge",
        "train_random_forest",
        "train_gradient_boosting",
    ]
    assert plan["steps"][1]["parameter_override"]["Run/stage"] == "train_model"
    assert plan["steps"][-1]["parameter_override"]["Run/stage"] == "evaluate_models"
    assert "${train_linear.artifacts.model.url}" in plan["steps"][-1]["parameter_override"]["Input/model_refs"]


def test_clearml_full_ensemble_pipeline_plan_has_ensemble_stage_and_refs():
    pipelines = load_clearml_pipelines_module()
    plan = pipelines.build_pipeline_plan(
        "config/tasks/tabular_train_full_ensemble_pipeline.yaml",
        "config/profiles/clearml-dev.yaml",
    )

    names = [step["name"] for step in plan["steps"]]
    assert "build_ensemble" in names
    assert names[-1] == "evaluate_models"
    assert set(plan["candidate_models"]) == {
        "linear",
        "ridge",
        "random_forest",
        "gradient_boosting",
        "lasso",
        "elasticnet",
        "extra_trees",
        "knn",
        "svr",
        "mlp",
    }
    build = next(step for step in plan["steps"] if step["name"] == "build_ensemble")
    evaluate = plan["steps"][-1]
    assert build["parents"] == [name for name in names if name.startswith("train_")]
    assert "build_ensemble" in evaluate["parents"]
    assert "${train_ridge.artifacts.metrics.url}" in build["parameter_override"]["Input/model_refs"]
    assert "${build_ensemble.artifacts.model.url}" in evaluate["parameter_override"]["Input/ensemble_ref"]


def test_clearml_optimization_pipeline_plan_is_stage_graph():
    pipelines = load_clearml_pipelines_module()
    plan = pipelines.build_pipeline_plan(
        "config/tasks/tabular_train_pipeline.yaml",
        "config/profiles/clearml-dev.yaml",
        ui_params={
            "Model/params": "{}",
            "Model/candidates": "[]",
            "Model/search_enabled": True,
            "Model/search_method": "grid",
            "Model/search_space": '{"alpha":[0.1,1.0]}',
            "Model/max_trials": 2,
            "Model/ensemble_enabled": False,
        },
    )

    assert plan["kind"] == "optimization"
    assert plan["pipeline_mode"] == "optimization"
    assert [step["name"] for step in plan["steps"]] == [
        "preprocess_features",
        "search_trials",
        "retrain_best",
        "evaluate_best",
    ]
    assert all(step["base_task_name"] == "tabular_stage_template" for step in plan["steps"])
    assert plan["steps"][1]["parents"] == ["preprocess_features"]
    assert plan["steps"][2]["parents"] == ["search_trials"]
    assert plan["steps"][3]["parents"] == ["retrain_best"]
    search = plan["steps"][1]
    retrain = plan["steps"][2]
    evaluate = plan["steps"][3]
    assert search["parameter_override"]["Run/stage"] == "search_trials"
    assert search["parameter_override"]["Model/search_enabled"] is True
    assert search["parameter_override"]["Model/search_space"] == '{"alpha": [0.1, 1.0]}'
    assert retrain["parameter_override"]["Input/best_params"] == "${search_trials.artifacts.best_params.url}"
    assert evaluate["parameter_override"]["Input/model"] == "${retrain_best.artifacts.model.url}"
    assert evaluate["parameter_override"]["Input/optimization_summary"] == "${search_trials.artifacts.optimization_summary.url}"


def test_clearml_optimization_pipeline_plan_rejects_search_and_ensemble():
    pipelines = load_clearml_pipelines_module()

    with pytest.raises(ValueError, match="cannot be combined"):
        pipelines.build_pipeline_plan(
            "config/tasks/tabular_train_pipeline.yaml",
            "config/profiles/clearml-dev.yaml",
            ui_params={
                "Model/search_enabled": True,
                "Model/search_space": '{"alpha":[1.0]}',
                "Model/ensemble_enabled": True,
            },
        )


def test_clearml_compatibility_full_run_plan_is_three_step_dag(tmp_path):
    pipelines = load_clearml_pipelines_module()
    task_path = write_compat_pipeline_config(tmp_path)
    plan = pipelines.build_pipeline_plan(task_path, "config/profiles/clearml-dev.yaml")

    assert [step["name"] for step in plan["steps"]] == ["train", "eval", "infer"]
    assert plan["pipeline_mode"] == "single"
    assert plan["steps"][0]["parents"] == []
    assert plan["steps"][1]["parents"] == ["train"]
    assert plan["steps"][2]["parents"] == ["eval"]
    assert plan["steps"][1]["parameter_override"]["Model/artifact_path"] == "${train.artifacts.model.url}"
    assert plan["steps"][2]["parameter_override"]["Model/artifact_path"] == "${train.artifacts.model.url}"


def test_clearml_training_pipeline_plan_applies_dataset_and_model_overrides():
    pipelines = load_clearml_pipelines_module()
    plan = pipelines.build_pipeline_plan(
        "config/tasks/tabular_train_pipeline.yaml",
        "config/profiles/clearml-dev.yaml",
        ui_params={
            "Input/clearml_dataset_id": "dataset-id",
            "Input/dataset_file": "train.csv",
            "Input/target_column": "target",
            "Input/id_columns": ["id"],
            "Model/params": "{}",
            "Model/candidates": '["linear","ridge"]',
            "Model/selection_metric": "rmse",
            "Model/ensemble_enabled": True,
            "Model/ensemble_method": "mean_topk",
            "Model/ensemble_top_k": 2,
            "Model/feature_preset": "basic",
        },
    )

    assert [step["name"] for step in plan["steps"]] == [
        "preprocess_features",
        "train_linear",
        "train_ridge",
        "build_ensemble",
        "evaluate_models",
    ]
    preprocess = plan["steps"][0]
    train_linear = plan["steps"][1]
    build = plan["steps"][3]
    assert preprocess["parameter_override"]["Input/clearml_dataset_id"] == "dataset-id"
    assert preprocess["parameter_override"]["Input/dataset_file"] == "train.csv"
    assert preprocess["parameter_override"]["Input/target_column"] == "target"
    assert preprocess["parameter_override"]["Input/id_columns"] == ["id"]
    assert train_linear["parameter_override"]["Model/name"] == "linear"
    assert train_linear["parameter_override"]["Model/params"] == "{}"
    assert train_linear["parameter_override"]["Model/selection_metric"] == "rmse"
    assert train_linear["parameter_override"]["Input/preprocess_bundle"] == "${preprocess_features.artifacts.preprocess_bundle.url}"
    assert build["parameter_override"]["Model/ensemble_enabled"] is True
    assert build["parameter_override"]["Model/ensemble_method"] == "mean_topk"
    assert build["parameter_override"]["Model/ensemble_top_k"] == 2


def test_clearml_compatibility_pipeline_rejects_search_and_ensemble_combo(tmp_path):
    pipelines = load_clearml_pipelines_module()
    task_path = write_compat_pipeline_config(tmp_path)

    with pytest.raises(ValueError, match="cannot combine|cannot be combined"):
        pipelines.build_pipeline_plan(
            task_path,
            "config/profiles/clearml-dev.yaml",
            ui_params={
                "Run/pipeline_mode": "auto",
                "Model/candidates": '["linear","ridge"]',
                "Model/search_enabled": True,
                "Model/search_space": '{"alpha":[1.0]}',
                "Model/ensemble_enabled": True,
            },
        )
