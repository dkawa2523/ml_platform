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
  `ml_platform_tabular.pipeline`: public compatibility facades remain for
  external imports and runner paths. CLEAN-4 removed private helper re-exports
  from `infer.py` / `pipeline.py` after moving repo-internal imports to
  implementation modules.

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
  - public compatibility facade for `ml_platform_tabular.plots`; repo-internal
    tests now import the canonical `ml_platform_tabular.plotting` package.
- `pkgs/tabular/src/ml_platform_tabular/infer.py`
  - thin compatibility facade for `ml_platform_tabular.infer:run_infer`.
- `pkgs/tabular/src/ml_platform_tabular/pipeline.py`
  - thin compatibility facade for `ml_platform_tabular.pipeline:run_pipeline`,
    `evaluate_model_candidates`, and `EvaluationResult`.

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
- `pkgs/tabular/src/ml_platform_tabular/stage.py`: CLEAN-4 removed the import
  dependency on private `pipeline.py` re-exports. The file still owns stage
  dispatch plus artifact-ref loading and may be split later only if call sites
  become clearer.

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

CLEAN-5 dependency decision:

- No dependencies were removed because `deptry` is not installed in the current
  uv environment.
- `requirements.txt`, `requirements-dev.txt`, and
  `docs/ml_platform_mkdocs/requirements-docs.txt` remain compatibility files for
  Docker, ClearML remote setup, docs-only environments, and legacy pip flows.
- Active setup docs now present `uv sync --group dev`, `uv sync --group docs`,
  and `uv run python ...` as the default commands.

## Active Docs Cleanup

CLEAN-5 pruned current-facing docs outside `docs/review/source`:

- Replaced old direct `python scripts/...` and `pytest -q` examples with
  `uv run python ...` commands.
- Replaced the old MkDocs setup command with `uv sync --group docs` and
  `uv run --group docs python -m mkdocs ...`.
- Rewrote the MkDocs repository-structure, development-guidelines,
  add-model, add-feature-or-metric, model-reference, and environment pages to
  describe the current `training`, `inference`, and `plotting` package layout.
- Shortened `clearml/README.md` and `docs/CODEX_HANDOFF.md` so active docs no
  longer explain low-level `sys.path` mechanics.
- Kept review evidence and historical review-response docs intact.

Verification:

- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m pytest`: passed, 120 tests.
- `uv run python -m ruff check .`: passed.
- `uv run --group docs python -m mkdocs build --config-file docs\ml_platform_mkdocs\mkdocs.yml --strict`:
  passed.
- `uv run python -m deptry .`: failed because `deptry` is not installed, so
  dependency deletion remains `needs_confirmation`.
- `uv run python -m ruff format --check .`: failed on known formatting debt
  outside this docs cleanup.

## Deletion Possibility

Removed or narrowed in CLEAN-4:

- Private helper re-exports from `infer.py` and `pipeline.py`.
- Repo-internal test imports from `ml_platform_tabular.plots`.
- Duplicated `importlib.util.spec_from_file_location()` bootstrap loaders in
  `clearml/app.py`, `clearml/pipelines.py`, and `clearml/templates.py`.

Likely deletion candidates after confirmation:

- UI-named compatibility wrappers after all internal and target imports migrate.
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

## CLEAN-S05/S08/S09 Verification

CLEAN-4 narrowed the confirmed facade and entrypoint cleanup:

- `stage.py` now imports tabular training helpers from `training.*` modules
  instead of private `pipeline.py` re-exports.
- Inference, decision-summary, and plot tests now import implementation
  modules directly where they exercise private helpers.
- `infer.py` now exposes only `run_infer`.
- `pipeline.py` now exposes only `run_pipeline`,
  `evaluate_model_candidates`, and `EvaluationResult`.
- `plots.py` remains as a public plotting compatibility facade.
- ClearML direct entrypoints still call `_entrypoint_bootstrap.py`, but the
  duplicate `importlib.util` loader function was removed from each entrypoint.

Verification:

- `uv run python -m pytest tests/test_infer_schema_check.py tests/test_decision_summary.py tests/test_tabular_plots.py`: passed, 9 tests.
- `uv run python -m pytest tests/test_stage_smoke.py tests/test_tabular_characterization.py tests/test_runtime_manifest.py`: passed, 15 tests.
- `uv run python -m pytest tests/test_clearml_mapping.py`: passed, 51 tests.
- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m pytest`: passed, 120 tests.
- `uv run python -m ruff check .`: passed.
- `uv run python -m ruff format --check` on changed code/test files: passed.
- `uv run python -m ruff format --check .`: failed on the known remaining
  11-file format debt outside this cleanup.

## Recommended Cleanup Order

1. Confirm unused-code tooling approach and run it without committing tool churn.
2. Keep public facades and ClearML direct-entrypoint bootstrap until external
   imports and remote Agent execution are confirmed.
3. Confirm dependency pruning with `deptry` or equivalent before deleting any
   dependency files or package entries.
4. Split ClearML adapter/reporting responsibilities behind existing behavior.
5. Simplify manifest/policy/contracts only where a real multi-domain boundary is
   proven.
6. Address ruff formatting debt in a standalone no-behavior commit.
7. Re-run full tests and porting checks.

## Final Lean Completion Summary

Date: 2026-06-29

Completion: `pass_with_notes`

Main removals:

- Removed confirmed stale one-line UI-named wrappers:
  `as_list`, `default_ui_params`, `grouped_ui_params`, `apply_ui_params`,
  `pipeline_ui_params`, and `_task_ui_params`.
- Removed the unused `ml_platform_core.runtime_types` Protocol scaffold.
- Removed descriptive-only contract fields that were not consumed by runtime,
  manifest validation, artifacts, or tests.
- Removed private helper re-exports from `ml_platform_tabular.infer` and
  `ml_platform_tabular.pipeline`.
- Removed duplicated `spec_from_file_location()` bootstrap loader functions
  from ClearML direct entrypoints.

Main simplifications:

- Tabular internals now import canonical implementation modules under
  `training`, `inference`, and `plotting` instead of private helpers from old
  facade modules.
- ClearML reporting now separates best-effort artifact parsing from ClearML
  logger runtime failures.
- Active setup and architecture docs now use `uv sync` / `uv run` and describe
  the current package layout.
- Requirements files are documented as compatibility inputs rather than the
  primary dependency source of truth.

Compatibility layers intentionally retained:

- `ml_platform_tabular.infer:run_infer`
- `ml_platform_tabular.pipeline:run_pipeline`
- `ml_platform_tabular.pipeline:evaluate_model_candidates`
- `ml_platform_tabular.pipeline:EvaluationResult`
- `ml_platform_tabular.plots`
- ClearML direct entrypoints: `clearml/app.py`, `clearml/pipelines.py`, and
  `clearml/templates.py`
- `clearml/_entrypoint_bootstrap.py`
- ClearML SDK shadow guard and script metadata compatibility helpers
- `requirements*.txt` compatibility files

Reasons retained:

- External imports were not audited outside this repository.
- ClearML remote Agent/template execution was not verified in this cleanup.
- Docker, ClearML remote setup, docs-only setup, and legacy pip environments may
  still use requirements files.
- Existing ClearML artifact names, parameter keys, runner paths, and prediction
  output contracts must remain stable.

Future deletion candidates after confirmation:

- Public tabular facade modules after target repositories migrate to
  `training`, `inference`, and `plotting` imports.
- `clearml/_entrypoint_bootstrap.py` after remote template execution no longer
  depends on direct file execution.
- Requirements compatibility files after Docker/ClearML/docs setup no longer
  consumes them.
- Additional unused code after `vulture` or equivalent tooling is available.
- Dependency entries after `deptry` or manual import proof is available.

Final verification:

- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m pytest`: passed, 120 tests.
- `uv run python -m ruff check .`: passed.
- `uv run python -m radon cc clearml pkgs scripts -s -a`: passed; average
  complexity A.
- `uv run python -m ruff format --check .`: failed on known 11-file formatting
  debt.
- `uv run python -m pre_commit run --all-files`: failed only on the same ruff
  format-check debt.
- `uv run python -m vulture ...`: unavailable.
- `uv run python -m deptry .`: unavailable.
- Bare `python -m ...` commands failed because this workstation resolves
  `python` to the Windows Store alias.

Target repo porting notes:

- Port Lean cleanup commits after the PR review-response commits.
- Keep compatibility facades unless target import searches prove they are
  unused.
- Keep ClearML direct entrypoints and `_entrypoint_bootstrap.py` until remote
  template execution is verified in the target environment.
- Keep requirements compatibility files unless target Docker/ClearML/docs setup
  has fully moved to uv groups.
- Do not include Kubernetes / K8 verification in this Lean cleanup port.
