# ADR 0002: Runtime spec and package manifest boundary

## Status

Proposed

## Context

The current repository keeps ClearML SDK usage outside `pkgs/core` and
`pkgs/tabular`, which is the right dependency boundary. However, the ClearML
runtime still owns tabular-specific knowledge such as stage names, default
presets, parameter schema, pipeline graph shape, candidate model policy, and
ensemble controls.

That makes the runtime a bottleneck for future domain packages. A new domain
should be able to publish its own manifest and policy without teaching the
ClearML adapter the domain's internal structure.

## Decision

- `pkgs/core` owns runtime-facing contracts, typed config building blocks, and
  shared validation.
- `pkgs/tabular` owns the tabular domain implementation, manifest, policy, and
  config models.
- `clearml/`, or a future `runtimes/clearml/`, owns only the ClearML SDK adapter
  and renderer.
- The runtime consumes domain manifests and converts them into ClearML tasks,
  parameters, stages, and reporting metadata.
- Tabular default presets, stage graph, and parameter schema move toward the
  tabular package instead of living as ad hoc ClearML runtime constants.
- Parameter terminology should move away from broad `ui_*` names. Prefer
  `runtime_params`, `connected_params`, and `default_params`; keep `ui_*` only
  for compatibility wrappers or explicitly UI-bound comments.

## Migration

Migrate incrementally. Add contracts and manifests first, keep current ClearML
behavior compatible, then move tabular constants and policy behind the manifest.
Do not use this ADR as permission for a full rewrite.

Phase 2 dependency/import normalization keeps the current `clearml/` entrypoint
paths for template compatibility. Local scripts should move to uv
workspace-installed imports first; removal of `clearml/_entrypoint_bootstrap.py`
is gated on direct-entrypoint and remote Agent verification.

Phase 3 introduces the first typed config boundary in `pkgs/core` via
dataclass-based models and `parse_run_config()`. Existing dict-returning
`load_run_config()` remains compatible while validating known sections early;
downstream runtime and tabular consumers should migrate to typed accessors
incrementally.

Phase 4-A adds the first runtime-facing contract and tabular package manifest
scaffold. `pkgs/core` now defines `ArtifactSpec`, `ParameterSpec`, `StageSpec`,
`PipelineSpec`, `TaskSpec`, `PackageManifest`, `DomainStepPlan`, and
`DomainPipelinePlan`, plus minimal runtime adapter protocols. `pkgs/tabular`
now owns an initial manifest and policy module for tabular model suites,
quality presets, task/stage declarations, and a ClearML-free domain pipeline
plan builder.

Phase 4-B connects the ClearML runtime to that boundary. Tabular-owned model
suite selection, quality-mode presets, runtime parameter defaults, candidate
normalization, ensemble policy, and training graph construction now live in
`ml_platform_tabular.policy` / `ml_platform_tabular.manifest`. The ClearML
runtime builds a `DomainPipelinePlan` and renders it into existing
`PipelineController` step definitions.

The ClearML runtime still owns runtime-vendor work: SDK access,
`PipelineController` calls, project/queue/tag wiring, task draft lifecycle,
script metadata, artifact reference wiring, and direct `clearml/app.py` /
`clearml/pipelines.py` entrypoint compatibility. ClearML localhost UI, remote
Agent execution, and Kubernetes checks remain manual verification required.

## Consequences

- `pkgs/core` stays free of runtime-vendor knowledge.
- New domain packages can be introduced primarily through their own manifest and
  policy modules.
- The ClearML runtime becomes thinner and easier to test as an adapter.
- Existing ClearML templates and local workflows must remain compatible during
  migration.
