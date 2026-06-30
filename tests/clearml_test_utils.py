from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


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
    try:
        spec.loader.exec_module(module)
    finally:
        if remove_module_dir:
            sys.path.remove(module_dir)
    return module


def load_clearml_adapter_module():
    return load_module("clearml/adapter.py", "ml_platform_clearml_adapter_test")


def load_clearml_params_module():
    return load_module("clearml/params.py", "ml_platform_clearml_params_test")


def load_clearml_templates_module():
    return load_module("clearml/templates.py", "ml_platform_clearml_templates_test")


def load_clearml_pipeline_plan_module():
    return load_module("clearml/pipeline_plan.py", "ml_platform_clearml_pipeline_plan_test")


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
