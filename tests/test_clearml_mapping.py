import importlib.util
from pathlib import Path

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
        "Model/artifact_path": "outputs/latest_train/model.joblib",
        "Output/prediction_name": "scored.csv",
        "Output/chunk_size": 500,
    }
    updated = adapter.apply_ui_params(cfg, connected)
    assert updated["data"]["local_path"] == "data/other.csv"
    assert updated["data"]["dataset_file"] == "train.csv"
    assert updated["data"]["target_column"] == "y"
    assert updated["run"]["seed"] == 7
    assert updated["model"]["artifact_path"] == "outputs/latest_train/model.joblib"
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
    assert set(pipeline) == {"Run/task", "Run/name", "Run/seed"}


def test_clearml_pipeline_template_has_minimal_pipeline_overrides():
    pipelines = load_clearml_pipelines_module()
    params = pipelines.pipeline_ui_params("config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml")

    assert {key.split("/", 1)[0] for key in params} <= {"Input", "Run", "Model", "Output"}
    assert {"Input/clearml_dataset_id", "Input/train_dataset_file", "Input/eval_dataset_file", "Input/infer_dataset_file"}.issubset(params)
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
    }.issubset(params)


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


def test_clearml_launch_targets_are_fixed_to_three_tasks_and_one_pipeline_draft():
    templates = load_clearml_templates_module()
    assert [name for name, _, _ in templates.TEMPLATES] == [
        "tabular_train_template",
        "tabular_eval_template",
        "tabular_infer_template",
        "tabular_pipeline_template",
    ]
    assert [name for name, _, _ in templates.TASK_TEMPLATES] == [
        "tabular_train_template",
        "tabular_eval_template",
        "tabular_infer_template",
    ]
    assert templates.PIPELINE_TEMPLATE[0] == "tabular_pipeline_template"
    assert templates.PIPELINE_TEMPLATE[2] == "pipeline"
    assert templates._entry_point("tabular_train_template") == "clearml/app.py"
    assert templates._entry_point("tabular_pipeline_template") == "clearml/pipelines.py"


def test_clearml_pipeline_plan_is_fixed_three_step_dag():
    pipelines = load_clearml_pipelines_module()
    plan = pipelines.build_pipeline_plan("config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml")

    assert [step["name"] for step in plan["steps"]] == ["train", "eval", "infer"]
    assert plan["steps"][0]["parents"] == []
    assert plan["steps"][1]["parents"] == ["train"]
    assert plan["steps"][2]["parents"] == ["eval"]
    assert plan["steps"][1]["parameter_override"]["Model/artifact_path"] == "${train.artifacts.model.url}"
    assert plan["steps"][2]["parameter_override"]["Model/artifact_path"] == "${train.artifacts.model.url}"


def test_clearml_pipeline_plan_applies_dataset_and_model_overrides():
    pipelines = load_clearml_pipelines_module()
    plan = pipelines.build_pipeline_plan(
        "config/tasks/tabular_pipeline.yaml",
        "config/profiles/clearml-dev.yaml",
        ui_params={
            "Input/clearml_dataset_id": "dataset-id",
            "Input/train_dataset_file": "train.csv",
            "Input/eval_dataset_file": "eval.csv",
            "Input/infer_dataset_file": "infer.csv",
            "Model/name": "linear",
            "Model/params": "{}",
            "Model/candidates": '["linear","ridge"]',
            "Model/selection_metric": "rmse",
            "Model/search_enabled": True,
            "Model/search_method": "grid",
            "Model/search_space": '{"ridge":{"alpha":[0.1,1.0]}}',
            "Model/max_trials": 3,
            "Model/ensemble_enabled": True,
            "Model/ensemble_method": "mean_topk",
            "Model/ensemble_top_k": 2,
            "Model/feature_preset": "basic",
        },
    )

    train, eval_step, infer = plan["steps"]
    assert train["parameter_override"]["Input/clearml_dataset_id"] == "dataset-id"
    assert train["parameter_override"]["Input/dataset_file"] == "train.csv"
    assert train["parameter_override"]["Model/name"] == "linear"
    assert train["parameter_override"]["Model/params"] == "{}"
    assert train["parameter_override"]["Model/candidates"] == '["linear", "ridge"]'
    assert train["parameter_override"]["Model/selection_metric"] == "rmse"
    assert train["parameter_override"]["Model/search_enabled"] is True
    assert train["parameter_override"]["Model/search_method"] == "grid"
    assert train["parameter_override"]["Model/search_space"] == '{"ridge":{"alpha":[0.1,1.0]}}'
    assert train["parameter_override"]["Model/max_trials"] == 3
    assert train["parameter_override"]["Model/ensemble_enabled"] is True
    assert train["parameter_override"]["Model/ensemble_method"] == "mean_topk"
    assert train["parameter_override"]["Model/ensemble_top_k"] == 2
    assert eval_step["parameter_override"]["Input/dataset_file"] == "eval.csv"
    assert infer["parameter_override"]["Input/dataset_file"] == "infer.csv"
