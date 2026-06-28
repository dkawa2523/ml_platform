# LEAN-S00 Simplification Audit

## Summary

- Date: 2026-06-29 08:23:59 +09:00
- Branch: `cleanup/s00-lean-codebase-audit`
- Worker: Codex
- Purpose: audit the post-review codebase for simplification opportunities without deleting or refactoring code.
- Scope: docs-only audit. Kubernetes / K8 verification is intentionally out of scope.

This audit records candidates for later cleanup. It does not authorize deletion
by itself. Public APIs, ClearML template runner paths, and compatibility facades
are marked `needs_confirmation` until repository users and ClearML remote
execution paths are checked.

`docs/review/source` is evidence from the original review and is not a deletion
candidate.

## Current State

Initial status showed existing uncommitted documentation changes:

```text
 M docs/review/CODEX_WORK_LOG.md
 M docs/review/REVIEW_RESPONSE_DRAFTS.md
```

Those changes predate this audit and should not be mixed into the LEAN-S00
commit unless the user explicitly decides to combine them.

The local `python` launcher is not reliable in this workspace. The successful
verification path is `uv run python ...`.

## Commands And Results

| Command | Result |
|---|---|
| `git status --short` | existing modified review docs plus new audit docs after this work |
| `git branch --show-current` | `cleanup/s00-lean-codebase-audit` |
| `uv run python --version` | Python 3.13.12 |
| `uv run python -m pytest --version` | pytest 9.1.1 |
| `uv run python -m ruff --version` | ruff 0.15.20 |
| `uv run python -m radon --version` | 6.0.1 |
| `uv run python -m vulture --version` | failed: module not installed |
| `uv run python -m deptry --version` | failed: module not installed |
| `uv run python -m compileall clearml pkgs scripts` | passed |
| `uv run python -m pytest` | passed: 117 tests |
| `uv run python -m ruff check .` | passed |
| `uv run python -m ruff format --check .` | failed: 16 files would be reformatted |
| `uv run python -m radon cc clearml pkgs scripts -s -a` | ran; average complexity A (4.92) |
| `uv run python -m radon mi clearml pkgs scripts -s` | ran; several large modules report C maintainability |
| `uv run python -m vulture clearml pkgs scripts tests --min-confidence 70` | failed: module not installed |
| `uv run python -m deptry .` | failed: module not installed |

## Verification Notes

Passing checks:

- `compileall`
- full `pytest` suite: 117 tests
- `ruff check`
- `radon cc`
- `radon mi`

Known failures or unavailable checks:

- `ruff format --check` reports existing broad format debt in 16 files.
- `vulture` is not installed.
- `deptry` is not installed.

No formatting command was run because this audit must not rewrite tracked code.

## Large Files

Largest Python files by line count:

| Lines | File |
|---:|---|
| 1632 | `tests/test_clearml_mapping.py` |
| 938 | `clearml/adapter.py` |
| 732 | `clearml/reports.py` |
| 702 | `clearml/pipelines.py` |
| 471 | `pkgs/core/src/ml_platform_core/config_models.py` |
| 460 | `tests/test_tabular_characterization.py` |
| 406 | `tests/test_pipeline_smoke.py` |
| 378 | `pkgs/tabular/src/ml_platform_tabular/training/evaluation.py` |
| 352 | `pkgs/tabular/src/ml_platform_tabular/manifest.py` |
| 318 | `pkgs/tabular/src/ml_platform_tabular/stage.py` |
| 312 | `pkgs/tabular/src/ml_platform_tabular/policy.py` |
| 303 | `clearml/templates.py` |

The largest files are not automatically deletion candidates. The main concern
is mixed responsibility: adapter parameter mapping plus SDK discovery,
reporting plus Plotly/table rendering, pipeline planning plus ClearML draft
lifecycle, and large compatibility-oriented tests.

## High Complexity Functions

Highest radon cyclomatic complexity findings:

| Rank | Function | File | Grade |
|---:|---|---|---|
| 1 | `apply_runtime_params` | `clearml/adapter.py` | F (60) |
| 2 | `default_runtime_params` | `clearml/adapter.py` | E (39) |
| 3 | `ClearMLAdapter._select_infer_task_artifact` | `clearml/adapter.py` | E (34) |
| 4 | `_report_prediction_plots` | `clearml/reports.py` | D (27) |
| 5 | `evaluate_model_candidates` | `pkgs/tabular/src/ml_platform_tabular/training/evaluation.py` | D (26) |
| 6 | `select_features` | `pkgs/tabular/src/ml_platform_tabular/data.py` | D (23) |
| 7 | `FeatureTransformer.fit` | `pkgs/tabular/src/ml_platform_tabular/features.py` | D (21) |
| 8 | `_model_ref` | `pkgs/tabular/src/ml_platform_tabular/stage.py` | D (21) |
| 9 | `_build_ensemble` | `pkgs/tabular/src/ml_platform_tabular/training/ensemble.py` | D (21) |
| 10 | `_run_training_pipeline` | `pkgs/tabular/src/ml_platform_tabular/training/orchestrator.py` | D (21) |

Secondary complexity clusters:

- `clearml/pipelines.py`: `_build_training_plan`, `_apply_pipeline_template_metadata`, `_render_domain_plan_steps`.
- `pkgs/tabular/src/ml_platform_tabular/policy.py`: runtime default and model-suite conversion helpers.
- `pkgs/tabular/src/ml_platform_tabular/inference/schema.py`: schema summary construction.
- `pkgs/tabular/src/ml_platform_tabular/plotting/*`: plot/table writers with repeated range, label, and image logic.

## Maintainability Index

Radon maintainability index C:

- `clearml/adapter.py`
- `clearml/pipelines.py`
- `clearml/reports.py`
- `pkgs/core/src/ml_platform_core/config_models.py`

Radon maintainability index B:

- `pkgs/tabular/src/ml_platform_tabular/policy.py`

These are priority targets for cleanup after confirmed compatibility coverage.

## Unused Candidates

Confirmed-unused removal is not safe in this prompt because the dedicated
unused-code tools are unavailable:

- `vulture`: not installed
- `deptry`: not installed

Current repository search confirms that the old `Registry` implementation and
`set_dotted_path` alias are already removed from live code. Remaining matches
are in review evidence/docs/tests.

Future cleanup should install or temporarily run unused-code tooling before
deleting live code. Until then, S01 stays `needs_confirmation`.

## Stale Compatibility Layer Candidates

These wrappers or compatibility surfaces are intentional today, but are
candidates for staged removal after target imports and ClearML execution paths
are confirmed:

- `clearml/adapter.py`
  - `as_list()`
  - `default_ui_params()`
  - `grouped_ui_params()`
  - `apply_ui_params()`
- `clearml/pipelines.py`
  - `pipeline_ui_params()`
  - `ui_params` argument naming in build helpers
  - `_set_pipeline_script_with_compat()`
  - `_delete_legacy_pipeline_templates()`
- `clearml/templates.py`
  - `_task_ui_params()`
  - `_set_script_with_compat()`
- `clearml/_entrypoint_bootstrap.py`
  - still required unless direct ClearML `clearml/app.py` and
    `clearml/pipelines.py` execution is replaced or remotely verified.
- `pkgs/tabular/src/ml_platform_tabular/plots.py`
  - compatibility facade for `ml_platform_tabular.plots`.
- `pkgs/tabular/src/ml_platform_tabular/infer.py`
  - compatibility facade for `ml_platform_tabular.infer:run_infer` and private
    helpers used by tests.
- `pkgs/tabular/src/ml_platform_tabular/pipeline.py`
  - compatibility facade for `ml_platform_tabular.pipeline:run_pipeline` and
    private helpers still used by `stage.py` and tests.

Deletion risk is high for ClearML runner paths and external import users. Treat
these as `needs_confirmation`, not immediate delete.

## Excessive Contract Candidates

The runtime/package manifest boundary is useful, but several abstractions are
still single-domain or single-implementation:

- `pkgs/core/src/ml_platform_core/runtime_types.py`
  - `TaskRunner`
  - `RuntimeAdapter`
- `pkgs/core/src/ml_platform_core/contracts.py`
  - broad `ArtifactSpec`, `ParameterSpec`, `StageSpec`, `PipelineSpec`,
    `TaskSpec`, `PackageManifest`, `DomainStepPlan`, `DomainPipelinePlan`
    surface.
- `pkgs/tabular/src/ml_platform_tabular/manifest.py`
  - manifest constants and domain plan builder live together.
- `pkgs/tabular/src/ml_platform_tabular/policy.py`
  - defaults, runtime parameter parsing, model-suite policy, and quality-mode
    application are all in one module.
- `clearml/pipelines.py`
  - runtime consumes `DomainPipelinePlan`, but still has its own plan dict shape
    and ClearML render lifecycle.

These are not immediate deletion candidates. They should be simplified only
after deciding which boundaries are real product extension points.

## Ambiguous Responsibility Files

- `clearml/adapter.py`: ClearML SDK import/shadow handling, project/tag naming,
  parameter conversion, dataset checks, artifact discovery, and reporting
  adapter methods live together.
- `clearml/pipelines.py`: runtime parameter defaults, domain plan rendering,
  plan printing, template draft sync, metadata tagging, and legacy cleanup live
  together.
- `clearml/reports.py`: file reads, metric/table reporting, figure creation,
  leaderboard dashboard rendering, and adapter fallback behavior live together.
- `clearml/templates.py`: template metadata, script setup compatibility,
  parameter defaults, dry-run output, and stale template cleanup live together.
- `pkgs/core/src/ml_platform_core/config_models.py`: parsing, validation,
  unknown-key retention, and dict compatibility serialization are in one large
  module.
- `pkgs/tabular/src/ml_platform_tabular/policy.py`: model suite, quality mode,
  runtime defaults, and config mutation are tightly coupled.
- `pkgs/tabular/src/ml_platform_tabular/training/evaluation.py`: evaluation,
  prediction table writing, leaderboard artifacts, recommendation, and summary
  generation are partially split but still orchestrated in one high-complexity
  function.
- `pkgs/tabular/src/ml_platform_tabular/stage.py`: stage dispatch still imports
  private compatibility helpers from `pipeline.py`.

## Diagnostics, Logging, And Error Handling Duplication

Potential simplification areas:

- `clearml/templates.py` and `clearml/pipelines.py` both contain dry-run/print
  flows and script setup compatibility helpers.
- `clearml/adapter.py` has several ClearML metadata/tag helpers that are similar
  to metadata logic in templates and pipelines.
- `clearml/reports.py` repeats Plotly-like figure dict construction that overlaps
  conceptually with `pkgs/tabular/src/ml_platform_tabular/plotting`.
- CLI-style `print()` calls exist in scripts and ClearML sync/plan functions.
  These are acceptable operator output today, but should be reviewed if a
  unified logging policy is introduced.

## Dependency And Tooling Candidates

- Add or temporarily run `vulture` for confirmed unused-code cleanup.
- Add or temporarily run `deptry` for dependency pruning.
- Decide whether these should become permanent dev dependencies or remain
  ad-hoc audit tools.
- `ruff format --check` debt should be fixed in an isolated formatting cleanup,
  not mixed with simplification or behavior changes.

## Deletion Possibility

Likely deletion candidates after confirmation:

- UI-named compatibility wrappers after all internal and target imports migrate.
- Private helper re-exports from `infer.py` and `pipeline.py` after tests and
  `stage.py` import implementation modules directly.
- `plots.py` facade after external imports are confirmed gone.
- ClearML direct-entrypoint bootstrap only after ClearML remote template
  execution no longer depends on file execution paths.

Not deletion candidates in this audit:

- `docs/review/source/*`
- ClearML template runner paths
- compatibility facades currently referenced by tests or `runners.py`
- `requirements*.txt` compatibility files used by Docker/ClearML/legacy pip
  paths

## Deletion Risk

High-risk areas:

- ClearML SDK compatibility guards and `getattr()` calls.
- Direct `clearml/app.py` and `clearml/pipelines.py` entrypoints.
- `ml_platform_tabular.infer:run_infer` and
  `ml_platform_tabular.pipeline:run_pipeline` runner paths.
- `ml_platform_tabular.plots`, `infer`, and `pipeline` public module imports.
- Existing artifact names, prediction column order, and ClearML parameter keys.

Medium-risk areas:

- Internal private helper imports from compatibility facades.
- Runtime manifest/contracts simplification.
- Report/plot consolidation.

Low-risk areas:

- Documentation cleanup outside evidence files.
- Adding optional audit tooling notes.
- Isolated formatting-only cleanup.

## Recommended Cleanup Order

1. Confirm unused-code tooling approach and run it without committing tool churn.
2. Migrate internal tests and `stage.py` away from private facade imports.
3. Remove stale UI-named wrappers only after target imports are confirmed.
4. Split ClearML adapter/reporting responsibilities behind existing behavior.
5. Simplify manifest/policy/contracts only where a real multi-domain boundary is
   proven.
6. Address ruff formatting debt in a standalone no-behavior commit.
7. Re-run full tests and porting checks.
