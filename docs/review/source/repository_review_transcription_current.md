# パッケージ間の役割整理のご提案

## TL;DR

本PRは、ドメイン実装と実行アダプタの分離という方向性が適切で、将来拡張に耐える土台になっています。

一方で、clearml 実行層にドメイン固有定義が集約されているため、将来のモデリングパッケージ追加時に clearml パッケージも変更しなければならない構造になっており、モデリングパッケージ開発者が本リポジトリで変更すべき層が一貫しないという点が懸念事項です。

改善方針として、以下をご提案させていただきます。

1. `ml_platform_core` は、各パッケージで共通に使う入出力の形と検証ルールを持つ
2. モデリングパッケージ（今回の場合 `ml_platform_tabular`）は、モデリング本体に加え、そのパッケージが何を実行できるかを記した宣言ファイルを持つ
3. 実行層（clearml）は、その宣言を読み取って実行手順に変換する薄いアダプタに徹する

この整理により、保守性と変更容易性を高めつつ、実行層の変更ボトルネックを回避できます。

ここでいう「共通に使う入出力の形」は、実装の約束事を揃えるためのもので、業務ロジックそのものではありません。

また「宣言ファイル」は、どのステージがあり、どのパラメータや成果物を持つかを一覧できるようにするためのものです。

加えて、実装上の語彙は UI 依存ではなく、`runtime_params` や `connected_params` のような実行パラメータ寄りの表現に統一するのがよいです。

## 各課題と提案

### 1. 実行（clearml）層に tabular 固有ロジックが集中している

対象は `pipelines.py` です。

BASIC 系の既定値、ステージ構成、パラメータ解釈を tabular 側へ移し、実行層はその宣言を描画するだけにすると、変更の影響範囲を小さくできます。

### 2. UI 語彙が実装責務を曖昧にしている

対象は `pipelines.py` と `adapter.py` です。

`ui_params` や `ui_value` ではなく `runtime_params` や `connected_params` を使うと、見た目の都合ではなく実行時の受け渡しであることが明確になります。

### 3. 設定契約が暗黙的で、読み手に負担がある

対象は core の `config.py` です。

境界面に型を置いて、入力と出力の形を明示すると、レビューや保守のしやすさが上がります。

### 提案の構造

```text
pkgs/core: 入出力の形と検証ルール
        ↓
pkgs/tabular: 宣言ファイルとドメイン実装
        ↓
runtime/clearml: 実行手順への変換
        ↓
ClearML SDK
```

- core は共通の入出力ルールを持つ
- モデリングパッケージは宣言ファイルで自分の実行内容を記す
- 実行（runtime）層はその宣言を読み、実行系へ変換する（今は `./clearml` ディレクトリですが、実行系を拡張する意図なら `./runtime/clearml` のように階層を増やすといいと思います）

---

# 本件に関するADR

# ADR 0002: Runtime spec and package manifest boundary

## Status

Proposed

## Context

The current repository keeps ClearML SDK imports outside `pkgs/core` and `pkgs/tabular`. That boundary is correct and should remain.

However, the current runtime layer still contains tabular-specific knowledge in the ClearML entrypoints:

- pipeline shape
- stage names
- UI parameter names
- candidate model handling
- ensemble controls

This is acceptable for the first tabular release, but it will become a scaling problem when additional domain packages are added under `pkgs/`, for example:

- image
- audio
- video
- simulation / 3D

If the runtime layer must be edited every time a domain package is added, the ClearML boundary remains technically clean but becomes a change bottleneck.

## Decision

Keep the ClearML runtime outside domain packages, but reduce its domain knowledge.

- `pkgs/core` becomes the home of runtime-facing contracts and typed config models. Here, "contracts" means the shared shape and validation rules of inputs and outputs, not business logic.
- each domain package publishes a small manifest/spec that describes its tasks, stages, parameters, artifacts, and reporting surface. Here, "manifest/spec" means a small declaration file that tells the runtime what the package can run and what it needs.
- the ClearML runtime reads the package manifest/spec and builds the runtime behavior from that declaration.
- `scripts/` remain thin wrappers over package runners or runtime adapters.

This means the long-term target is not "move ClearML into core", but rather:

- keep ClearML as a replaceable runtime adapter
- move contracts into core
- move domain declarations into each package
- make runtime orchestration consume those declarations

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
         task spec / stage spec / UI spec    thin wrappers
                 └───────────────────────────────>
```

## Consequences

### Positive

- adding a new package does not require large runtime rewrites
- package developers can work mainly inside their own package
- ClearML remains optional from the point of view of package code
- config and artifact contracts become explicit and testable
- another runtime can be added later without moving domain logic again

### Negative

- one more explicit abstraction layer must be designed and maintained
- tabular-specific runtime code must be gradually moved behind specs
- typed config introduces migration cost for current dict-based code

## Core contracts

`pkgs/core` should own shared input/output rules and validation, not tabular business logic.

The following classes are the recommended minimum kernel.

### 1. Task and stage contracts

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
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

### 2. Typed config boundary

The highest-value structural improvement is to type the external boundary.

Recommended split:

- `dataclass` for light internal immutable values
- `pydantic` for loading and validating external config inputs

```python
from pydantic import BaseModel, Field


class RuntimeConfig(BaseModel):
    use_clearml: bool = False
    output_dir: str = "outputs"
    clearml_task_id: str | None = None


class SplitConfig(BaseModel):
    method: str = Field(default="random")
    valid_size: float = Field(default=0.2)
    group_column: str | None = None
    time_column: str | None = None
    valid_filter_column: str | None = None
    valid_filter_value: str | None = None


class BaseTaskConfig(BaseModel):
    task: str
    profile: str | None = None
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
```

Each package extends this base model with package-specific config.

### 3. Runtime adapter contract

```python
class RuntimeAdapter(Protocol):
    def prepare_config(self, raw_config: dict[str, Any], task_spec: "TaskSpec") -> "BaseTaskConfig":
        ...

    def resolve_inputs(self, config: "BaseTaskConfig", task_spec: "TaskSpec") -> "BaseTaskConfig":
        ...

    def before_run(self, config: "BaseTaskConfig", task_spec: "TaskSpec") -> None:
        ...

    def report_result(self, result: "RunResult", task_spec: "TaskSpec") -> None:
        ...
```

This keeps ClearML-specific concerns replaceable:

- UI params
- dataset lookup
- artifact URI resolution
- task metadata
- plots and tables upload

## Package manifest

Each domain package should expose one manifest object. The manifest must be small, declarative, and easy to test. In practice, this is the package-side file that lists stages, parameters, default values, and expected artifacts.

### Minimal manifest shape

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

`TaskSpec` is the user-facing runtime unit.

```python
@dataclass(frozen=True)
class TaskSpec:
    key: str
    display_name: str
    config_model: type[BaseTaskConfig]
    runner_path: str
    runtime_features: list[str] = field(default_factory=list)
    parameters: list[ParameterSpec] = field(default_factory=list)
    artifacts: list[ArtifactSpec] = field(default_factory=list)
    stage_specs: list[StageSpec] = field(default_factory=list)
```

## Recommended tabular manifest

The current tabular package can be expressed with a manifest similar to the following.

```python
TABULAR_MANIFEST = PackageManifest(
    domain="tabular",
    version="0.1.0",
    tags=["problem:scalar_regression"],
    task_specs=[
        TaskSpec(
            key="tabular_pipeline",
            display_name="Tabular training pipeline",
            config_model=TabularPipelineConfig,
            runner_path="ml_platform_tabular.pipeline:run_pipeline",
            runtime_features=["pipeline", "clearml_template", "local_run"],
            parameters=TABULAR_PIPELINE_PARAMETERS,
            artifacts=TABULAR_PIPELINE_ARTIFACTS,
            stage_specs=[
                TABULAR_PREPROCESS_STAGE,
                TABULAR_TRAIN_STAGE,
                TABULAR_ENSEMBLE_STAGE,
                TABULAR_EVALUATE_STAGE,
            ],
        ),
        TaskSpec(
            key="tabular_stage",
            display_name="Tabular stage task",
            config_model=TabularStageConfig,
            runner_path="ml_platform_tabular.stage:run_stage",
            runtime_features=["stage", "clearml_internal", "local_run"],
            parameters=TABULAR_STAGE_PARAMETERS,
            artifacts=TABULAR_STAGE_ARTIFACTS,
            stage_specs=[
                TABULAR_PREPROCESS_STAGE,
                TABULAR_TRAIN_STAGE,
                TABULAR_ENSEMBLE_STAGE,
                TABULAR_EVALUATE_STAGE,
            ],
        ),
        TaskSpec(
            key="tabular_infer",
            display_name="Tabular inference",
            config_model=TabularInferConfig,
            runner_path="ml_platform_tabular.infer:run_infer",
            runtime_features=["task", "clearml_template", "local_run"],
            parameters=TABULAR_INFER_PARAMETERS,
            artifacts=TABULAR_INFER_ARTIFACTS,
        ),
    ],
    pipeline_specs=[
        PipelineSpec(
            key="tabular_training_graph",
            display_name="Tabular stage-based training graph",
            stages=[
                TABULAR_PREPROCESS_STAGE,
                TABULAR_TRAIN_STAGE,
                TABULAR_ENSEMBLE_STAGE,
                TABULAR_EVALUATE_STAGE,
            ],
            user_entry_stage="preprocess_features",
            supports_partial_stage_run=True,
        )
    ],
)
```

## Dedicated fix for pipelines.py concentration

`clearml/pipelines.py` currently mixes runtime orchestration with tabular domain policy. The most visible concentration points are:

- tabular default model suites and quality presets
- tabular UI parameter defaults and parameter keys
- tabular stage graph assembly details
- tabular candidate/ensemble-specific override behavior

This section defines how to split those responsibilities while preserving current behavior.

### What moves out of clearml/pipelines.py

| current concern in `clearml/pipelines.py` | destination | ownership |
|---|---|---|
| `BASIC_MODEL_SUITES` | `pkgs/tabular/.../manifest.py` or `policy.py` | tabular package |
| `BASIC_QUALITY_MODES` and `BASIC_QUALITY_MODEL_PARAMS` | `pkgs/tabular/.../manifest.py` or `policy.py` | tabular package |
| `_training_pipeline_ui_params` key defaults | `pkgs/tabular/.../ui_schema.py` | tabular package |
| `_apply_basic_model_suite`, `_apply_basic_quality_mode` | `pkgs/tabular/.../policy.py` | tabular package |
| stage sequence knowledge in `_build_training_plan` | `PipelineSpec` + stage rules in tabular manifest | tabular package |
| generic step rendering (`_stage_step`, `_add_plan_steps`) | runtime adapter renderer | runtime layer |

### What remains in clearml/pipelines.py

Only runtime-vendor concerns remain:

- ClearML SDK and PipelineController interaction
- task draft lifecycle handling
- queue/project/tag metadata application
- script metadata compatibility
- translation from package `PipelineSpec` to ClearML API calls

### Practical split shape

```text
tabular manifest and policy
        ↓
build DomainPlan
        ↓
runtime renderer
        ↓
ClearML PipelineController
```

`DomainPlan` is a runtime-neutral object. It includes step names, parent links, parameter overrides, and expected artifacts, but no ClearML SDK objects.

### Suggested interface

```python
@dataclass(frozen=True)
class DomainStepPlan:
    name: str
    stage_key: str
    parents: list[str]
    parameter_override: dict[str, Any]
    model_name: str | None = None
    ensemble_method: str | None = None


@dataclass(frozen=True)
class DomainPipelinePlan:
    key: str
    version: str
    run_name: str
    stage_queue: str
    controller_queue: str
    steps: list[DomainStepPlan]
    tags: list[str]
```

Tabular package exports a planner.

```python
def build_tabular_domain_plan(
    task_cfg: dict[str, Any],
    profile_cfg: dict[str, Any],
    ui_params: dict[str, Any] | None,
) -> DomainPipelinePlan:
    ...
```

Runtime consumes that plan:

```python
def render_clearml_pipeline(plan: DomainPipelinePlan, runtime_spec: RuntimeRenderSpec) -> Any:
    ...
```

### Why this directly solves tabular leakage

- tabular defaults no longer live in runtime files
- adding another package does not require editing tabular constants in runtime
- runtime can remain stable while package policies evolve independently
- review ownership becomes clear: package policy review and runtime adapter review are separate

## Terminology: replace UI-centric names in code

The implementation should not model itself as a UI application.
In this repository, the so-called UI values are runtime parameter transport values connected through ClearML task fields.

Recommended naming:

- use `runtime_params` or `connected_params` for runtime-facing values
- use `default_params` for package defaults
- reserve `ui_*` wording only for compatibility wrappers or comments tied to specific ClearML screens

This keeps domain and runtime logic neutral and avoids accidental coupling to a specific presentation surface.

## Guardrail for this extraction

After refactor, this check should pass for runtime modules:

- no tabular candidate list constants in runtime adapter files
- no quality preset maps in runtime adapter files
- no package-specific UI key defaults in runtime adapter files

The runtime may still hold neutral key transport helpers such as Args mirroring, but not package policy values.

## Runtime responsibilities after the change

The runtime should consume the manifest, not hardcode tabular behavior.

### Runtime keeps

- ClearML SDK import and compatibility handling
- Task initialization and metadata updates
- parameter connection to UI
- dataset resolution
- artifact download / upload
- queue, project, tag, comment handling
- PipelineController wiring based on `PipelineSpec`

### Runtime no longer owns

- the canonical list of tabular stage names
- package-specific parameter schema
- package-specific artifact schema
- package-specific candidate model semantics
- package-specific pipeline graph encoded as ad hoc conditionals

## Files and ownership

Recommended target placement:

| path | responsibility |
|---|---|
| `pkgs/core/src/ml_platform_core/contracts.py` | `TaskSpec`, `StageSpec`, `ArtifactSpec`, `ParameterSpec` |
| `pkgs/core/src/ml_platform_core/runtime_types.py` | runtime adapter protocols and shared enums |
| `pkgs/core/src/ml_platform_core/config_models.py` | base typed config models |
| `pkgs/tabular/src/ml_platform_tabular/manifest.py` | tabular package manifest |
| `pkgs/tabular/src/ml_platform_tabular/config_models.py` | typed tabular config |
| `clearml/` or future `runtimes/clearml/` | ClearML adapter implementation |
| `scripts/` | thin CLI wrappers only |

## Testing strategy

Testing should follow the same split.

```text
spec validation tests
        ↓
package local runner tests
        ↓
runtime adapter contract tests
        ↓
end-to-end ClearML smoke tests
```

### 1. Spec validation tests

Validate that each manifest is internally consistent.

- every `runner_path` resolves
- every stage key is unique
- required artifacts are declared
- user-facing parameters have supported types

### 2. Package local runner tests

Keep the current local smoke tests and stage tests.

### 3. Runtime adapter contract tests

Test runtime behavior without running a real ClearML server.

- raw UI params to typed config conversion
- dataset/artifact resolution
- stage input placeholder resolution
- metadata mapping from spec to runtime

### 4. End-to-end ClearML smoke tests

Keep a very small number of real ClearML execution checks.

## Migration plan

This should be an incremental refactor, not a rewrite.

### Step 1

Add core contracts and a tabular manifest without changing runtime behavior.

### Step 2

Move pipeline graph constants and parameter declarations from `clearml/pipelines.py` into `ml_platform_tabular/manifest.py`.

This includes all tabular default presets currently concentrated in `clearml/pipelines.py`.

### Step 3

Make the ClearML runtime read the manifest to generate:

- template parameter definitions
- stage graph
- reporting metadata

### Step 4

Introduce typed config models at the boundary of:

- task YAML loading
- profile YAML loading
- UI parameter application

### Step 5

Optionally rename `clearml/` to a clearer runtime path only after synced templates and existing drafts have migrated.

## Rejected alternatives

### Move all ClearML logic into `pkgs/core`

Rejected because it would mix product contracts with one runtime technology.
That would make `core` a harder dependency center instead of a stable kernel.

### Keep current layering and only add more helper functions

Rejected because the central scaling problem is ownership of package-specific knowledge, not only code size.

### Add one runtime implementation per domain package

Rejected as the default because it duplicates operational logic and weakens the benefit of a shared platform. Domain-specific runtime extensions are allowed, but should hang from shared contracts.

## Review checklist

Review this proposal with the following questions.

1. Does `pkgs/core` stay free of runtime-vendor knowledge?
2. Can a new package be added mostly by editing only its own package manifest?
3. Are stage boundaries explicit enough to test locally and remotely?
4. Are config and artifact contracts explicit enough to validate automatically?
5. Does the proposal preserve the current ClearML UX for tabular users?
