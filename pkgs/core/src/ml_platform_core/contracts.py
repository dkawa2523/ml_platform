from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ArtifactKind = Literal["file", "directory", "json", "table", "plot", "model", "metric"]
ParameterValueType = Literal["str", "int", "float", "bool", "list", "dict", "enum", "json"]
StageKind = Literal["preprocess", "train", "ensemble", "evaluate", "infer"]
TaskKind = Literal["task", "stage", "pipeline"]

ARTIFACT_KINDS: tuple[str, ...] = ("file", "directory", "json", "table", "plot", "model", "metric")
PARAMETER_VALUE_TYPES: tuple[str, ...] = ("str", "int", "float", "bool", "list", "dict", "enum", "json")
STAGE_KINDS: tuple[str, ...] = ("preprocess", "train", "ensemble", "evaluate", "infer")
TASK_KINDS: tuple[str, ...] = ("task", "stage", "pipeline")


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")


def _tuple_text(values: tuple[str, ...] | list[str], field_name: str) -> tuple[str, ...]:
    normalized = tuple(str(value).strip() for value in values)
    empty = [index for index, value in enumerate(normalized) if not value]
    if empty:
        raise ValueError(f"{field_name} contains an empty value at index {empty[0]}.")
    return normalized


def _unique(keys: tuple[str, ...], field_name: str) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for key in keys:
        if key in seen and key not in duplicates:
            duplicates.append(key)
        seen.add(key)
    if duplicates:
        raise ValueError(f"{field_name} must be unique. Duplicates: {', '.join(duplicates)}.")


@dataclass(frozen=True)
class ArtifactSpec:
    name: str
    kind: ArtifactKind
    required: bool = True

    def __post_init__(self) -> None:
        _require_text(self.name, "ArtifactSpec.name")
        if self.kind not in ARTIFACT_KINDS:
            raise ValueError(f"ArtifactSpec.kind must be one of: {', '.join(ARTIFACT_KINDS)}.")


@dataclass(frozen=True)
class ParameterSpec:
    name: str
    value_type: ParameterValueType
    required: bool = False
    default: object | None = None
    choices: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_text(self.name, "ParameterSpec.name")
        if self.value_type not in PARAMETER_VALUE_TYPES:
            raise ValueError(f"ParameterSpec.value_type must be one of: {', '.join(PARAMETER_VALUE_TYPES)}.")
        object.__setattr__(self, "choices", _tuple_text(tuple(self.choices), "ParameterSpec.choices"))
        if self.value_type == "enum" and not self.choices:
            raise ValueError(f"ParameterSpec {self.name!r} has enum type but no choices.")


@dataclass(frozen=True)
class StageSpec:
    key: str
    kind: StageKind
    display_name: str
    runner_path: str
    input_artifacts: tuple[ArtifactSpec, ...] = field(default_factory=tuple)
    output_artifacts: tuple[ArtifactSpec, ...] = field(default_factory=tuple)
    parameters: tuple[ParameterSpec, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_text(self.key, "StageSpec.key")
        if self.kind not in STAGE_KINDS:
            raise ValueError(f"StageSpec.kind must be one of: {', '.join(STAGE_KINDS)}.")
        _require_text(self.display_name, "StageSpec.display_name")
        _require_text(self.runner_path, "StageSpec.runner_path")
        _unique(tuple(artifact.name for artifact in self.input_artifacts), f"StageSpec {self.key!r} input artifacts")
        _unique(tuple(artifact.name for artifact in self.output_artifacts), f"StageSpec {self.key!r} output artifacts")
        _unique(tuple(parameter.name for parameter in self.parameters), f"StageSpec {self.key!r} parameters")


@dataclass(frozen=True)
class PipelineSpec:
    key: str
    display_name: str
    stage_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text(self.key, "PipelineSpec.key")
        _require_text(self.display_name, "PipelineSpec.display_name")
        object.__setattr__(self, "stage_keys", _tuple_text(tuple(self.stage_keys), "PipelineSpec.stage_keys"))
        _unique(self.stage_keys, f"PipelineSpec {self.key!r} stage keys")


@dataclass(frozen=True)
class TaskSpec:
    key: str
    display_name: str
    runner_path: str
    kind: TaskKind = "task"
    parameters: tuple[ParameterSpec, ...] = field(default_factory=tuple)
    artifacts: tuple[ArtifactSpec, ...] = field(default_factory=tuple)
    stage_keys: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_text(self.key, "TaskSpec.key")
        if self.kind not in TASK_KINDS:
            raise ValueError(f"TaskSpec.kind must be one of: {', '.join(TASK_KINDS)}.")
        _require_text(self.display_name, "TaskSpec.display_name")
        _require_text(self.runner_path, "TaskSpec.runner_path")
        object.__setattr__(self, "stage_keys", _tuple_text(tuple(self.stage_keys), "TaskSpec.stage_keys"))
        _unique(tuple(parameter.name for parameter in self.parameters), f"TaskSpec {self.key!r} parameters")
        _unique(tuple(artifact.name for artifact in self.artifacts), f"TaskSpec {self.key!r} artifacts")
        _unique(self.stage_keys, f"TaskSpec {self.key!r} stage keys")


@dataclass(frozen=True)
class PackageManifest:
    domain: str
    version: str
    tasks: tuple[TaskSpec, ...]
    stages: tuple[StageSpec, ...]
    pipelines: tuple[PipelineSpec, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_text(self.domain, "PackageManifest.domain")
        _require_text(self.version, "PackageManifest.version")
        object.__setattr__(self, "tags", _tuple_text(tuple(self.tags), "PackageManifest.tags"))
        stage_keys, task_keys, pipeline_keys = _manifest_key_sets(self)
        _unique(stage_keys, "PackageManifest.stages")
        _unique(task_keys, "PackageManifest.tasks")
        _unique(pipeline_keys, "PackageManifest.pipelines")
        _validate_manifest_reference_keys(self, set(stage_keys))

    def stage(self, key: str) -> StageSpec:
        return self._lookup(self.stages, key, "stage")

    def task(self, key: str) -> TaskSpec:
        return self._lookup(self.tasks, key, "task")

    def pipeline(self, key: str) -> PipelineSpec:
        return self._lookup(self.pipelines, key, "pipeline")

    @staticmethod
    def _lookup(items, key: str, kind: str):
        for item in items:
            if item.key == key:
                return item
        raise KeyError(f"Unknown {kind}: {key}")


def _manifest_key_sets(manifest: PackageManifest) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    return (
        tuple(stage.key for stage in manifest.stages),
        tuple(task.key for task in manifest.tasks),
        tuple(pipeline.key for pipeline in manifest.pipelines),
    )


def _validate_manifest_reference_keys(manifest: PackageManifest, known_stages: set[str]) -> None:
    for task in manifest.tasks:
        _require_known_stage_keys(task.stage_keys, known_stages, f"TaskSpec {task.key!r}")
    for pipeline in manifest.pipelines:
        _require_known_stage_keys(pipeline.stage_keys, known_stages, f"PipelineSpec {pipeline.key!r}")


def _require_known_stage_keys(stage_keys: tuple[str, ...], known_stages: set[str], owner: str) -> None:
    missing = [key for key in stage_keys if key not in known_stages]
    if missing:
        raise ValueError(f"{owner} references unknown stage keys: {missing}.")


@dataclass(frozen=True)
class DomainStepPlan:
    name: str
    stage_key: str
    parents: tuple[str, ...] = field(default_factory=tuple)
    parameter_overrides: dict[str, object] = field(default_factory=dict)
    expected_artifacts: tuple[str, ...] = field(default_factory=tuple)
    model_name: str | None = None
    ensemble_method: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.name, "DomainStepPlan.name")
        _require_text(self.stage_key, "DomainStepPlan.stage_key")
        object.__setattr__(self, "parents", _tuple_text(tuple(self.parents), "DomainStepPlan.parents"))
        object.__setattr__(
            self,
            "expected_artifacts",
            _tuple_text(tuple(self.expected_artifacts), "DomainStepPlan.expected_artifacts"),
        )


@dataclass(frozen=True)
class DomainPipelinePlan:
    key: str
    version: str
    run_name: str
    steps: tuple[DomainStepPlan, ...]

    def __post_init__(self) -> None:
        _require_text(self.key, "DomainPipelinePlan.key")
        _require_text(self.version, "DomainPipelinePlan.version")
        _require_text(self.run_name, "DomainPipelinePlan.run_name")
        if not self.steps:
            raise ValueError("DomainPipelinePlan.steps must contain at least one step.")
        step_names = tuple(step.name for step in self.steps)
        _unique(step_names, f"DomainPipelinePlan {self.key!r} steps")
        known_steps = set(step_names)
        for step in self.steps:
            missing = [parent for parent in step.parents if parent not in known_steps]
            if missing:
                raise ValueError(f"DomainStepPlan {step.name!r} references unknown parents: {missing}.")
