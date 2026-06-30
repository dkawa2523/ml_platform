from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Protocol

from ml_platform_core.io import find_table_file
from ml_platform_core.stages import StageName, as_stage_name
from ml_platform_core.value_coercion import (
    as_bool as _as_bool,
    as_candidates as _as_candidates,
    as_dict as _as_dict,
    as_str_list as _as_str_list,
)
from params import (
    apply_connected_params_to_config,
    build_default_connected_params,
    group_connected_params,
)
from source_resolution import resolve_infer_model_source_config, resolve_stage_inputs_config


class ClearMLUnavailable(RuntimeError):
    pass


class ClearMLExecutionTask(Protocol):
    def set_base_docker(self, *args: Any, **kwargs: Any) -> Any: ...

    def update_parameters(self, params: dict[str, Any]) -> Any: ...


def clearml_projects(clearml_cfg: dict[str, Any] | None) -> dict[str, str]:
    """Return ClearML project layout, preferring explicit profile projects."""
    clearml_cfg = clearml_cfg or {}
    root = str(clearml_cfg.get("project_root") or "MLPlatform/Dev").rstrip("/")
    configured = _configured_projects(clearml_cfg)
    return _project_layout(root, configured)


def _configured_projects(clearml_cfg: dict[str, Any]) -> dict[str, Any]:
    configured = clearml_cfg.get("projects") or {}
    return configured if isinstance(configured, dict) else {}


def _project_layout(root: str, configured: dict[str, Any]) -> dict[str, str]:
    stages = str(configured.get("stages") or f"{root}/Runs/Tabular/Stages")
    tasks = str(configured.get("tasks") or f"{root}/Runs/Tabular/Tasks")
    defaults = _project_defaults(
        root,
        stage_project=stages if configured.get("stages") else None,
        task_project=tasks if configured.get("tasks") else None,
        stages=stages,
        tasks=tasks,
    )
    return {key: str(configured.get(key) or value) for key, value in defaults.items()}


def _project_defaults(
    root: str,
    *,
    stage_project: str | None,
    task_project: str | None,
    stages: str,
    tasks: str,
) -> dict[str, str]:
    return {
        "templates": f"{root}/Templates/Tabular",
        "pipelines": f"{root}/Pipelines/Tabular",
        "preprocess": stage_project or f"{root}/Runs/Tabular/Preprocess",
        "train": stage_project or f"{root}/Runs/Tabular/Train",
        "ensemble": stage_project or f"{root}/Runs/Tabular/Ensemble",
        "evaluate": stage_project or f"{root}/Runs/Tabular/Evaluate",
        "infer": task_project or f"{root}/Runs/Tabular/Infer",
        "stages": stages,
        "tasks": tasks,
        "experiments": f"{root}/Experiments/Tabular",
    }


def clearml_execution_image(clearml_cfg: dict[str, Any] | None) -> str | None:
    clearml_cfg = clearml_cfg or {}
    execution = clearml_cfg.get("execution") or {}
    if not isinstance(execution, dict):
        execution = {}
    return execution.get("image") or clearml_cfg.get("execution_image")


def apply_execution_image(task: ClearMLExecutionTask, image: str | None) -> None:
    if not image:
        return
    try:
        task.set_base_docker(docker_image=image)
    except TypeError:  # pragma: no cover - ClearML SDK version compatibility
        task.set_base_docker(docker_cmd=image)
    task.update_parameters({"Execution/docker_image": image})


def clearml_stage_project(projects: dict[str, str], stage: StageName | str) -> str:
    stage_name = as_stage_name(str(stage))
    if stage_name == "preprocess_features":
        return projects["preprocess"]
    if stage_name == "train_model":
        return projects["train"]
    if stage_name == "build_ensemble":
        return projects["ensemble"]
    if stage_name == "evaluate_models":
        return projects["evaluate"]
    raise AssertionError(f"Unhandled stage: {stage_name}")


def clearml_template_name(template_name: str) -> str:
    mapping = {
        "tabular_train_pipeline_template": "template/tabular_train_pipeline",
        "tabular_infer_template": "template/tabular_infer",
        "tabular_stage_template": "internal/tabular_stage",
    }
    return mapping.get(template_name, template_name)


def clearml_tags(
    run_type: str,
    *,
    user_facing: bool = False,
    internal: bool = False,
    stage: str | None = None,
    model: str | None = None,
    ensemble: str | None = None,
) -> list[str]:
    tags = ["domain:tabular", f"run_type:{run_type}"]
    if user_facing:
        tags.append("user_facing:true")
    if internal:
        tags.append("internal:true")
    if stage:
        tags.append(f"stage:{stage}")
    if model:
        tags.append(f"model:{model}")
    if ensemble:
        tags.append(f"ensemble:{ensemble}")
    return tags


def prefixed_task_name(prefix: str, name: str, run_name: str | None = None) -> str:
    if name.startswith(("template/", "internal/", "pipeline/", "stage/", "task/")):
        return name
    if run_name:
        return f"{prefix}/{name}/{run_name}"
    return f"{prefix}/{name}"


def stage_task_label(stage: StageName | str, model_name: str | None = None, ensemble_method: str | None = None) -> str:
    stage_name = as_stage_name(str(stage))
    if stage_name == "train_model" and model_name:
        return f"train_{model_name}"
    if stage_name == "build_ensemble" and ensemble_method:
        return f"build_ensemble_{ensemble_method}"
    return stage_name


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
    add_tags = getattr(task, "add_tags", None)
    set_tags = getattr(task, "set_tags", None)
    if replace_tags and callable(set_tags):
        set_tags(sorted(set(tags)))
    elif callable(add_tags):
        add_tags(tags)
    elif callable(set_tags):
        set_tags(sorted(set(_existing_tags(task)) | set(tags)))


def _existing_tags(task: Any) -> list[str]:
    get_tags = getattr(task, "get_tags", None)
    return list(get_tags() or []) if callable(get_tags) else []


def _apply_clearml_comment(task: Any, comment: str) -> None:
    set_comment = getattr(task, "set_comment", None)
    if callable(set_comment):
        set_comment(comment)


@contextmanager
def _without_repo_clearml_shadow() -> Iterator[None]:
    """Avoid accidental shadowing of the official `clearml` package.

    The repository has a top-level `clearml/` operations directory. SDK imports go
    through this helper so the official SDK is imported, not the repo directory.
    """
    repo_root = Path(__file__).resolve().parents[1]
    original_path = list(sys.path)
    try:
        sys.path = [p for p in sys.path if Path(p or ".").resolve() != repo_root.resolve()]
        yield
    finally:
        sys.path = original_path


def import_clearml_sdk() -> Any:
    """Import the official ClearML SDK while the repo keeps `clearml/`.

    The operations directory is still named `clearml` for template compatibility,
    so SDK imports stay behind this helper until the runtime entrypoints move.
    """
    try:
        with _without_repo_clearml_shadow():
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
        with _without_repo_clearml_shadow():
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


def validate_clearml_runtime() -> None:
    """Fail early when the ClearML SDK/runtime cannot be imported."""
    import_clearml_symbol("Task")


def clearml_dataset_exists(dataset_id: str) -> bool:
    """Return whether a ClearML Dataset ID resolves.

    Callers should validate ClearML runtime availability at the entrypoint
    before using this narrow existence check.
    """
    dataset_id = dataset_id.strip()
    if not dataset_id:
        raise ValueError("dataset_id must not be empty.")
    Dataset = import_clearml_symbol("Dataset")
    try:
        Dataset.get(dataset_id=dataset_id)
    except Exception:  # pragma: no cover - ClearML SDK raises version-specific exceptions
        return False
    return True


def as_bool(value: Any, *, default: bool = False) -> bool:
    return _as_bool(value, default=default)


def default_runtime_params(cfg: dict[str, Any]) -> dict[str, Any]:
    return build_default_connected_params(cfg)


def grouped_runtime_params(params: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return group_connected_params(params)


def as_str_list(value: Any) -> list[str] | None:
    return _as_str_list(value)


def as_dict(value: Any) -> dict[str, Any]:
    return _as_dict(value)


def as_candidates(value: Any) -> list[Any]:
    return _as_candidates(value)


def apply_runtime_params(
    cfg: dict[str, Any],
    connected_params: dict[str, Any],
    *,
    resolved_local_path: str | None = None,
) -> dict[str, Any]:
    return apply_connected_params_to_config(
        cfg,
        connected_params,
        resolved_local_path=resolved_local_path,
    )


def _read_table_for_reporting(path: Path):
    try:
        import pandas as pd

        return pd.read_csv(path)
    except (OSError, UnicodeDecodeError, ValueError):
        return None


def _raise_logger_signature_error(method_name: str, exc: TypeError) -> None:
    raise TypeError(f"ClearML logger method {method_name} has an unsupported signature.") from exc


class ClearMLAdapter:
    """Thin ClearML wrapper.

    This file is the only normal runtime place that touches the ClearML SDK.
    Package logic belongs to pkgs and must remain ClearML-free.
    """

    def __init__(self, task: Any) -> None:
        self.task = task

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
        for group, values in grouped_runtime_params(params).items():
            group_values = self.task.connect(values, name=group)
            if not isinstance(group_values, dict):
                group_values = values
            connected.update({f"{group}/{key}": value for key, value in group_values.items()})
        return connected

    def resolve_dataset(
        self,
        dataset_id: str | None,
        fallback_local_path: str | None,
        *,
        dataset_file: str | None = None,
    ) -> str:
        if dataset_id is None or not str(dataset_id).strip():
            if not fallback_local_path:
                raise ValueError("Either clearml_dataset_id or local_path is required.")
            return str(find_table_file(fallback_local_path, preferred_name=dataset_file))

        dataset_id_text = str(dataset_id).strip()
        Dataset = import_clearml_symbol("Dataset")
        dataset = Dataset.get(dataset_id=dataset_id_text)
        return str(find_table_file(Path(dataset.get_local_copy()), preferred_name=dataset_file))

    def resolve_artifact_path(self, artifact_path: str | Path | None) -> str | None:
        if not artifact_path:
            return None
        text = str(artifact_path)
        if "://" not in text:
            return text

        StorageManager = import_clearml_symbol("StorageManager")
        try:
            local_copy = StorageManager.get_local_copy(remote_url=text)
        except TypeError:  # pragma: no cover - depends on ClearML SDK version
            local_copy = StorageManager.get_local_copy(text)
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
        self.task.get_logger().report_scalar(title=title, series=series, value=value, iteration=iteration)

    def report_table(self, title: str, series: str, path: str | Path, iteration: int = 0) -> None:
        path = Path(path)
        if not path.exists():
            return
        report_table = getattr(self.task.get_logger(), "report_table", None)
        if not callable(report_table):
            return
        frame = _read_table_for_reporting(path)
        if frame is None:
            return
        try:
            report_table(title=title, series=series, table_plot=frame, iteration=iteration)
        except TypeError as exc:
            _raise_logger_signature_error("report_table", exc)

    def report_scatter(self, title: str, series: str, points: list[tuple[float, float]], iteration: int = 0) -> None:
        if not points:
            return
        report_scatter = getattr(self.task.get_logger(), "report_scatter2d", None)
        if not callable(report_scatter):
            return
        try:
            report_scatter(
                title=title,
                series=series,
                scatter=points,
                iteration=iteration,
                xaxis="actual",
                yaxis="prediction",
                mode="markers",
            )
        except TypeError:
            try:
                report_scatter(title=title, series=series, scatter=points, iteration=iteration)
            except TypeError:
                try:
                    report_scatter(
                        title=title,
                        series=series,
                        x=[point[0] for point in points],
                        y=[point[1] for point in points],
                        iteration=iteration,
                    )
                except TypeError as exc:
                    _raise_logger_signature_error("report_scatter2d", exc)

    def report_plotly(self, title: str, series: str, figure: dict[str, Any], iteration: int = 0) -> None:
        if not figure:
            return
        report_plotly = getattr(self.task.get_logger(), "report_plotly", None)
        if not callable(report_plotly):
            return
        try:
            report_plotly(title=title, series=series, figure=figure, iteration=iteration)
        except TypeError:
            try:
                report_plotly(title=title, series=series, plotly_object=figure, iteration=iteration)
            except TypeError as exc:
                _raise_logger_signature_error("report_plotly", exc)

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
        report_histogram = getattr(self.task.get_logger(), "report_histogram", None)
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
        try:
            report_histogram(**kwargs)
        except TypeError:
            try:
                kwargs.pop("values", None)
                kwargs["histogram"] = values
                report_histogram(**kwargs)
            except TypeError:
                try:
                    report_histogram(title=title, series=series, values=values, iteration=iteration)
                except TypeError as exc:
                    _raise_logger_signature_error("report_histogram", exc)

    def report_media(self, title: str, series: str, path: str | Path, iteration: int = 0) -> None:
        path = Path(path)
        if not path.exists():
            return
        report_media = getattr(self.task.get_logger(), "report_media", None)
        if not callable(report_media):
            return
        report_media(title=title, series=series, local_path=str(path), iteration=iteration)

    def report_image(self, title: str, series: str, path: str | Path, iteration: int = 0) -> None:
        path = Path(path)
        if not path.exists():
            return
        logger = self.task.get_logger()
        report_image = getattr(logger, "report_image", None)
        if callable(report_image):
            try:
                report_image(title=title, series=series, local_path=str(path), iteration=iteration)
                return
            except TypeError:
                pass
        self.report_media(title, series, path, iteration=iteration)

    def close(self) -> None:
        close = getattr(self.task, "close", None)
        if callable(close):
            close()
