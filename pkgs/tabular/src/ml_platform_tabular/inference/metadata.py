from __future__ import annotations

from pathlib import Path
from typing import Any

from ml_platform_core.io import load_joblib, read_json


def _json_path(cfg: dict[str, Any], key: str) -> Path | None:
    value = cfg.get("model", {}).get(key)
    return Path(value) if value else None


def _read_json_if_exists(path: Path | None) -> dict[str, Any]:
    if path is not None and path.exists():
        return read_json(path)
    return {}


def _model_info_path(cfg: dict[str, Any], model_path: Path) -> Path | None:
    value = cfg.get("model", {}).get("info_path")
    if value:
        return Path(value)
    if model_path.name.startswith("model_") and model_path.suffix == ".joblib":
        method = model_path.stem.replace("model_", "", 1)
        for candidate in (
            model_path.parent / f"model_info_{method}.json",
            model_path.parent / f"ensemble_info_{method}.json",
        ):
            if candidate.exists():
                return candidate
    for candidate in (
        model_path.parent / "model_info.json",
        model_path.parent / "best_model.json",
        model_path.parent / "ensemble_info.json",
    ):
        if candidate.exists():
            return candidate
    return None


def _load_model_info(cfg: dict[str, Any], model_path: Path) -> dict[str, Any]:
    info_path = _model_info_path(cfg, model_path)
    return read_json(info_path) if info_path else {}


def _feature_spec_path(cfg: dict[str, Any], model_path: Path) -> Path | None:
    explicit = _json_path(cfg, "feature_spec_path")
    if explicit:
        return explicit
    for candidate in (
        model_path.parent / "feature_spec.json",
        model_path.parent.parent / "preprocess_features" / "feature_spec.json",
    ):
        if candidate.exists():
            return candidate
    return None


def _preprocess_bundle_path(cfg: dict[str, Any], model_path: Path) -> Path | None:
    explicit = _json_path(cfg, "preprocess_bundle_path")
    if explicit:
        return explicit
    for candidate in (
        model_path.parent / "preprocess_bundle.joblib",
        model_path.parent.parent / "preprocess_features" / "preprocess_bundle.joblib",
    ):
        if candidate.exists():
            return candidate
    return None


def _load_feature_spec(cfg: dict[str, Any], model_path: Path) -> dict[str, Any]:
    return _read_json_if_exists(_feature_spec_path(cfg, model_path))


def _load_preprocess_bundle(cfg: dict[str, Any], model_path: Path) -> dict[str, Any]:
    path = _preprocess_bundle_path(cfg, model_path)
    if path is None or not path.exists():
        return {}
    bundle = load_joblib(path)
    return bundle if isinstance(bundle, dict) else {}


def _known_target_column(
    cfg: dict[str, Any],
    feature_spec: dict[str, Any],
    model_info: dict[str, Any],
    preprocess_bundle: dict[str, Any],
) -> str | None:
    for value in (
        cfg.get("data", {}).get("target_column"),
        feature_spec.get("target_column"),
        model_info.get("target_column"),
        preprocess_bundle.get("target_column"),
    ):
        if value:
            return str(value)
    return None


def _feature_preset(
    feature_spec: dict[str, Any],
    model_info: dict[str, Any],
    preprocess_bundle: dict[str, Any],
) -> str | None:
    for value in (
        feature_spec.get("feature_preset"),
        model_info.get("feature_preset"),
        preprocess_bundle.get("feature_preset"),
    ):
        if value:
            return str(value)
    return None
