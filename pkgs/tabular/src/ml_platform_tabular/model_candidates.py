from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .model_catalog import validate_model_name


@dataclass(frozen=True)
class ModelCandidate:
    name: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "params": dict(self.params)}


def model_candidates(model_cfg: dict[str, Any]) -> list[ModelCandidate]:
    raw_candidates = model_cfg.get("candidates") or []
    model_params = model_cfg.get("params") or {}
    if not raw_candidates:
        return [_single_candidate(model_cfg, model_params)]
    if not isinstance(raw_candidates, list):
        raise ValueError("model.candidates must be a list of model names or model definitions.")
    return _candidate_list(raw_candidates, model_params)


def _single_candidate(model_cfg: dict[str, Any], model_params: Any) -> ModelCandidate:
    if not isinstance(model_params, dict):
        raise ValueError("model.params must be a mapping.")
    name = validate_model_name(str(model_cfg.get("name", "ridge")))
    return ModelCandidate(name=name, params=dict(model_params))


def _candidate_list(raw_candidates: list[Any], model_params: Any) -> list[ModelCandidate]:
    candidates: list[ModelCandidate] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_candidates):
        candidate = _candidate(item, index, model_params)
        if candidate.name in seen:
            raise ValueError(f"model.candidates contains duplicate model name: {candidate.name}")
        validate_model_name(candidate.name)
        seen.add(candidate.name)
        candidates.append(candidate)
    return candidates


def _candidate(item: Any, index: int, model_params: Any) -> ModelCandidate:
    if isinstance(item, str):
        name = item.strip()
        if not name:
            raise ValueError(f"model.candidates[{index}] must not be empty.")
        return ModelCandidate(name=name, params=_candidate_params(model_params, name))
    if isinstance(item, dict):
        return _candidate_from_mapping(item, index, model_params)
    raise ValueError(f"model.candidates[{index}] must be a model name or mapping.")


def _candidate_from_mapping(item: dict[str, Any], index: int, model_params: Any) -> ModelCandidate:
    name = item.get("name")
    if not name:
        raise ValueError(f"model.candidates[{index}].name is required.")
    name = str(name)
    params = item.get("params")
    if params is None:
        params = _candidate_params(model_params, name)
    if not isinstance(params, dict):
        raise ValueError(f"model.candidates[{index}].params must be a mapping.")
    return ModelCandidate(name=name, params=dict(params))


def _candidate_params(model_params: Any, name: str) -> dict[str, Any]:
    if not model_params:
        return {}
    if not isinstance(model_params, dict):
        raise ValueError("model.params must be a mapping.")
    value = model_params.get(name)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"model.params.{name} must be a mapping.")
    return dict(value)
