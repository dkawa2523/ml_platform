from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from .contracts import DomainPipelinePlan, PackageManifest, TaskSpec
from .result import RunResult


class TaskRunner(Protocol):
    def __call__(self, config: Mapping[str, object]) -> RunResult: ...


class RuntimeAdapter(Protocol):
    def prepare_task_config(
        self,
        raw_config: Mapping[str, object],
        task_spec: TaskSpec,
    ) -> Mapping[str, object]: ...

    def render_pipeline(
        self,
        plan: DomainPipelinePlan,
        manifest: PackageManifest,
    ) -> object: ...

    def report_result(self, result: RunResult, task_spec: TaskSpec) -> None: ...
