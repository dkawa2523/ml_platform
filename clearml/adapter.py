from __future__ import annotations

import importlib
import json
import sys
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterator

from ml_platform_core.io import find_table_file


class ClearMLUnavailable(RuntimeError):
    pass


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
    try:
        with _without_repo_clearml_shadow():
            return importlib.import_module("clearml")
    except Exception as exc:  # pragma: no cover - optional dependency
        raise ClearMLUnavailable(
            "Official ClearML SDK is not installed or cannot be imported. "
            "Install with `pip install clearml`."
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
    except Exception as exc:  # pragma: no cover - optional dependency
        raise ClearMLUnavailable("ClearML automation module is unavailable. Install/upgrade ClearML SDK.") from exc


def as_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"", "none", "null"}:
            return default
        return text in {"1", "true", "yes", "y", "on"}
    return bool(value)


def as_list(value: Any) -> list[str] | None:
    if value is None or value == "":
        return None
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, tuple):
        return [str(v) for v in value]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(v) for v in parsed]
        except Exception:
            pass
        return [v.strip() for v in text.split(",") if v.strip()]
    raise ValueError(f"Cannot convert value to list: {value!r}")


def as_dict(value: Any) -> dict[str, Any]:
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError(f"Expected JSON object, got: {value!r}")
        return parsed
    raise ValueError(f"Cannot convert value to dict: {value!r}")


def as_candidates(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        value = json.loads(text)
    if not isinstance(value, list):
        raise ValueError(f"Expected JSON array for candidates, got: {value!r}")
    candidates = []
    for index, item in enumerate(value):
        if isinstance(item, str):
            text = item.strip()
            if not text:
                raise ValueError(f"Model/candidates[{index}] must not be empty.")
            candidates.append(text)
        elif isinstance(item, dict):
            candidates.append(dict(item))
        else:
            raise ValueError(f"Model/candidates[{index}] must be a model name or object.")
    return candidates


def default_ui_params(cfg: dict[str, Any]) -> dict[str, Any]:
    """Return the small ClearML UI parameter surface for a task config."""
    run = cfg.get("run", {})
    params = {
        "Run/task": cfg.get("task"),
        "Run/name": run.get("name"),
        "Run/seed": run.get("seed"),
    }
    if "data" in cfg:
        data = cfg.get("data", {})
        params.update(
            {
                "Input/local_path": data.get("local_path"),
                "Input/clearml_dataset_id": data.get("clearml_dataset_id"),
                "Input/dataset_file": data.get("dataset_file"),
                "Input/target_column": data.get("target_column"),
                "Input/feature_columns": data.get("feature_columns"),
                "Input/id_columns": data.get("id_columns", []),
            }
        )
    if "model" in cfg:
        model = cfg.get("model", {})
        if "name" in model:
            params["Model/name"] = model.get("name")
        if "params" in model:
            params["Model/params"] = json.dumps(model.get("params", {}) or {})
        if "candidates" in model:
            params["Model/candidates"] = json.dumps(model.get("candidates", []) or [])
        if "selection_metric" in model:
            params["Model/selection_metric"] = model.get("selection_metric")
        if "search" in model:
            search = model.get("search", {}) or {}
            if not isinstance(search, dict):
                search = {}
            params["Model/search_enabled"] = as_bool(search.get("enabled"))
            params["Model/search_method"] = search.get("method", "grid")
            params["Model/search_space"] = json.dumps(search.get("search_space", {}) or {})
            params["Model/max_trials"] = int(search.get("max_trials") or 20)
        if "ensemble" in model:
            ensemble = model.get("ensemble", {}) or {}
            if not isinstance(ensemble, dict):
                ensemble = {}
            params["Model/ensemble_enabled"] = as_bool(ensemble.get("enabled"))
            params["Model/ensemble_method"] = ensemble.get("method", "mean_topk")
            params["Model/ensemble_top_k"] = int(ensemble.get("top_k") or 3)
        if "artifact_path" in model:
            params["Model/artifact_path"] = model.get("artifact_path")
    if "features" in cfg:
        params["Model/feature_preset"] = cfg.get("features", {}).get("preset")
    if "output" in cfg:
        output = cfg.get("output", {})
        if "prediction_name" in output:
            params["Output/prediction_name"] = output.get("prediction_name")
        if "chunk_size" in output:
            params["Output/chunk_size"] = output.get("chunk_size")
    return params


def grouped_ui_params(params: dict[str, Any]) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for key, value in params.items():
        group, name = key.split("/", 1)
        groups.setdefault(group, {})[name] = value
    return groups


def apply_ui_params(
    cfg: dict[str, Any],
    connected: dict[str, Any],
    *,
    resolved_local_path: str | None = None,
) -> dict[str, Any]:
    """Apply ClearML UI parameter values to nested config without importing ClearML."""
    cfg = deepcopy(cfg)
    has_input_params = any(key.startswith("Input/") for key in connected)
    if "data" in cfg or has_input_params:
        cfg.setdefault("data", {})
    cfg.setdefault("run", {})
    if any(key.startswith("Model/") for key in connected):
        cfg.setdefault("model", {})
    if "Model/feature_preset" in connected:
        cfg.setdefault("features", {})
    if any(key.startswith("Output/") for key in connected):
        cfg.setdefault("output", {})

    if connected.get("Run/task"):
        cfg["task"] = connected["Run/task"]
    if connected.get("Run/name"):
        cfg["run"]["name"] = connected["Run/name"]
    if connected.get("Run/seed") is not None:
        cfg["run"]["seed"] = int(connected["Run/seed"])

    if "data" in cfg:
        if resolved_local_path is not None:
            cfg["data"]["local_path"] = resolved_local_path
        elif connected.get("Input/local_path"):
            cfg["data"]["local_path"] = connected["Input/local_path"]

        for ui_key, config_key in (
            ("Input/clearml_dataset_id", "clearml_dataset_id"),
            ("Input/dataset_file", "dataset_file"),
            ("Input/target_column", "target_column"),
        ):
            if ui_key in connected:
                cfg["data"][config_key] = connected[ui_key]
        if "Input/feature_columns" in connected:
            cfg["data"]["feature_columns"] = as_list(connected.get("Input/feature_columns"))
        if "Input/id_columns" in connected:
            cfg["data"]["id_columns"] = as_list(connected.get("Input/id_columns")) or []

    if connected.get("Model/name"):
        cfg["model"]["name"] = connected["Model/name"]
    if "Model/params" in connected:
        cfg["model"]["params"] = as_dict(connected.get("Model/params"))
    if "Model/candidates" in connected:
        cfg["model"]["candidates"] = as_candidates(connected.get("Model/candidates"))
    if connected.get("Model/selection_metric"):
        cfg["model"]["selection_metric"] = connected["Model/selection_metric"]
    search_updates: dict[str, Any] = {}
    if "Model/search_enabled" in connected:
        search_updates["enabled"] = as_bool(connected.get("Model/search_enabled"))
    if connected.get("Model/search_method"):
        search_updates["method"] = str(connected["Model/search_method"]).strip().lower()
    if "Model/search_space" in connected:
        search_updates["search_space"] = as_dict(connected.get("Model/search_space"))
    if "Model/max_trials" in connected and connected.get("Model/max_trials") not in {None, ""}:
        search_updates["max_trials"] = int(connected["Model/max_trials"])
    if search_updates:
        cfg["model"].setdefault("search", {})
        cfg["model"]["search"].update(search_updates)
    ensemble_updates: dict[str, Any] = {}
    if "Model/ensemble_enabled" in connected:
        ensemble_updates["enabled"] = as_bool(connected.get("Model/ensemble_enabled"))
    if connected.get("Model/ensemble_method"):
        ensemble_updates["method"] = connected["Model/ensemble_method"]
    if "Model/ensemble_top_k" in connected and connected.get("Model/ensemble_top_k") not in {None, ""}:
        ensemble_updates["top_k"] = int(connected["Model/ensemble_top_k"])
    if ensemble_updates:
        cfg["model"].setdefault("ensemble", {})
        cfg["model"]["ensemble"].update(ensemble_updates)
    if connected.get("Model/artifact_path"):
        cfg["model"]["artifact_path"] = connected["Model/artifact_path"]
    if connected.get("Model/feature_preset"):
        cfg["features"]["preset"] = connected["Model/feature_preset"]

    if connected.get("Output/prediction_name"):
        cfg["output"]["prediction_name"] = connected["Output/prediction_name"]
    if "Output/chunk_size" in connected and connected.get("Output/chunk_size") not in {None, ""}:
        cfg["output"]["chunk_size"] = int(connected["Output/chunk_size"])
    return cfg


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
    ):
        Task = import_clearml_symbol("Task")
        kwargs: dict[str, Any] = {"project_name": project_name, "task_name": task_name}
        if output_uri:
            kwargs["output_uri"] = output_uri
        task = Task.init(**kwargs)
        return cls(task)

    def connect_params(self, params: dict[str, Any]) -> dict[str, Any]:
        connected: dict[str, Any] = {}
        for group, values in grouped_ui_params(params).items():
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
        if not dataset_id:
            if not fallback_local_path:
                raise ValueError("Either clearml_dataset_id or local_path is required.")
            return str(find_table_file(fallback_local_path, preferred_name=dataset_file))

        Dataset = import_clearml_symbol("Dataset")
        dataset = Dataset.get(dataset_id=dataset_id)
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

    def upload_artifact(self, name: str, path: str | Path) -> None:
        path = Path(path)
        if path.exists():
            self.task.upload_artifact(name=name, artifact_object=path)

    def report_scalar(self, title: str, series: str, value: float, iteration: int = 0) -> None:
        self.task.get_logger().report_scalar(title=title, series=series, value=value, iteration=iteration)

    def close(self) -> None:
        close = getattr(self.task, "close", None)
        if callable(close):
            close()
