from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from typing import Any

from ml_platform_core.result import RunResult

Runner = Callable[[dict[str, Any]], RunResult]

# Keep this registry as strings so importing ml_platform_tabular does not import
# sklearn-heavy modules until a task is actually executed.
RUNNER_PATHS: dict[str, str] = {
    "tabular_train": "ml_platform_tabular.train:run_train",
    "tabular_eval": "ml_platform_tabular.evaluate:run_evaluate",
    "tabular_infer": "ml_platform_tabular.infer:run_infer",
    "tabular_pipeline": "ml_platform_tabular.pipeline:run_pipeline",
    "tabular_1d_output": "ml_platform_tabular.output_1d:run_output_1d",
}


def available_tasks() -> list[str]:
    return list(RUNNER_PATHS)


def get_runner(task_name: str) -> Runner:
    try:
        path = RUNNER_PATHS[task_name]
    except KeyError as exc:
        raise ValueError(f"Unknown task: {task_name}. Available: {available_tasks()}") from exc
    module_name, attr_name = path.split(":", 1)
    module = import_module(module_name)
    runner = getattr(module, attr_name)
    return runner


def run_task(cfg: dict[str, Any]) -> RunResult:
    task_name = cfg.get("task")
    if not isinstance(task_name, str) or not task_name:
        raise ValueError("Config key 'task' is required.")
    return get_runner(task_name)(cfg)
