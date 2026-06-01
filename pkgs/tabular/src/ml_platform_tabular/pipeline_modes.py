from __future__ import annotations

from copy import deepcopy
from typing import Any

PIPELINE_MODES = ("auto", "single", "compare", "ensemble", "optimize")
PIPELINE_MODE_ALIASES = {
    "single_model": "single",
    "comparison": "compare",
    "optimization": "optimize",
}


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


def normalize_pipeline_mode(value: Any) -> str:
    mode = str(value or "auto").strip().lower().replace("-", "_")
    mode = PIPELINE_MODE_ALIASES.get(mode, mode)
    if mode not in PIPELINE_MODES:
        allowed = ", ".join((*PIPELINE_MODES, *PIPELINE_MODE_ALIASES))
        raise ValueError(f"run.pipeline_mode must be one of: {allowed}.")
    return mode


def _has_candidates(model_cfg: dict[str, Any]) -> bool:
    candidates = model_cfg.get("candidates") or []
    if not isinstance(candidates, list):
        raise ValueError("model.candidates must be a list for pipeline execution.")
    return bool(candidates)


def _ensemble_enabled(model_cfg: dict[str, Any]) -> bool:
    ensemble_cfg = model_cfg.get("ensemble") or {}
    if not isinstance(ensemble_cfg, dict):
        raise ValueError("model.ensemble must be a mapping.")
    return as_bool(ensemble_cfg.get("enabled"))


def _search_enabled(model_cfg: dict[str, Any]) -> bool:
    search_cfg = model_cfg.get("search") or {}
    if not isinstance(search_cfg, dict):
        raise ValueError("model.search must be a mapping.")
    return as_bool(search_cfg.get("enabled"))


def _has_search_space(model_cfg: dict[str, Any]) -> bool:
    search_cfg = model_cfg.get("search") or {}
    if not isinstance(search_cfg, dict):
        raise ValueError("model.search must be a mapping.")
    search_space = search_cfg.get("search_space") or {}
    if not isinstance(search_space, dict):
        raise ValueError("model.search.search_space must be a mapping.")
    return bool(search_space)


def infer_pipeline_mode(model_cfg: dict[str, Any]) -> str:
    has_candidates = _has_candidates(model_cfg)
    ensemble_enabled = _ensemble_enabled(model_cfg)
    search_enabled = _search_enabled(model_cfg)
    if search_enabled and ensemble_enabled:
        raise ValueError("run.pipeline_mode=auto cannot combine model.search.enabled=true and model.ensemble.enabled=true.")
    if search_enabled:
        return "optimize"
    if has_candidates and ensemble_enabled:
        return "ensemble"
    if has_candidates:
        return "compare"
    return "single"


def apply_pipeline_mode_defaults(cfg: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    cfg = deepcopy(cfg)
    run_cfg = cfg.setdefault("run", {})
    model_cfg = cfg.setdefault("model", {})
    requested_mode = normalize_pipeline_mode(run_cfg.get("pipeline_mode", "auto"))

    if requested_mode == "ensemble":
        ensemble_cfg = model_cfg.get("ensemble") or {}
        if not isinstance(ensemble_cfg, dict):
            raise ValueError("model.ensemble must be a mapping.")
        ensemble_cfg["enabled"] = True
        model_cfg["ensemble"] = ensemble_cfg
    if requested_mode == "optimize":
        search_cfg = model_cfg.get("search") or {}
        if not isinstance(search_cfg, dict):
            raise ValueError("model.search must be a mapping.")
        search_cfg["enabled"] = True
        model_cfg["search"] = search_cfg

    resolved_mode = infer_pipeline_mode(model_cfg) if requested_mode == "auto" else requested_mode
    _validate_pipeline_mode(resolved_mode, model_cfg)
    run_cfg["pipeline_mode"] = requested_mode
    return resolved_mode, cfg


def _validate_pipeline_mode(mode: str, model_cfg: dict[str, Any]) -> None:
    has_candidates = _has_candidates(model_cfg)
    ensemble_enabled = _ensemble_enabled(model_cfg)
    search_enabled = _search_enabled(model_cfg)

    if search_enabled and ensemble_enabled:
        raise ValueError("Pipeline optimization and ensemble modes cannot be combined in V2.3.")
    if mode == "single":
        if has_candidates or search_enabled or ensemble_enabled:
            raise ValueError("run.pipeline_mode=single cannot use candidates, search, or ensemble settings.")
        return
    if mode == "compare":
        if not has_candidates:
            raise ValueError("run.pipeline_mode=compare requires model.candidates.")
        if search_enabled:
            raise ValueError("run.pipeline_mode=compare cannot use model.search.enabled=true; use optimize.")
        if ensemble_enabled:
            raise ValueError("run.pipeline_mode=compare cannot use model.ensemble.enabled=true; use ensemble.")
        return
    if mode == "ensemble":
        if not has_candidates:
            raise ValueError("run.pipeline_mode=ensemble requires model.candidates.")
        if not ensemble_enabled:
            raise ValueError("run.pipeline_mode=ensemble requires model.ensemble.enabled=true.")
        return
    if mode == "optimize":
        if not search_enabled:
            raise ValueError("run.pipeline_mode=optimize requires model.search.enabled=true.")
        if not _has_search_space(model_cfg):
            raise ValueError("run.pipeline_mode=optimize requires model.search.search_space.")
        return
    raise ValueError(f"Unsupported pipeline mode: {mode!r}")
