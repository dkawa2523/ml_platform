from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

ArtifactPathResolver = Callable[[str | Path | None], str | None]
TaskClassFactory = Callable[[], Any]

LOCAL_MODEL_PATH_KEYS = (
    "artifact_path",
    "local_model_path",
    "info_path",
    "feature_spec_path",
    "preprocess_bundle_path",
)
TASK_SOURCE_TYPE = "task_id"


def resolve_stage_inputs_config(
    cfg: dict[str, Any],
    resolve_artifact_path: ArtifactPathResolver,
) -> dict[str, Any]:
    cfg = deepcopy(cfg)
    if "stage_inputs" not in cfg:
        return cfg
    cfg["stage_inputs"] = {
        key: _resolve_stage_value(value, resolve_artifact_path)
        for key, value in (cfg.get("stage_inputs") or {}).items()
    }
    return cfg


def resolve_infer_model_source_config(
    cfg: dict[str, Any],
    *,
    task_cls_factory: TaskClassFactory,
    resolve_artifact_path: ArtifactPathResolver,
) -> dict[str, Any]:
    cfg = deepcopy(cfg)
    model_cfg = cfg.setdefault("model", {})
    source_type = str(model_cfg.get("source_type") or "local_path").strip()
    if source_type == TASK_SOURCE_TYPE:
        return _resolve_task_model_source(cfg, task_cls_factory(), resolve_artifact_path)
    if source_type == "local_path":
        _resolve_local_model_paths(model_cfg, resolve_artifact_path)
        return cfg
    raise ValueError("model.source_type must be one of: task_id, local_path.")


def _decode_stage_value(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("{") or text.startswith("["):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return value
    return value


def _resolve_stage_value(value: Any, resolve_artifact_path: ArtifactPathResolver) -> Any:
    value = _decode_stage_value(value)
    if isinstance(value, dict):
        return _resolve_stage_mapping(value, resolve_artifact_path)
    if isinstance(value, list):
        return _resolve_stage_list(value, resolve_artifact_path)
    if _is_artifact_ref(value):
        return resolve_artifact_path(value)
    return value


def _resolve_stage_mapping(value: dict[str, Any], resolve_artifact_path: ArtifactPathResolver) -> dict[str, Any]:
    return {key: _resolve_stage_value(item, resolve_artifact_path) for key, item in value.items()}


def _resolve_stage_list(value: list[Any], resolve_artifact_path: ArtifactPathResolver) -> list[Any]:
    return [_resolve_stage_value(item, resolve_artifact_path) for item in value]


def _is_artifact_ref(value: Any) -> bool:
    return isinstance(value, str) and "://" in value.strip()


def _resolve_local_model_paths(model_cfg: dict[str, Any], resolve_artifact_path: ArtifactPathResolver) -> None:
    for key in LOCAL_MODEL_PATH_KEYS:
        value = model_cfg.get(key)
        if isinstance(value, str) and "://" in value:
            model_cfg[key] = resolve_artifact_path(value)


def _resolve_task_model_source(
    cfg: dict[str, Any],
    Task: Any,
    resolve_artifact_path: ArtifactPathResolver,
) -> dict[str, Any]:
    model_cfg = cfg.setdefault("model", {})
    source_task_id = model_cfg.get("source_task_id")
    if not source_task_id:
        raise ValueError("model.source_task_id is required when model.source_type=task_id.")

    selector = str(model_cfg.get("model_selector") or "best").strip()
    source_task = Task.get_task(task_id=source_task_id)
    tasks = _task_family(Task, str(source_task_id), source_task)
    selected_task, model_key, info_key = _select_model_artifact(tasks, selector)
    model_path = _artifact_local_path(selected_task, model_key, resolve_artifact_path)
    if not model_path:
        raise ValueError(f"Artifact {model_key!r} on task {_task_name(selected_task)} has no URL.")

    model_cfg["artifact_path"] = model_path
    _set_optional_info_path(model_cfg, selected_task, info_key, resolve_artifact_path)
    model_cfg.update(_preprocess_paths(tasks, resolve_artifact_path))
    model_cfg["resolved_source_task_name"] = _task_name(selected_task)
    model_cfg["resolved_source_artifact"] = model_key
    return cfg


def _task_family(Task: Any, task_id: str, source_task: Any) -> list[Any]:
    tasks: list[Any] = [source_task]
    seen_ids = {getattr(source_task, "id", None)}
    for parent in _task_query_ids(task_id, source_task):
        _append_unseen_children(tasks, seen_ids, _child_tasks(Task, parent))
    return tasks


def _task_query_ids(task_id: str, source_task: Any) -> list[str]:
    query_ids = [task_id]
    parent_id = getattr(source_task, "parent", None)
    if parent_id and parent_id not in query_ids:
        query_ids.append(parent_id)
    return query_ids


def _append_unseen_children(tasks: list[Any], seen_ids: set[Any], children: list[Any]) -> None:
    for child in children:
        child_id = getattr(child, "id", None)
        if child_id not in seen_ids:
            tasks.append(child)
            seen_ids.add(child_id)


def _child_tasks(Task: Any, parent_id: str) -> list[Any]:
    try:
        children = Task.get_tasks(task_filter={"parent": parent_id}, allow_archived=True)
    except TypeError:
        children = Task.get_tasks(task_filter={"parent": parent_id})
    return list(children or [])


def _set_optional_info_path(
    model_cfg: dict[str, Any],
    selected_task: Any,
    info_key: str | None,
    resolve_artifact_path: ArtifactPathResolver,
) -> None:
    if not info_key:
        return
    info_path = _artifact_local_path(selected_task, info_key, resolve_artifact_path)
    if info_path:
        model_cfg["info_path"] = info_path


def _preprocess_paths(tasks: list[Any], resolve_artifact_path: ArtifactPathResolver) -> dict[str, str]:
    preprocess = next((task for task in tasks if _looks_like_stage(task, "preprocess_features")), None)
    if preprocess is None:
        return {}
    return _artifact_path_map(
        preprocess,
        resolve_artifact_path,
        {
            "feature_spec_path": "feature_spec",
            "preprocess_bundle_path": "preprocess_bundle",
        },
    )


def _artifact_path_map(
    task: Any,
    resolve_artifact_path: ArtifactPathResolver,
    artifacts: dict[str, str],
) -> dict[str, str]:
    paths: dict[str, str] = {}
    for config_key, artifact_key in artifacts.items():
        path = _artifact_local_path(task, artifact_key, resolve_artifact_path)
        if path:
            paths[config_key] = path
    return paths


def _select_model_artifact(tasks: list[Any], selector: str) -> tuple[Any, str, str | None]:
    if selector == "best":
        selected = _select_best_artifact(tasks)
    elif _is_ensemble_selector(selector):
        selected = _select_ensemble_artifact(tasks, selector)
    else:
        selected = _select_named_model_artifact(tasks, selector)
    if selected is None:
        raise ValueError(
            f"Could not resolve model_selector={selector!r} from source_task_id. "
            f"Discovered: {_discovery_summary(tasks)}"
        )
    return selected


def _select_best_artifact(tasks: list[Any]) -> tuple[Any, str, str | None] | None:
    source = tasks[0]
    source_artifacts = _task_artifacts(source)
    if "best_model" in source_artifacts:
        return source, "best_model", _info_key(source_artifacts, "best_model_json", fallback="model_info")

    evaluate = _first_task_with_artifact(tasks, "best_model", stage="evaluate_models")
    if evaluate is not None:
        return evaluate, "best_model", _info_key(_task_artifacts(evaluate), "best_model_json", fallback="model_info")
    if "model" in source_artifacts:
        return source, "model", _info_key(source_artifacts, "model_info")
    return None


def _select_ensemble_artifact(tasks: list[Any], selector: str) -> tuple[Any, str, str | None] | None:
    model_key, info_key, fallback_info_key = _ensemble_artifact_keys(selector)
    ensemble = _ensemble_task_with_artifact(tasks, model_key)
    if ensemble is None:
        return None
    return ensemble, model_key, _info_key(_task_artifacts(ensemble), info_key, fallback=fallback_info_key)


def _ensemble_artifact_keys(selector: str) -> tuple[str, str, str]:
    ensemble_method = selector.split(":", 1)[1].strip() if selector.startswith("ensemble:") else ""
    suffix = f"_{ensemble_method}" if ensemble_method else ""
    return f"model{suffix}", f"model_info{suffix}", f"ensemble_info{suffix}"


def _ensemble_task_with_artifact(tasks: list[Any], model_key: str) -> Any | None:
    source = tasks[0]
    if _stage_task_has_artifact(source, "build_ensemble", model_key):
        return source
    return next((task for task in tasks[1:] if _stage_task_has_artifact(task, "build_ensemble", model_key)), None)


def _stage_task_has_artifact(task: Any, stage: str, artifact_name: str) -> bool:
    return _looks_like_stage(task, stage) and artifact_name in _task_artifacts(task)


def _select_named_model_artifact(tasks: list[Any], selector: str) -> tuple[Any, str, str | None] | None:
    source = tasks[0]
    source_artifacts = _task_artifacts(source)
    if "model" in source_artifacts and _matches_named_model(source, selector):
        return source, "model", _info_key(source_artifacts, "model_info")

    train = _first_named_train_task(tasks, selector)
    if train is not None:
        return train, "model", _info_key(_task_artifacts(train), "model_info")
    return None


def _first_task_with_artifact(tasks: list[Any], artifact_name: str, *, stage: str | None = None) -> Any | None:
    for task in tasks:
        if stage is not None and not _looks_like_stage(task, stage):
            continue
        if artifact_name in _task_artifacts(task):
            return task
    return None


def _matches_named_model(task: Any, selector: str) -> bool:
    return _looks_like_train_model(task, selector) or _task_model_name(task) == selector


def _first_named_train_task(tasks: list[Any], selector: str) -> Any | None:
    return next(
        (task for task in tasks if _looks_like_train_model(task, selector) and "model" in _task_artifacts(task)),
        None,
    )


def _is_ensemble_selector(selector: str) -> bool:
    return selector == "ensemble" or selector.startswith("ensemble:")


def _info_key(artifacts: dict[str, Any], key: str, *, fallback: str | None = None) -> str | None:
    if key in artifacts:
        return key
    return fallback


def _artifact_local_path(
    task: Any,
    artifact_name: str,
    resolve_artifact_path: ArtifactPathResolver,
) -> str | None:
    artifact = _task_artifacts(task).get(artifact_name)
    url = _artifact_url(artifact)
    if not url:
        return None
    return resolve_artifact_path(url)


def _artifact_url(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (str, Path)):
        return str(value)
    return _string_attr(value, "url") or _string_attr(value, "uri")


def _string_attr(value: Any, name: str) -> str | None:
    attr_value = getattr(value, name, None)
    if callable(attr_value):
        attr_value = attr_value()
    return str(attr_value) if attr_value else None


def _task_artifacts(task: Any) -> dict[str, Any]:
    artifacts = getattr(task, "artifacts", None)
    if callable(artifacts):
        artifacts = artifacts()
    if isinstance(artifacts, dict):
        return artifacts
    get_registered = getattr(task, "get_registered_artifacts", None)
    if callable(get_registered):
        artifacts = get_registered()
        if isinstance(artifacts, dict):
            return artifacts
    return {}


def _task_parameters(task: Any) -> dict[str, Any]:
    get_parameters = getattr(task, "get_parameters", None)
    if not callable(get_parameters):
        return {}
    try:
        params = get_parameters(cast=True)
    except TypeError:
        params = get_parameters()
    return params if isinstance(params, dict) else {}


def _task_name(task: Any) -> str:
    for attr in ("name", "task_name"):
        value = getattr(task, attr, None)
        if value:
            return str(value)
    get_name = getattr(task, "get_name", None)
    if callable(get_name):
        return str(get_name())
    return str(getattr(task, "id", "unknown"))


def _task_stage(task: Any) -> str:
    params = _task_parameters(task)
    return str(params.get("Run/stage") or "").strip()


def _task_model_name(task: Any) -> str:
    params = _task_parameters(task)
    return str(params.get("Model/name") or "").strip()


def _looks_like_stage(task: Any, stage: str) -> bool:
    name = _task_name(task)
    return _task_stage(task) == stage or name == stage or name.endswith(f"/{stage}") or name.endswith(stage)


def _looks_like_train_model(task: Any, selector: str) -> bool:
    safe_selector = selector.replace("-", "_")
    name = _task_name(task)
    return _task_stage(task) == "train_model" and (
        _task_model_name(task) == selector
        or name.endswith(f"train_{safe_selector}")
        or name.endswith(f"train_{selector}")
    )


def _discovery_summary(tasks: list[Any]) -> str:
    if not tasks:
        return "no tasks discovered"
    return "; ".join(
        f"{_task_name(task)}(stage={_task_stage(task) or '-'}, artifacts={sorted(_task_artifacts(task))})"
        for task in tasks
    )
