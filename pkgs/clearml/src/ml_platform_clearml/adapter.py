from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from .model_source_resolution import resolve_infer_model_source_config
from .naming import (
    clearml_projects as clearml_projects,
)
from .naming import (
    clearml_stage_project as clearml_stage_project,
)
from .naming import (
    clearml_tags as clearml_tags,
)
from .naming import (
    clearml_template_name as clearml_template_name,
)
from .naming import (
    prefixed_task_name as prefixed_task_name,
)
from .naming import (
    stage_task_label as stage_task_label,
)
from .param_transport import group_connected_params
from .stage_input_resolution import resolve_stage_inputs_config
from .support import ClearMLLoggerAdapter, apply_task_tags, set_task_comment


class ClearMLUnavailable(RuntimeError):
    pass


CLEARML_SDK_VERSION_PREFIX = "2.1."


def _apply_clearml_metadata(
    task: Any,
    *,
    tags: list[str] | None = None,
    comment: str | None = None,
    replace_tags: bool = False,
) -> None:
    tags = tags or []
    if tags:
        _apply_clearml_tags(task, tags, replace_tags=replace_tags)
    if comment:
        _apply_clearml_comment(task, comment)


def _apply_clearml_tags(task: Any, tags: list[str], *, replace_tags: bool) -> None:
    apply_task_tags(task, tags, replace=replace_tags)


def _apply_clearml_comment(task: Any, comment: str) -> None:
    set_task_comment(task, comment)


def import_clearml_sdk() -> Any:
    """Import the optional official ClearML SDK."""
    try:
        return importlib.import_module("clearml")
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        if exc.name == "clearml":
            raise ClearMLUnavailable(
                "Official ClearML SDK is not installed. Install the `clearml` extra or run `uv sync --extra clearml`."
            ) from exc
        raise ClearMLUnavailable(f"ClearML SDK dependency is missing while importing official SDK: {exc.name}") from exc
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ClearMLUnavailable(
            "Official ClearML SDK is installed but could not be imported. "
            "Check the SDK version and its optional runtime dependencies."
        ) from exc


def import_clearml_symbol(symbol: str) -> Any:
    module = import_clearml_sdk()
    try:
        return getattr(module, symbol)
    except AttributeError as exc:  # pragma: no cover - defensive
        raise ClearMLUnavailable(f"ClearML SDK does not expose symbol: {symbol}") from exc


def import_clearml_automation() -> Any:
    try:
        return importlib.import_module("clearml.automation")
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        if exc.name in {"clearml", "clearml.automation"}:
            raise ClearMLUnavailable("ClearML automation module is unavailable. Install/upgrade ClearML SDK.") from exc
        raise ClearMLUnavailable(
            f"ClearML automation dependency is missing while importing official SDK: {exc.name}"
        ) from exc
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ClearMLUnavailable(
            "ClearML automation module could not be imported. Install/upgrade ClearML SDK."
        ) from exc


def validate_clearml_runtime(*, require_automation: bool = False) -> None:
    """Fail early when the ClearML SDK/runtime cannot be imported."""
    sdk = import_clearml_sdk()
    version = str(getattr(sdk, "__version__", "") or "")
    if not version.startswith(CLEARML_SDK_VERSION_PREFIX):
        raise ClearMLUnavailable(
            f"ClearML SDK {CLEARML_SDK_VERSION_PREFIX}x is required; found {version or 'unknown'}."
        )
    _require_clearml_symbols(sdk, ("Task", "StorageManager"), owner="ClearML SDK")
    if require_automation:
        _require_clearml_symbols(import_clearml_automation(), ("PipelineController",), owner="clearml.automation")


def _require_clearml_symbols(module: Any, symbols: tuple[str, ...], *, owner: str) -> None:
    missing = [symbol for symbol in symbols if not hasattr(module, symbol)]
    if missing:
        raise ClearMLUnavailable(f"{owner} is missing required symbol(s): {', '.join(missing)}.")


class ClearMLAdapter:
    """Thin ClearML wrapper.

    This file is the only normal runtime place that touches the ClearML SDK.
    Package logic belongs to pkgs and must remain ClearML-free.
    """

    def __init__(self, task: Any) -> None:
        self.task = task
        self.logger = ClearMLLoggerAdapter(task)

    @classmethod
    def init(
        cls,
        *,
        project_name: str,
        task_name: str,
        output_uri: str | None = None,
        tags: list[str] | None = None,
        comment: str | None = None,
    ):
        Task = import_clearml_symbol("Task")
        kwargs: dict[str, Any] = {"project_name": project_name, "task_name": task_name}
        if output_uri:
            kwargs["output_uri"] = output_uri
        task = Task.init(**kwargs)
        _apply_clearml_metadata(task, tags=tags, comment=comment, replace_tags=True)
        return cls(task)

    def apply_metadata(
        self,
        *,
        project_name: str | None = None,
        task_name: str | None = None,
        tags: list[str] | None = None,
        comment: str | None = None,
        replace_tags: bool = False,
    ) -> None:
        if project_name:
            move_to_project = getattr(self.task, "move_to_project", None)
            set_project = getattr(self.task, "set_project", None)
            if callable(move_to_project):
                move_to_project(new_project_name=project_name)
            elif callable(set_project):
                set_project(project_name=project_name)
        if task_name:
            set_name = getattr(self.task, "set_name", None)
            if callable(set_name):
                set_name(task_name)
        _apply_clearml_metadata(self.task, tags=tags, comment=comment, replace_tags=replace_tags)

    def connect_params(self, params: dict[str, Any]) -> dict[str, Any]:
        connected: dict[str, Any] = {}
        for group, values in group_connected_params(params).items():
            group_values = self.task.connect(values, name=group)
            if not isinstance(group_values, dict):
                group_values = values
            connected.update({f"{group}/{key}": value for key, value in group_values.items()})
        return connected

    def resolve_dataset(
        self,
        dataset_id: str | None,
        fallback_local_path: str | None,
    ) -> str:
        if dataset_id is None or not str(dataset_id).strip():
            if not fallback_local_path:
                raise ValueError("Either clearml_dataset_id or local_path is required.")
            return str(fallback_local_path)

        dataset_id_text = str(dataset_id).strip()
        Dataset = import_clearml_symbol("Dataset")
        dataset = Dataset.get(dataset_id=dataset_id_text)
        return str(dataset.get_local_copy())

    def resolve_artifact_path(self, artifact_path: str | Path | None) -> str | None:
        if not artifact_path:
            return None
        text = str(artifact_path)
        if "://" not in text:
            return text

        StorageManager = import_clearml_symbol("StorageManager")
        local_copy = StorageManager.get_local_copy(remote_url=text)
        return str(local_copy)

    def resolve_stage_inputs(self, cfg: dict[str, Any]) -> dict[str, Any]:
        return resolve_stage_inputs_config(cfg, self.resolve_artifact_path)

    def resolve_infer_model_source(self, cfg: dict[str, Any]) -> dict[str, Any]:
        return resolve_infer_model_source_config(
            cfg,
            task_cls_factory=lambda: import_clearml_symbol("Task"),
            resolve_artifact_path=self.resolve_artifact_path,
        )

    def upload_artifact(self, name: str, path: str | Path) -> None:
        path = Path(path)
        if path.exists():
            self.task.upload_artifact(name=name, artifact_object=path)

    def report_scalar(self, title: str, series: str, value: float, iteration: int = 0) -> None:
        self.logger.report_scalar(title, series, value, iteration=iteration)

    def report_table(self, title: str, series: str, path: str | Path, iteration: int = 0) -> None:
        self.logger.report_table(title, series, path, iteration=iteration)

    def report_media(self, title: str, series: str, path: str | Path, iteration: int = 0) -> None:
        self.logger.report_media(title, series, path, iteration=iteration)

    def report_image(self, title: str, series: str, path: str | Path, iteration: int = 0) -> None:
        self.logger.report_image(title, series, path, iteration=iteration)

    def close(self) -> None:
        close = getattr(self.task, "close", None)
        if callable(close):
            close()
