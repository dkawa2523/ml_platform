from ml_platform_core.config import load_run_config

from clearml_test_utils import (
    load_clearml_pipeline_controller_module,
    load_clearml_templates_module,
)


def test_clearml_pipeline_run_metadata_replaces_template_run_type_tag():
    pipeline_controller = load_clearml_pipeline_controller_module()

    class FakeTask:
        def __init__(self):
            self.name = None
            self.tags = ["domain:tabular", "run_type:template", "user_facing:true"]

        def set_name(self, name):
            self.name = name

        def get_tags(self):
            return list(self.tags)

        def set_tags(self, tags):
            self.tags = list(tags)

    task = FakeTask()
    pipeline_controller._apply_pipeline_run_metadata(task, task_name="pipeline/tabular_train_pipeline/run")

    assert task.name == "pipeline/tabular_train_pipeline/run"
    assert "run_type:pipeline" in task.tags
    assert "run_type:template" not in task.tags
    assert "user_facing:true" in task.tags


def test_clearml_launch_targets_use_infer_stage_and_training_pipeline_drafts():
    templates = load_clearml_templates_module()
    assert [name for name, _, _ in templates.TEMPLATES] == [
        "tabular_infer_template",
        "tabular_stage_template",
        "tabular_train_pipeline_template",
    ]
    assert [name for name, _, _ in templates.TASK_TEMPLATES] == [
        "tabular_infer_template",
        "tabular_stage_template",
    ]
    assert [name for name, _, _ in templates.PIPELINE_TEMPLATES] == [
        "tabular_train_pipeline_template",
    ]
    assert templates.PIPELINE_TEMPLATES[0][1] == "config/tasks/tabular_pipeline.yaml"
    assert templates._entry_point("tabular_stage_template") == "clearml/app.py"
    assert templates._entry_point("tabular_train_pipeline_template") == "clearml/pipelines.py"
    assert templates.clearml_template_name("tabular_train_pipeline_template") == "template/tabular_train_pipeline"
    assert templates.clearml_template_name("tabular_infer_template") == "template/tabular_infer"
    assert templates.clearml_template_name("tabular_stage_template") == "internal/tabular_stage"
    assert templates._template_tags("tabular_train_pipeline_template") == [
        "domain:tabular",
        "run_type:template",
        "user_facing:true",
    ]
    assert templates._template_tags("tabular_stage_template") == [
        "domain:tabular",
        "run_type:template",
        "internal:true",
    ]


def test_clearml_infer_template_uses_remote_dataset_defaults():
    templates = load_clearml_templates_module()
    cfg = load_run_config("config/tasks/tabular_infer.yaml", "config/profiles/clearml-dev.yaml")

    params = templates._task_runtime_params("tabular_infer_template", cfg)

    assert params["Input/local_path"] == ""
    assert params["Input/clearml_dataset_id"] == "b7afaea9d7aa42f084fb4fc06b0d4d41"
    assert params["Input/dataset_file"] == "sample_train.csv"
    assert params["Model/source_type"] == "task_id"


def test_clearml_template_metadata_replaces_stale_role_tags():
    templates = load_clearml_templates_module()
    pipeline_controller = load_clearml_pipeline_controller_module()

    class FakeTask:
        def __init__(self):
            self.tags = ["domain:tabular", "run_type:task", "internal:true", "old:keep"]
            self.comment = None

        def get_tags(self):
            return list(self.tags)

        def set_tags(self, tags):
            self.tags = list(tags)

        def set_comment(self, comment):
            self.comment = comment

    infer = FakeTask()
    templates._apply_task_metadata(infer, "tabular_infer_template", "image:tag")
    assert "run_type:template" in infer.tags
    assert "user_facing:true" in infer.tags
    assert "run_type:task" not in infer.tags
    assert "internal:true" not in infer.tags
    assert "old:keep" in infer.tags

    pipeline = FakeTask()
    pipeline_controller._apply_pipeline_template_metadata(pipeline, "image:tag")
    assert "run_type:template" in pipeline.tags
    assert "user_facing:true" in pipeline.tags
    assert "run_type:task" not in pipeline.tags
    assert "internal:true" not in pipeline.tags
