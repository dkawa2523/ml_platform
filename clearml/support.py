from __future__ import annotations

import shlex
from collections.abc import Mapping
from pathlib import Path
from typing import Any

MAX_REPORT_TABLE_ROWS = 1000


def existing_task_tags(task: Any) -> list[str]:
    get_tags = getattr(task, "get_tags", None)
    if not callable(get_tags):
        return []
    tags = get_tags()
    if not isinstance(tags, (list, tuple, set)):
        return []
    return [str(tag) for tag in tags]


def apply_task_tags(task: Any, tags: list[str], *, replace: bool = False) -> None:
    add_tags = getattr(task, "add_tags", None)
    set_tags = getattr(task, "set_tags", None)
    if replace and callable(set_tags):
        set_tags(sorted(set(tags)))
    elif callable(add_tags):
        add_tags(tags)
    elif callable(set_tags):
        set_tags(sorted(set(existing_task_tags(task)) | set(tags)))


def replace_task_tags(
    task: Any,
    tags: list[str],
    *,
    remove_tags: set[str] | None = None,
    remove_prefixes: tuple[str, ...] = (),
) -> None:
    set_tags = getattr(task, "set_tags", None)
    if callable(set_tags):
        kept = kept_task_tags(task, remove_tags=remove_tags, remove_prefixes=remove_prefixes)
        set_tags(sorted(set(kept) | set(tags)))
        return

    add_tags = getattr(task, "add_tags", None)
    if callable(add_tags):
        add_tags(tags)


def kept_task_tags(
    task: Any,
    *,
    remove_tags: set[str] | None = None,
    remove_prefixes: tuple[str, ...] = (),
) -> list[str]:
    remove_tags = remove_tags or set()
    return [
        tag
        for tag in existing_task_tags(task)
        if tag not in remove_tags and not any(tag.startswith(prefix) for prefix in remove_prefixes)
    ]


def set_task_comment(task: Any, comment: str) -> None:
    set_comment = getattr(task, "set_comment", None)
    if callable(set_comment):
        set_comment(comment)


def delete_task(task: Any) -> None:
    delete = getattr(task, "delete", None)
    if callable(delete):
        delete(delete_artifacts_and_models=False, raise_on_error=True)


def script_args(cli_args: Mapping[str, str | Path]) -> str:
    return shlex.join(_cli_parts(cli_args))


def script_entry_point(entry_point: str, cli_args: Mapping[str, str | Path]) -> str:
    return shlex.join([entry_point, *_cli_parts(cli_args)])


def _cli_parts(cli_args: Mapping[str, str | Path]) -> list[str]:
    return [part for key, value in cli_args.items() for part in (key, Path(value).as_posix())]


def read_csv_for_reporting(path: str | Path, *, max_rows: int = MAX_REPORT_TABLE_ROWS):
    try:
        import pandas as pd

        return pd.read_csv(path, nrows=max_rows)
    except (OSError, UnicodeDecodeError, ValueError):
        return None


class ClearMLLoggerAdapter:
    """Small wrapper around the ClearML Logger calls used by this product."""

    def __init__(self, task: Any) -> None:
        self.task = task

    def _logger(self) -> Any:
        return self.task.get_logger()

    def report_scalar(self, title: str, series: str, value: float, iteration: int = 0) -> None:
        self._logger().report_scalar(title=title, series=series, value=value, iteration=iteration)

    def report_table(self, title: str, series: str, path: str | Path, iteration: int = 0) -> None:
        path = Path(path)
        if not path.exists():
            return
        report_table = getattr(self._logger(), "report_table", None)
        if not callable(report_table):
            return
        frame = read_csv_for_reporting(path)
        if frame is None:
            return
        report_table(title=title, series=series, table_plot=frame, iteration=iteration)

    def report_media(self, title: str, series: str, path: str | Path, iteration: int = 0) -> None:
        path = Path(path)
        if not path.exists():
            return
        report_media = getattr(self._logger(), "report_media", None)
        if not callable(report_media):
            return
        report_media(title=title, series=series, local_path=str(path), iteration=iteration)

    def report_image(self, title: str, series: str, path: str | Path, iteration: int = 0) -> None:
        path = Path(path)
        if not path.exists():
            return
        report_image = getattr(self._logger(), "report_image", None)
        if callable(report_image):
            report_image(title=title, series=series, local_path=str(path), iteration=iteration)
            return
        self.report_media(title, series, path, iteration=iteration)
