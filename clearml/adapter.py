from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from ml_platform_core.stages import StageName, as_stage_name
from param_transport import group_connected_params
from source_resolution import resolve_infer_model_source_config, resolve_stage_inputs_config
from support import ClearMLLoggerAdapter, apply_task_tags, set_task_comment


class ClearMLUnavailable(RuntimeError):
    pass


CLEARML_SDK_VERSION_PREFIX = "2.1."


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
    apply_task_tags(task, tags, replace=replace_tags)


def _apply_clearml_comment(task: Any, comment: str) -> None:
    set_task_comment(task, comment)


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
