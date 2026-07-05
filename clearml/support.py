from __future__ import annotations

from pathlib import Path
import shlex
from typing import Any

MAX_REPORT_TABLE_ROWS = 1000


def existing_task_tags(task: Any) -> list[str]:
    get_tags = getattr(task, "get_tags", None)
    return list(get_tags() or []) if callable(get_tags) else []


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
        delete(delete_artifacts_and_models=False, raise_on_error=False)


def script_args(cli_args: dict[str, str | Path]) -> str:
    return shlex.join(_cli_parts(cli_args))


def script_entry_point(entry_point: str, cli_args: dict[str, str | Path]) -> str:
    return shlex.join([entry_point, *_cli_parts(cli_args)])


def _cli_parts(cli_args: dict[str, str | Path]) -> list[str]:
    return [part for key, value in cli_args.items() for part in (key, Path(value).as_posix())]


def set_task_script(
    task: Any,
    *,
    repository: str,
    branch: str,
    working_dir: str,
    entry_point: str,
    cli_args: dict[str, str | Path],
) -> None:
    task.set_script(
        repository=repository,
        branch=branch,
        commit="",
        diff="",
        working_dir=working_dir,
        entry_point=script_entry_point(entry_point, cli_args),
    )


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

    def report_scatter(self, title: str, series: str, points: list[tuple[float, float]], iteration: int = 0) -> None:
        if not points:
            return
        report_scatter = getattr(self._logger(), "report_scatter2d", None)
        if not callable(report_scatter):
            return
        report_scatter(
            title=title,
            series=series,
            scatter=points,
            iteration=iteration,
            xaxis="actual",
            yaxis="prediction",
            mode="markers",
        )

    def report_plotly(self, title: str, series: str, figure: dict[str, Any], iteration: int = 0) -> None:
        if not figure:
            return
        report_plotly = getattr(self._logger(), "report_plotly", None)
        if not callable(report_plotly):
            return
        report_plotly(title=title, series=series, figure=figure, iteration=iteration)

    def report_histogram(
        self,
        title: str,
        series: str,
        values: list[float],
        iteration: int = 0,
        *,
        xaxis: str | None = None,
        yaxis: str | None = None,
        mode: str | None = None,
    ) -> None:
        if not values:
            return
        report_histogram = getattr(self._logger(), "report_histogram", None)
        if not callable(report_histogram):
            return
        kwargs: dict[str, Any] = {
            "title": title,
            "series": series,
            "values": values,
            "iteration": iteration,
        }
        if xaxis:
            kwargs["xaxis"] = xaxis
        if yaxis:
            kwargs["yaxis"] = yaxis
        if mode:
            kwargs["mode"] = mode
        report_histogram(**kwargs)

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
