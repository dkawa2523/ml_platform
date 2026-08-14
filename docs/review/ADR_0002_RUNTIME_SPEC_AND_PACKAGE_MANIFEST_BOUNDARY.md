# ADR 0002: Runtime spec and package manifest boundary

## Status

Proposed

## Context

現行リポジトリでは、ClearML SDK importを `pkgs/core` と `pkgs/tabular` の外側に置くという境界は妥当です。一方で、ClearML実行層にはtabular固有の知識がまだ残っています。

代表例:

- pipeline shape
- stage names
- runtime parameter names
- candidate model handling
- ensemble controls
- BASIC model suites / quality presets

この状態では、将来 `image`, `audio`, `video`, `simulation / 3D` などのdomain packageを追加するたびに、runtime層も変更する必要があります。技術的にはClearML依存が分離されていても、変更ボトルネックがruntimeに残ります。

## Decision

ClearML runtimeはdomain packageの実装詳細を持たず、domain packageが公開するmanifest/specを読み取って実行手順に変換する薄いadapterに寄せます。

- `pkgs/core`: runtime-facing contracts, typed config models, shared validation
- `pkgs/tabular`: tabular domain implementation, manifest, policy, config models
- `clearml/` または将来の `runtimes/clearml/`: ClearML SDK adapter / renderer
- `scripts/`: thin wrappers only

## Target layering

```text
pkgs/core
contracts and typed config
    ├─────────────────────────────────────────────┐
    │                                             ↓
    └──> pkgs/tabular                       runtime/clearml
         domain implementation              adapter implementation
                 ↓                                 ↓
         package manifest                    scripts
         task spec / stage spec              thin wrappers
                 └───────────────────────────────>
```

## Core contracts minimum kernel

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

StageKind = Literal["preprocess", "train", "ensemble", "evaluate", "infer"]

@dataclass(frozen=True)
class ArtifactSpec:
    name: str
    kind: Literal["file", "table", "plot", "directory", "json"]
    required: bool = True
    description: str = ""

@dataclass(frozen=True)
class ParameterSpec:
    name: str
    group: str
    value_type: Literal["str", "int", "float", "bool", "list", "dict", "enum"]
    required: bool = False
    default: Any = None
    choices: list[str] = field(default_factory=list)
    description: str = ""

@dataclass(frozen=True)
class StageSpec:
    key: str
    kind: StageKind
    display_name: str
    input_artifacts: list[ArtifactSpec] = field(default_factory=list)
    output_artifacts: list[ArtifactSpec] = field(default_factory=list)
    parameters: list[ParameterSpec] = field(default_factory=list)
    supports_local_run: bool = True
    supports_remote_run: bool = True

@dataclass(frozen=True)
class PipelineSpec:
    key: str
    display_name: str
    stages: list[StageSpec]
    user_entry_stage: str | None = None
    supports_partial_stage_run: bool = False

class TaskRunner(Protocol):
    def __call__(self, config: "BaseTaskConfig") -> "RunResult":
        ...
```

## Package manifest shape

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class PackageManifest:
    domain: str
    version: str
    task_specs: list[TaskSpec] = field(default_factory=list)
    pipeline_specs: list[PipelineSpec] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
```

## Dedicated split for `clearml/pipelines.py`

| Current concern | Destination | Owner |
|---|---|---|
| `BASIC_MODEL_SUITES` | `pkgs/tabular/.../manifest.py` or `policy.py` | tabular package |
| `BASIC_QUALITY_MODES` | `pkgs/tabular/.../manifest.py` or `policy.py` | tabular package |
| parameter defaults | `pkgs/tabular/.../parameters.py` or `manifest.py` | tabular package |
| `_apply_basic_model_suite` | `pkgs/tabular/.../policy.py` | tabular package |
| `_apply_basic_quality_mode` | `pkgs/tabular/.../policy.py` | tabular package |
| stage sequence knowledge | `PipelineSpec` + tabular manifest | tabular package |
| generic step rendering | ClearML runtime renderer | runtime layer |

## Terminology

`ui_params` や `ui_value` は、画面そのものではなくClearML task/pipeline parameter transportを表しています。原則として次の語彙へ寄せます。

- `runtime_params`
- `connected_params`
- `default_params`

`ui_*` は互換wrapperやClearML画面に明確に依存するコメントに限定します。

## Runtime keeps

- ClearML SDK import and compatibility handling
- Task initialization and metadata updates
- parameter connection
- dataset resolution
- artifact download / upload
- queue, project, tag, comment handling
- PipelineController wiring based on `PipelineSpec`

## Runtime no longer owns

- canonical list of tabular stage names
- package-specific parameter schema
- package-specific artifact schema
- package-specific candidate model semantics
- package-specific pipeline graph encoded as ad hoc conditionals

## Testing strategy

```text
spec validation tests
        ↓
package local runner tests
        ↓
runtime adapter contract tests
        ↓
end-to-end ClearML smoke tests
```

## Migration plan

1. Add core contracts and a tabular manifest without changing runtime behavior.
2. Move pipeline graph constants and parameter declarations from `clearml/pipelines.py` into `ml_platform_tabular/manifest.py` or `policy.py`.
3. Make the ClearML runtime read the manifest to generate template parameters, stage graph, and reporting metadata.
4. Introduce typed config models at task YAML, profile YAML, and runtime parameter application boundaries.
5. Optionally rename `clearml/` to a clearer runtime path only after synced templates and existing drafts have migrated.

## Review checklist

1. Does `pkgs/core` stay free of runtime-vendor knowledge?
2. Can a new package be added mostly by editing only its own package manifest?
3. Are stage boundaries explicit enough to test locally and remotely?
4. Are config and artifact contracts explicit enough to validate automatically?
5. Does the proposal preserve the current ClearML UX for tabular users?
