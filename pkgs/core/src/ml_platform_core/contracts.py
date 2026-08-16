"""Small manifest records shared by the product and ClearML adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypeVar

ParameterValueType = Literal["str", "int", "float", "bool", "list", "dict", "enum", "json"]


@dataclass(frozen=True)
class ArtifactSpec:
    name: str


@dataclass(frozen=True)
class ParameterSpec:
    name: str
    value_type: ParameterValueType
    config_path: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class StageSpec:
    key: str
    parameters: tuple[ParameterSpec, ...] = field(default_factory=tuple)
    output_artifacts: tuple[ArtifactSpec, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TaskSpec:
    key: str
    parameters: tuple[ParameterSpec, ...] = field(default_factory=tuple)


_Spec = TypeVar("_Spec", StageSpec, TaskSpec)


@dataclass(frozen=True)
class PackageManifest:
    version: str
    tasks: tuple[TaskSpec, ...]
    stages: tuple[StageSpec, ...]

    def stage(self, key: str) -> StageSpec:
        return _lookup(self.stages, key, "stage")

    def task(self, key: str) -> TaskSpec:
        return _lookup(self.tasks, key, "task")


def _lookup(items: tuple[_Spec, ...], key: str, kind: str) -> _Spec:
    for item in items:
        if item.key == key:
            return item
    raise KeyError(f"Unknown {kind}: {key}")


@dataclass(frozen=True)
class DomainStepPlan:
    name: str
    stage_key: str
    parents: tuple[str, ...] = field(default_factory=tuple)
    parameter_overrides: dict[str, object] = field(default_factory=dict)
    expected_artifacts: tuple[str, ...] = field(default_factory=tuple)
    model_name: str | None = None
    ensemble_method: str | None = None


@dataclass(frozen=True)
class DomainPipelinePlan:
    key: str
    version: str
    run_name: str
    steps: tuple[DomainStepPlan, ...]
