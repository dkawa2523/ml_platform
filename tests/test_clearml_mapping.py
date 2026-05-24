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
    }
    updated = adapter.apply_ui_params(cfg, connected)
    assert updated["data"]["local_path"] == "data/other.csv"
    assert updated["data"]["dataset_file"] == "train.csv"
    assert updated["data"]["target_column"] == "y"
    assert updated["run"]["seed"] == 7
    assert updated["model"]["artifact_path"] == "outputs/latest_train/model.joblib"
    assert updated["output"]["prediction_name"] == "scored.csv"


def test_clearml_ui_params_stay_in_four_groups():
    adapter = load_clearml_adapter_module()
    cfg = load_run_config("config/tasks/tabular_train.yaml", "config/profiles/clearml-dev.yaml")
    params = adapter.default_ui_params(cfg)

    assert "Input/dataset_file" in params
    assert {key.split("/", 1)[0] for key in params} <= {"Input", "Run", "Model", "Output"}
    assert not [key for key in params if key.startswith("Output/")]


def test_clearml_ui_params_are_task_specific():
    adapter = load_clearml_adapter_module()
    train = adapter.default_ui_params(load_run_config("config/tasks/tabular_train.yaml", "config/profiles/clearml-dev.yaml"))
    eval_cfg = adapter.default_ui_params(load_run_config("config/tasks/tabular_eval.yaml", "config/profiles/clearml-dev.yaml"))
    infer = adapter.default_ui_params(load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/clearml-dev.yaml"))
    pipeline = adapter.default_ui_params(load_run_config("config/tasks/tabular_pipeline.yaml", "config/profiles/clearml-dev.yaml"))

    assert {"Model/name", "Model/params", "Model/feature_preset"}.issubset(train)
    assert "Model/name" not in eval_cfg
    assert "Model/params" not in eval_cfg
    assert "Output/prediction_name" in infer
    assert set(pipeline) == {"Run/task", "Run/name", "Run/seed"}


def test_clearml_templates_are_fixed_to_four_mvp_templates():
    templates = load_clearml_templates_module()
    assert [name for name, _, _ in templates.TEMPLATES] == [
        "tabular_train_template",
        "tabular_eval_template",
        "tabular_infer_template",
        "tabular_pipeline_template",
    ]
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
