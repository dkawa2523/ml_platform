from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace


def load_module(path: str, name: str):
    module_path = Path(path).resolve()
    module_dir = str(module_path.parent)
    remove_module_dir = False
    if module_path.parent.name == "clearml" and module_dir not in sys.path:
        sys.path.insert(0, module_dir)
        remove_module_dir = True
    spec = importlib.util.spec_from_file_location(name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if remove_module_dir:
            sys.path.remove(module_dir)
    return module


def load_clearml_adapter_module():
    return load_module("clearml/adapter.py", "ml_platform_clearml_adapter_test")


def load_clearml_params_module():
    bindings = load_module("clearml/param_bindings.py", "ml_platform_clearml_param_bindings_test")
    defaults = load_module("clearml/param_defaults.py", "ml_platform_clearml_param_defaults_test")
    apply = load_module("clearml/param_apply.py", "ml_platform_clearml_param_apply_test")
    transport = load_module("clearml/param_transport.py", "ml_platform_clearml_param_transport_test")
    return SimpleNamespace(
        apply_connected_params_to_config=apply.apply_connected_params_to_config,
        bindings_for_config=bindings.bindings_for_config,
        build_default_connected_params=defaults.build_default_connected_params,
        coerce_connected_params=transport.coerce_connected_params,
        group_connected_params=transport.group_connected_params,
        normalize_clearml_param_value=transport.normalize_clearml_param_value,
        unique_specs=bindings._unique_specs,
    )


def load_clearml_templates_module():
    return load_module("clearml/templates.py", "ml_platform_clearml_templates_test")


def load_clearml_execution_module():
    return load_module("clearml/execution.py", "ml_platform_clearml_execution_test")


def load_clearml_pipeline_plan_module():
    return load_module("clearml/pipeline_plan.py", "ml_platform_clearml_pipeline_plan_test")


def load_clearml_pipeline_params_module():
    return load_module("clearml/pipeline_params.py", "ml_platform_clearml_pipeline_params_test")


def load_clearml_pipeline_steps_module():
    return load_module("clearml/pipeline_steps.py", "ml_platform_clearml_pipeline_steps_test")


def load_clearml_pipeline_controller_module():
    return load_module("clearml/pipeline_controller.py", "ml_platform_clearml_pipeline_controller_test")


def load_clearml_app_module():
    return load_module("clearml/app.py", "ml_platform_clearml_app_test")


def load_clearml_reports_module():
    return load_module("clearml/reports.py", "ml_platform_clearml_reports_test")


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
