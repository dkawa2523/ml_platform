from __future__ import annotations

import importlib
from types import SimpleNamespace


def _clearml_module(name: str):
    return importlib.import_module(f"ml_platform_clearml.{name}")


def load_clearml_adapter_module():
    return _clearml_module("adapter")


def load_clearml_params_module():
    bindings = _clearml_module("param_bindings")
    defaults = _clearml_module("param_defaults")
    apply = _clearml_module("param_apply")
    transport = _clearml_module("param_transport")
    return SimpleNamespace(
        apply_connected_params_to_config=apply.apply_connected_params_to_config,
        bindings_for_config=bindings.bindings_for_config,
        build_default_connected_params=defaults.build_default_connected_params,
        coerce_connected_params=transport.coerce_connected_params,
        group_connected_params=transport.group_connected_params,
        normalize_clearml_param_value=transport.normalize_clearml_param_value,
        unique_specs=bindings._unique_specs,
    )


def load_clearml_template_spec_module():
    return _clearml_module("template_spec")


def load_clearml_execution_module():
    return _clearml_module("execution")


def load_clearml_pipeline_plan_module():
    return _clearml_module("pipeline_plan")


def load_clearml_pipeline_params_module():
    return _clearml_module("pipeline_params")


def load_clearml_pipeline_steps_module():
    return _clearml_module("pipeline_steps")


def load_clearml_pipeline_controller_module():
    return _clearml_module("pipeline_controller")


def load_clearml_app_module():
    return _clearml_module("app")


def load_clearml_reports_module():
    return _clearml_module("reports")


class FakeArtifact:
    def __init__(self, url):
        self.url = url


class FakeTask:
    def __init__(
        self,
        task_id,
        name,
        *,
        artifacts=None,
        params=None,
        parent=None,
        project="MLPlatform/Dev/Runs/Tabular/Evaluate",
        tags=None,
        status="completed",
    ):
        self.id = task_id
        self.name = name
        self.artifacts = artifacts or {}
        self._params = params or {}
        self.parent = parent
        self.project = project
        self.tags = tags or ["domain:tabular", "run_type:stage"]
        self.status = status

    def get_parameters(self, cast=False):
        return dict(self._params)

    def get_project_name(self):
        return self.project

    def get_tags(self):
        return list(self.tags)


def install_fake_task_api(adapter, tasks):
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
