from __future__ import annotations

from .runners import available_tasks, get_runner, run_task

TASK_NAMES = available_tasks()


__all__ = ["TASK_NAMES", "available_tasks", "get_runner", "run_task"]
