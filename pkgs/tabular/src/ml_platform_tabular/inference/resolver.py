from __future__ import annotations

from pathlib import Path
from typing import Any

from ..model_artifact import default_model_path
from .metadata import _read_json_if_exists


def _safe_name(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value)
    return safe or "model"


def _model_selector(cfg: dict[str, Any]) -> str:
    return str(cfg.get("model", {}).get("model_selector") or "best").strip()


def _model_source_type(cfg: dict[str, Any]) -> str:
    return str(cfg.get("model", {}).get("source_type") or "local_path").strip()


def _is_url(value: str) -> bool:
    return "://" in value


def _info_says_ensemble(path: Path) -> bool:
    info_path = path.parent / "model_info.json"
    info = _read_json_if_exists(info_path)
    return str(info.get("artifact_kind") or "").lower() == "ensemble"


def _ensemble_selector_parts(selector: str) -> tuple[bool, str | None]:
    if selector == "ensemble":
        return True, None
    if selector.startswith("ensemble:"):
        method = selector.split(":", 1)[1].strip()
        if not method:
            raise ValueError("model_selector=ensemble:<method> requires a method name.")
        return True, method
    return False, None


def _best_ensemble_from_refs(build_dir: Path) -> Path | None:
    refs = _read_json_if_exists(build_dir / "ensemble_refs.json")
    best = refs.get("best_ensemble") if isinstance(refs, dict) else None
    if isinstance(best, dict) and best.get("model"):
        path = Path(str(best["model"]))
        if path.exists():
            return path
        candidate = build_dir / path.name
        if candidate.exists():
            return candidate
    return None


def _ensemble_model_candidates(directory: Path, selector: str) -> list[Path]:
    _, method = _ensemble_selector_parts(selector)
    build_dirs = [directory / "build_ensemble", directory]
    candidates: list[Path] = []
    for build_dir in build_dirs:
        if method:
            candidates.append(build_dir / f"model_{method}.joblib")
        else:
            best = _best_ensemble_from_refs(build_dir)
            if best is not None:
                candidates.append(best)
            candidates.append(build_dir / "model.joblib")
    return candidates


def _selector_candidates(directory: Path, selector: str) -> list[Path]:
    selector = selector.strip()
    if selector == "best":
        return [
            directory / "evaluate_models" / "best_model.joblib",
            directory / "best_model.joblib",
            directory / "model.joblib",
        ]
    is_ensemble, _ = _ensemble_selector_parts(selector)
    if is_ensemble:
        return _ensemble_model_candidates(directory, selector)
    return [
        directory / f"train_{_safe_name(selector)}" / "model.joblib",
        directory / f"train_{selector}" / "model.joblib",
        directory / "model.joblib",
    ]


def _resolve_directory_model_path(directory: Path, selector: str, *, strict: bool = True) -> Path | None:
    for candidate in _selector_candidates(directory, selector):
        if not candidate.exists():
            continue
        is_ensemble, _ = _ensemble_selector_parts(selector)
        if is_ensemble and candidate.name == "model.joblib" and candidate.parent == directory:
            if not _info_says_ensemble(candidate):
                continue
        if selector != "best" and not is_ensemble and candidate.parent == directory:
            info = _read_json_if_exists(candidate.parent / "model_info.json")
            name = str(info.get("model_name") or info.get("best_model_name") or "")
            if name and name != selector:
                continue
        return candidate
    if strict:
        raise ValueError(f"Could not resolve model_selector={selector!r} under directory: {directory}")
    return None


def _path_from_value(value: Any, selector: str, *, strict: bool = True) -> Path | None:
    if not value:
        return None
    text = str(value)
    if _is_url(text):
        raise ValueError("Remote model URLs must be resolved by clearml/adapter.py before package inference.")
    path = Path(text)
    if path.is_dir():
        return _resolve_directory_model_path(path, selector, strict=strict)
    return path


def _latest_training_pipeline_model(output_dir: Path, selector: str) -> Path | None:
    latest_training = output_dir / "latest_training_pipeline"
    if not latest_training.exists():
        return None
    return _resolve_directory_model_path(latest_training, selector, strict=selector != "best")


def _model_artifact_path(cfg: dict[str, Any], output_dir: Path) -> Path:
    model_cfg = cfg.get("model", {})
    selector = _model_selector(cfg)
    for key in ("artifact_path", "local_model_path"):
        path = _path_from_value(model_cfg.get(key), selector)
        if path is not None:
            return path

    latest_training = _latest_training_pipeline_model(output_dir, selector)
    if latest_training is not None:
        return latest_training
    return default_model_path(output_dir)
