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

## CLEAN-1 S01/S02 Deletion Pass

Date: 2026-06-29

Confirmed removals:

- `clearml/adapter.py`
  - removed `as_list()`
  - removed `default_ui_params()`
  - removed `grouped_ui_params()`
  - removed `apply_ui_params()`
- `clearml/pipelines.py`
  - removed `pipeline_ui_params()`
- `clearml/templates.py`
  - removed `_task_ui_params()`

Reason:

- Repository grep showed no production caller for these wrappers.
- Active tests used them only to assert compatibility; tests were migrated to
  the current runtime names.
- The wrappers were one-line aliases to current helpers and did not represent
  ClearML template runner paths, CLI entrypoints, or product behavior.

Post-removal verification:

- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m pytest`: passed, 117 tests.
- `uv run python -m ruff check .`: passed.
- `uv run python -m ruff format --check .`: failed on the pre-existing 16-file
  format debt; no newly edited file remains in the format-failure list.
- `uv run python -m pytest tests/test_clearml_mapping.py`: passed, 49 tests.
- `uv run python -m ruff check clearml tests/test_clearml_mapping.py`: passed.
- `rg "def as_list|def default_ui_params|def grouped_ui_params|def apply_ui_params|def pipeline_ui_params|def _task_ui_params" clearml tests`: no live definitions.
- `python -m ...` commands with the bare `python` launcher failed because this
  workstation resolves `python` to the Windows Store alias.

Not removed in CLEAN-1:

- `clearml/_entrypoint_bootstrap.py`: ClearML direct-entrypoint compatibility
  still needs remote/template confirmation.
- `_set_script_with_compat()` and `_set_pipeline_script_with_compat()`:
  ClearML SDK script metadata compatibility remains a live behavior.
- `_delete_legacy_pipeline_templates()`: still called during pipeline draft sync
  to clean a known old template name.
- `ml_platform_tabular.plots`, `ml_platform_tabular.infer`, and
  `ml_platform_tabular.pipeline`: compatibility facades remain referenced by
  tests, runner paths, `stage.py`, and porting notes.

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

The following one-line UI-named wrappers were removed in CLEAN-1 after
repository references were migrated to the runtime names:

- `as_list()`
- `default_ui_params()`
- `grouped_ui_params()`
- `apply_ui_params()`
- `pipeline_ui_params()`
- `_task_ui_params()`

The remaining wrappers or compatibility surfaces are intentional today, but are
candidates for staged removal after target imports and ClearML execution paths
are confirmed:

- `clearml/pipelines.py`
  - `ui_params` argument naming in build helpers
  - `_set_pipeline_script_with_compat()`
  - `_delete_legacy_pipeline_templates()`
- `clearml/templates.py`
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

The runtime/package manifest boundary is useful, but LEAN-S00 found that the
first scaffold had grown beyond current use. CLEAN-S03 simplified the confirmed
excess:

- Removed `pkgs/core/src/ml_platform_core/runtime_types.py`.
  - `TaskRunner` and `RuntimeAdapter` were Protocols with no concrete
    implementation, no package export, and no runtime caller.
- Trimmed descriptive-only fields from `pkgs/core/src/ml_platform_core/contracts.py`.
  - Removed `description` fields from specs and plans.
  - Removed `StageSpec.supports_local_run` and `supports_remote_run`.
  - Removed `PipelineSpec.entry_stage_key` and `supports_partial_stage_run`.
  - Removed `TaskSpec.runtime_features` and `user_facing`.
  - Removed `DomainStepPlan.tags` and `DomainPipelinePlan.tags`.
- Updated `pkgs/tabular/src/ml_platform_tabular/manifest.py` so the manifest no
  longer passes removed metadata.
- Added a manifest test that pins the current minimal contract surface.

Contracts intentionally retained:

- `ArtifactSpec` and `ParameterSpec` because manifest validation and tests use
  artifact kind, required parameters, defaults, and enum choices.
- `StageSpec`, `TaskSpec`, `PipelineSpec`, and `PackageManifest` because they
  keep runner paths, stage graph keys, and manifest uniqueness testable without
  ClearML.
- `DomainStepPlan` and `DomainPipelinePlan` because ClearML runtime consumes
  them to render the training DAG while tabular keeps graph policy ownership.

Remaining non-S03 cleanup:

- `pkgs/tabular/src/ml_platform_tabular/manifest.py` still combines constants
  and plan construction; track under S05/S08 if it remains hard to read.
- `pkgs/tabular/src/ml_platform_tabular/policy.py` still combines defaults,
  runtime parameter parsing, model-suite policy, and quality-mode application;
  track under S05.
- `clearml/pipelines.py` still converts `DomainPipelinePlan` to its own plan
  dict before rendering; track under S08.

S03 verification:

- `uv run python -m pytest tests/test_runtime_manifest.py`: passed, 10 tests.
- `uv run python -m ruff check pkgs/core/src/ml_platform_core/contracts.py pkgs/tabular/src/ml_platform_tabular/manifest.py tests/test_runtime_manifest.py`: passed.
- `uv run python -m ruff format --check pkgs/core/src/ml_platform_core/contracts.py pkgs/tabular/src/ml_platform_tabular/manifest.py tests/test_runtime_manifest.py`: passed.
- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m pytest`: passed, 118 tests.
- `uv run python -m ruff check .`: passed.
- `uv run python -m ruff format --check .`: failed on the known pre-existing
  16-file format debt.
- The requested bare `python -m ...` validation commands failed because this
  workstation resolves `python` to the Windows Store alias.

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

LEAN-S00 found several broad catches and repeated reporting fallbacks. CLEAN-S04
simplified the confirmed cases:

- `clearml/reports.py`
  - centralized best-effort CSV loading in `_read_csv_or_none()`.
  - narrowed JSON parsing fallback to file, encoding, and JSON decode failures.
  - removed repeated `except Exception: return` blocks around table/dashboard
    CSV reads.
- `clearml/adapter.py`
  - narrowed JSON decoding fallbacks in runtime parameter and stage input
    decoding.
  - added one ClearML logger signature error helper.
  - stopped swallowing non-`TypeError` ClearML logger failures from table,
    plotly, scatter, histogram, media, and image reporting.
  - retained `TypeError` fallbacks only where ClearML SDK logger signatures are
    known to vary.
- `tests/test_clearml_mapping.py`
  - added tests that ClearML logger runtime errors surface instead of silently
    disappearing.
  - added a test that unsupported ClearML logger signatures produce an
    actionable message.

Diagnostics intentionally retained:

- `clearml/templates.py` and `clearml/pipelines.py` dry-run/sync `print()` calls
  remain operator-facing CLI output.
- `clearml_dataset_exists()` keeps a broad `Exception` catch because ClearML SDK
  versions raise different exceptions for missing datasets; runtime import
  failures still surface before that check.

Remaining non-S04 cleanup:

- `clearml/reports.py` still contains Plotly figure construction that overlaps
  conceptually with tabular plotting modules; track under S05/S08 if it remains
  hard to read.
- `clearml/templates.py` and `clearml/pipelines.py` still have separate CLI
  dry-run printers; keep until a shared operator output format is worth the
  extra abstraction.

S04 verification:

- `uv run python -m pytest tests/test_clearml_mapping.py`: passed, 51 tests.
- `uv run python -m ruff check clearml/adapter.py clearml/reports.py tests/test_clearml_mapping.py`: passed.
- `uv run python -m ruff format --check clearml/adapter.py clearml/reports.py tests/test_clearml_mapping.py`: passed.
- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m pytest`: passed, 120 tests.
- `uv run python -m ruff check .`: passed.
- `uv run python -m ruff format --check .`: failed on the known pre-existing
  14-file format debt.
- The requested bare `python -m ...` validation commands failed because this
  workstation resolves `python` to the Windows Store alias.

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
