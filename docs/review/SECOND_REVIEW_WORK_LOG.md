# Second Review Work Log

## 2026-06-29

- Branch: `cleanup/s00-lean-codebase-audit`
- Worker: Codex
- Purpose: second review triage and response-map creation
- Scope: documentation only; no code changes
- Kubernetes / K8: out of scope

### Commands

```powershell
git status --short
git branch --show-current
git log --oneline --decorate -n 30
Test-Path docs/review/SECOND_REVIEW_MAP.md
Test-Path docs/review/SECOND_REVIEW_WORK_LOG.md
Test-Path docs/review/SECOND_REVIEW_RESPONSE_DRAFTS.md
Get-ChildItem docs/review | Select-Object -ExpandProperty Name | Sort-Object
```

### Required Inputs Read

- `AGENTS.md`
- `docs/review/PR28_REVIEW_MAP.md`
- `docs/review/SIMPLIFICATION_FIX_MAP.md`
- `docs/review/EXTRA_REVIEW_NOTES.md`
- `docs/adr/0002-runtime-spec-and-package-manifest-boundary.md`
- `docs/review/source/repository_review_transcription_current.md`
- `docs/review/source/tabular_package_review_analysis.md`

### Results

- Current branch: `cleanup/s00-lean-codebase-audit`
- Initial working tree: clean
- Latest lean completion commit: `d794986 docs: record lean codebase completion judgment`
- Created `docs/review/SECOND_REVIEW_MAP.md`
- Created `docs/review/SECOND_REVIEW_RESPONSE_DRAFTS.md`
- Created `docs/review/SECOND_REVIEW_WORK_LOG.md`

### SR Triage

| Group | IDs | Status |
|---|---|---|
| P1 | SR01, SR02 | todo |
| P2 | SR03, SR05 | todo |
| P2 deferred | SR04 | deferred |
| P3 | SR06 | todo |
| Deletion gated | SR07, SR08 | needs_confirmation |
| Cleanup | SR09 | todo |
| Tool-backed cleanup | SR10 | needs_confirmation |

### Remaining Items

- Implement SR01 before SR02 if the same files would conflict.
- Keep SR04, SR07, and SR08 gated until external or Remote Agent verification is available.
- Do not mix SR items with the original `R01` through `R27` tracking.
- Do not include Kubernetes / K8 verification in SR scope.

### Next Action

Commit the second review docs with:

```text
docs: add second review response map

Review-Refs: SR01-SR10
Portability: target-repo-sync
```

## 2026-06-29 SR01

- Branch: `cleanup/s00-lean-codebase-audit`
- Worker: Codex
- Purpose: extract ClearML parameter transport mapping
- Scope: SR01 implementation and docs update
- Kubernetes / K8: out of scope

### Commands

```powershell
git status --short
rg -n "default_runtime_params|apply_runtime_params|runtime_params|connected_params|default_params|pipeline_params|Basic/" clearml pkgs tests docs
Get-Content clearml/adapter.py -TotalCount 560
Get-Content clearml/pipelines.py -TotalCount 460
Get-Content pkgs/tabular/src/ml_platform_tabular/policy.py -TotalCount 360
uv run python -m pytest tests/test_clearml_mapping.py -q
uv run python -m ruff check clearml/adapter.py clearml/params.py clearml/pipelines.py tests/test_clearml_mapping.py
```

### Results

- Added `clearml/params.py`.
- Moved ClearML parameter default construction, grouping, connected value coercion, legacy aliases, and nested config application out of `clearml/adapter.py`.
- Kept `adapter.default_runtime_params()`, `adapter.grouped_runtime_params()`, and `adapter.apply_runtime_params()` as thin compatibility wrappers.
- Moved Pipeline Args mirroring and task parameter extraction behind `clearml/params.py` helpers while keeping `pipeline_arg_params()` and `pipeline_params_from_task()` as thin wrappers.
- Kept tabular model-suite and quality-mode policy in `ml_platform_tabular.policy`.
- Added tests for `LEGACY_PARAM_ALIASES`, connected value coercion, unknown-key behavior, and adapter wrapper equivalence.

### Verification

- `uv run python -m pytest tests/test_clearml_mapping.py -q`: passed, 53 tests.
- `uv run python -m ruff check clearml/adapter.py clearml/params.py clearml/pipelines.py tests/test_clearml_mapping.py`: passed.
- `python -m compileall clearml pkgs scripts`: failed because the environment's bare `python` resolves to the Windows Store alias.
- `python -m pytest`: failed for the same bare-`python` alias reason.
- `python -m ruff check .`: failed for the same bare-`python` alias reason.
- `python -m ruff format --check .`: failed for the same bare-`python` alias reason.
- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m pytest`: passed, 122 tests.
- `uv run python -m ruff check .`: passed.
- `uv run python -m ruff format --check .`: failed on existing formatting debt in 11 files unrelated to SR01.

### Remaining Items

- ClearML Remote Agent execution remains manual/out of scope.
- SR02 remains the next P1 item.

## 2026-06-29 SR02

- Branch: `cleanup/s00-lean-codebase-audit`
- Worker: Codex
- Purpose: split tabular evaluation artifact writers
- Scope: SR02 implementation and docs update
- Kubernetes / K8: out of scope

### Commands

```powershell
git status --short
Get-Content pkgs/tabular/src/ml_platform_tabular/training/evaluation.py
Get-ChildItem pkgs/tabular/src/ml_platform_tabular/training -Recurse -File
rg -n "evaluate_model_candidates|leaderboard|decision_summary|best_model|prediction" pkgs/tabular/src tests docs
uv run python -m pytest tests/test_evaluation_artifact_writers.py tests/test_tabular_characterization.py tests/test_pipeline_smoke.py::test_local_training_pipeline_default_graph_and_artifacts
uv run python -m compileall clearml pkgs scripts
uv run python -m pytest
uv run python -m ruff check .
uv run python -m ruff format --check .
```

### Results

- Added `training/leaderboard_artifacts.py` for `leaderboard.csv`, `leaderboard_topk.csv`,
  `metrics_by_candidate.csv`, and leaderboard plots.
- Added `training/prediction_artifacts.py` for `evaluation_predictions.csv`,
  `candidate_predictions.csv`, and prediction/residual plots.
- Added `training/best_model_artifacts.py` for `best_model.joblib` and `best_model.json`.
- Added `training/decision_artifacts.py` for `model_refs.json`, metrics JSON,
  decision summary, evaluation report JSON, and summary tables.
- Reduced `training/evaluation.py` to ranking, best-candidate selection, writer orchestration,
  and `EvaluationResult` assembly.
- Preserved public API compatibility for `evaluate_model_candidates()`.
- Preserved existing artifact names, table names, plot names, report keys, and decision summary keys.
- Added `tests/test_evaluation_artifact_writers.py` for writer-level and public artifact-name checks.

### Verification

- `uv run python -m pytest tests/test_evaluation_artifact_writers.py tests/test_tabular_characterization.py tests/test_pipeline_smoke.py::test_local_training_pipeline_default_graph_and_artifacts`: passed, 7 tests.
- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m pytest`: passed, 125 tests.
- `uv run python -m ruff check .`: passed.
- `uv run python -m ruff format pkgs/tabular/src/ml_platform_tabular/training/evaluation.py pkgs/tabular/src/ml_platform_tabular/training/prediction_artifacts.py pkgs/tabular/src/ml_platform_tabular/training/leaderboard_artifacts.py pkgs/tabular/src/ml_platform_tabular/training/best_model_artifacts.py pkgs/tabular/src/ml_platform_tabular/training/decision_artifacts.py tests/test_evaluation_artifact_writers.py`: reformatted the new leaderboard writer only.
- `uv run python -m ruff format --check .`: failed on known pre-existing formatting debt in 11 unrelated files:
  `pkgs/core/src/ml_platform_core/config.py`, `pkgs/core/src/ml_platform_core/config_models.py`,
  `pkgs/core/src/ml_platform_core/io.py`, `pkgs/tabular/src/ml_platform_tabular/data_quality.py`,
  `pkgs/tabular/src/ml_platform_tabular/ensemble.py`, `pkgs/tabular/src/ml_platform_tabular/features.py`,
  `pkgs/tabular/src/ml_platform_tabular/models.py`, `scripts/make_sample_data.py`,
  `scripts/sync_clearml_templates.py`, `tests/test_config_overrides.py`, and
  `tests/test_pipeline_smoke.py`.

### Remaining Items

- SR03 remains open for ClearML reporting ownership.
- SR05 remains open for config legacy serialization ownership.
- `ruff format --check .` still has known repository formatting debt outside SR02.
- ClearML Remote Agent execution remains manual/out of scope.

## 2026-06-30 SR06

- Branch: `cleanup/s00-lean-codebase-audit`
- Worker: Codex
- Purpose: narrow optional dependency import exceptions
- Scope: SR06 implementation and docs update
- Kubernetes / K8: out of scope

### Commands

```powershell
git status --short
Get-Content pkgs/tabular/src/ml_platform_tabular/models.py -TotalCount 320
rg -n "except Exception" pkgs/tabular/src/ml_platform_tabular/models.py tests
rg -n "OPTIONAL_DEPENDENCY_MODELS|DEPENDENCY_FREE_MODELS|SUPPORTED_MODELS" pkgs/tabular/src tests
uv run python -m pytest tests/test_tabular_smoke.py -k optional_dependency
uv run python -m ruff check pkgs/tabular/src/ml_platform_tabular/models.py tests/test_tabular_smoke.py
python -m compileall clearml pkgs scripts
python -m pytest
python -m ruff check .
python -m ruff format --check .
uv run python -m compileall clearml pkgs scripts
uv run python -m pytest
uv run python -m ruff check .
uv run python -m ruff format --check .
uv run python -m ruff format pkgs/tabular/src/ml_platform_tabular/models.py tests/test_tabular_smoke.py
```

### Results

- Added `OptionalDependencyError` for optional GBM model dependency failures.
- Replaced `except Exception` in `models.py` with narrower dependency catches.
- Optional GBM missing package now raises `OptionalDependencyError` with uv extra,
  editable extra, and ClearML Agent image guidance.
- Optional GBM package import failure now reports that the package could not be
  imported instead of calling it missing.
- Missing estimator class now reports a package/class-version mismatch.
- Unexpected runtime errors during optional import are no longer caught.
- Scikit-learn dependency import catches were also narrowed from `Exception` to
  `ModuleNotFoundError` / `ImportError`.

### Verification

- `uv run python -m pytest tests/test_tabular_smoke.py -k optional_dependency`: passed, 4 tests.
- `uv run python -m ruff check pkgs/tabular/src/ml_platform_tabular/models.py tests/test_tabular_smoke.py`: passed.
- `rg -n "except Exception" pkgs/tabular/src/ml_platform_tabular/models.py tests/test_tabular_smoke.py`: no matches.
- `python -m compileall clearml pkgs scripts`: failed because bare `python` resolves to the Windows Store alias.
- `python -m pytest`: failed for the same bare-`python` alias reason.
- `python -m ruff check .`: failed for the same bare-`python` alias reason.
- `python -m ruff format --check .`: failed for the same bare-`python` alias reason.
- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m pytest`: passed, 128 tests.
- `uv run python -m ruff check .`: passed.
- `uv run python -m ruff format --check .`: failed on known pre-existing formatting debt in 10 unrelated files after formatting `models.py`.

### Remaining Items

- SR03 remains open for ClearML reporting ownership.
- SR05 remains open for config legacy serialization ownership.
- `ruff format --check .` still has repository formatting debt outside SR06.
- ClearML Remote Agent execution remains manual/out of scope.

## 2026-06-30 SR03

- Branch: `cleanup/s00-lean-codebase-audit`
- Worker: Codex
- Purpose: separate ClearML reporting from tabular plotting
- Scope: SR03 implementation and docs update
- Kubernetes / K8: out of scope

### Commands

```powershell
git status --short
Get-Content clearml/reports.py -TotalCount 760
Get-ChildItem pkgs/tabular/src/ml_platform_tabular -Recurse -File | Where-Object { $_.FullName -match "plot" }
rg -n "_report_prediction_plots|prediction_plots|plotly|scatter|histogram|report_" clearml pkgs/tabular/src tests docs
uv run python -m pytest tests/test_clearml_mapping.py -q
uv run python -m ruff check clearml/reports.py tests/test_clearml_mapping.py
uv run python -m ruff format --check clearml/reports.py tests/test_clearml_mapping.py
python -m compileall clearml pkgs scripts
python -m pytest
python -m ruff check .
python -m ruff format --check .
uv run python -m compileall clearml pkgs scripts
uv run python -m pytest
uv run python -m ruff check .
uv run python -m ruff format --check .
rg "_report_prediction_plots|_prediction_vs_actual_figure|_report_leaderboard_dashboard|_leaderboard_pareto_figure|report_plotly\(|report_scatter\(|report_histogram\(" clearml/reports.py
```

### Results

- Removed ClearML-side prediction/leaderboard plot reconstruction from
  `clearml/reports.py`.
- Removed CSV-to-plot helpers such as prediction-vs-actual, residual histogram,
  leaderboard table, top-k score, metric panel, and Pareto figure builders.
- Kept ClearML runtime responsibilities in `clearml/reports.py`: artifact upload,
  table reporting, scalar metric reporting, and reporting existing plot artifacts
  through `report_image` / `report_media`.
- Updated `tests/test_clearml_mapping.py` so `report_result()` is expected to
  report existing plot artifacts and no longer call Plotly/scatter/histogram
  reconstruction paths.
- Kept tabular plot generation ownership in the tabular training/plotting code
  introduced before SR03.

### Verification

- `uv run python -m pytest tests/test_clearml_mapping.py -q`: passed, 53 tests.
- `uv run python -m ruff check clearml/reports.py tests/test_clearml_mapping.py`: passed.
- `uv run python -m ruff format --check clearml/reports.py tests/test_clearml_mapping.py`: passed.
- `python -m compileall clearml pkgs scripts`: failed because bare `python`
  resolves to the Windows Store alias.
- `python -m pytest`: failed for the same bare-`python` alias reason.
- `python -m ruff check .`: failed for the same bare-`python` alias reason.
- `python -m ruff format --check .`: failed for the same bare-`python` alias reason.
- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m pytest`: passed, 128 tests.
- `uv run python -m ruff check .`: passed.
- `uv run python -m ruff format --check .`: failed on known pre-existing formatting
  debt in 10 unrelated files.
- `rg "_report_prediction_plots|_prediction_vs_actual_figure|_report_leaderboard_dashboard|_leaderboard_pareto_figure|report_plotly\(|report_scatter\(|report_histogram\(" clearml/reports.py`:
  no matches.

### Remaining Items

- Manual ClearML UI/Remote Agent reporting verification remains useful but out
  of scope for this local unit-test pass.
- SR05 remains open for config legacy serialization ownership.
- SR09/SR10 remain for docs cleanup and tool-backed unused-code confirmation.

## 2026-06-30 SR05

- Branch: `cleanup/s00-lean-codebase-audit`
- Worker: Codex
- Purpose: move legacy config serialization out of `RunConfig`
- Scope: SR05 implementation and docs update
- Kubernetes / K8: out of scope

### Commands

```powershell
git status --short
Get-Content pkgs/core/src/ml_platform_core/config_models.py -TotalCount 700
rg -n "present_sections|to_dict\(|to_dict\)|RunConfig" pkgs clearml scripts tests docs
uv run python -m pytest tests/test_config_models.py -q
uv run python -m ruff check pkgs/core/src/ml_platform_core/config_models.py pkgs/core/src/ml_platform_core/config_compat.py tests/test_config_models.py
uv run python -m ruff format --check pkgs/core/src/ml_platform_core/config_models.py pkgs/core/src/ml_platform_core/config_compat.py tests/test_config_models.py
uv run python -m ruff format pkgs/core/src/ml_platform_core/config_models.py
python -m compileall clearml pkgs scripts
python -m pytest
python -m ruff check .
python -m ruff format --check .
uv run python -m compileall clearml pkgs scripts
uv run python -m pytest
uv run python -m ruff check .
uv run python -m ruff format --check .
rg -n "present_sections|to_dict\(|to_legacy_dict|get_present_sections" pkgs/core/src/ml_platform_core tests/test_config_models.py docs/review/SECOND_REVIEW_MAP.md docs/review/SECOND_REVIEW_RESPONSE_DRAFTS.md docs/adr/0002-runtime-spec-and-package-manifest-boundary.md
```

### Results

- Added `pkgs/core/src/ml_platform_core/config_compat.py`.
- Moved legacy dict generation and `present_sections` access behind
  `to_legacy_dict()` and `get_present_sections()`.
- Moved section-level legacy serialization into small `*_to_legacy_dict()`
  helpers in `config_compat.py`.
- Kept existing `.to_dict()` methods on `RunConfig` and section models as thin
  compatibility wrappers so existing dict callers are not broken.
- Left `config_models.py` focused on typed field definitions, parsing, and
  validation.
- Added tests that compare `to_legacy_dict()` with existing `.to_dict()` output,
  verify present-section preservation, and prove `RunConfig.to_dict()` delegates
  to `config_compat.to_legacy_dict()`.

### Verification

- `uv run python -m pytest tests/test_config_models.py -q`: passed, 7 tests.
- `uv run python -m ruff check pkgs/core/src/ml_platform_core/config_models.py pkgs/core/src/ml_platform_core/config_compat.py tests/test_config_models.py`: passed.
- `uv run python -m ruff format --check pkgs/core/src/ml_platform_core/config_models.py pkgs/core/src/ml_platform_core/config_compat.py tests/test_config_models.py`: passed after formatting `config_models.py`.
- `python -m compileall clearml pkgs scripts`: failed because bare `python`
  resolves to the Windows Store alias.
- `python -m pytest`: failed for the same bare-`python` alias reason.
- `python -m ruff check .`: failed for the same bare-`python` alias reason.
- `python -m ruff format --check .`: failed for the same bare-`python` alias reason.
- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m pytest`: passed, 130 tests.
- `uv run python -m ruff check .`: passed.
- `uv run python -m ruff format --check .`: failed on known pre-existing formatting
  debt in 9 unrelated files.

### Remaining Items

- `.to_dict()` wrappers remain intentionally for backward compatibility.
- Downstream callers can migrate to `config_compat.to_legacy_dict()` in a later,
  low-risk pass.
- SR09/SR10 remain for docs cleanup and tool-backed unused-code confirmation.

## 2026-06-30 Final Second Review Completion Judgment

- Branch: `cleanup/s00-lean-codebase-audit`
- Worker: Codex
- Purpose: finalize SR01-SR10 response evidence
- Scope: documentation/status finalization only; no new implementation
- Kubernetes / K8: out of scope

### Commands

```powershell
git status --short
git branch --show-current
git log --oneline --decorate -n 50
python -m compileall clearml pkgs scripts
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m pre_commit run --all-files
uv run python -m compileall clearml pkgs scripts
uv run python -m pytest
uv run python -m ruff check .
uv run python -m ruff format --check .
uv run python -m pre_commit run --all-files
rg -n "default_runtime_params|apply_runtime_params|ui_params|ui_value" clearml pkgs tests docs
rg -n "except Exception" pkgs/tabular/src/ml_platform_tabular/models.py clearml pkgs tests
rg -n "_entrypoint_bootstrap|sys\.path|add_clearml_entrypoint_paths" clearml pkgs scripts tests docs
rg -n "present_sections|to_dict\(\)" pkgs/core/src/ml_platform_core tests docs
```

### Results

- Current branch: `cleanup/s00-lean-codebase-audit`.
- P1 items complete: SR01 and SR02 are `done`.
- Implemented P2/P3 items complete: SR03, SR05, and SR06 are `done`.
- SR09 is `done` based on the existing Lean S06/S07 active-docs cleanup.
- SR04 is `deferred` until ClearML Remote Agent direct-entrypoint execution is
  verified.
- SR07 is `deferred` until repo, target-repo, template, and external import
  checks confirm public facades are unused.
- SR08 is `deferred` until Docker, ClearML remote setup, docs setup, CI, and
  onboarding paths are confirmed uv/pyproject-only.
- SR10 is `deferred` until vulture/deptry are run and false positives are
  triaged.

### Verification

- `python -m compileall clearml pkgs scripts`: failed because bare `python`
  resolves to the Windows Store alias.
- `python -m pytest`: failed for the same bare-`python` alias reason.
- `python -m ruff check .`: failed for the same bare-`python` alias reason.
- `python -m ruff format --check .`: failed for the same bare-`python` alias
  reason.
- `python -m pre_commit run --all-files`: failed for the same bare-`python`
  alias reason.
- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m pytest`: passed, 130 tests.
- `uv run python -m ruff check .`: passed.
- `uv run python -m ruff format --check .`: failed on known formatting debt in
  9 unrelated files:
  `pkgs/core/src/ml_platform_core/config.py`,
  `pkgs/core/src/ml_platform_core/io.py`,
  `pkgs/tabular/src/ml_platform_tabular/data_quality.py`,
  `pkgs/tabular/src/ml_platform_tabular/ensemble.py`,
  `pkgs/tabular/src/ml_platform_tabular/features.py`,
  `scripts/make_sample_data.py`,
  `scripts/sync_clearml_templates.py`,
  `tests/test_config_overrides.py`, and `tests/test_pipeline_smoke.py`.
- `uv run python -m pre_commit run --all-files`: failed only in the
  `ruff-format-check` hook for known formatting debt.

### Residual Search Notes

- `default_runtime_params` / `apply_runtime_params` remain as thin compatibility
  wrappers in `clearml/adapter.py`; SR01 moved transport ownership to
  `clearml/params.py`.
- Residual `ui_params` names remain as internal argument names in pipeline
  helper/tests and in review evidence. Removed `default_ui_params`,
  `apply_ui_params`, and `pipeline_ui_params` public wrappers are still absent.
- `except Exception` remains in non-SR06 paths: ClearML SDK version-specific
  handling, optional artifact serialization fallback, and policy quality-mode
  validation. `models.py` optional dependency import broad catches are removed.
- `_entrypoint_bootstrap.py` and direct `sys.path` entrypoint compatibility
  remain intentionally for SR04 pending Remote Agent verification.
- `present_sections` remains as typed metadata and `to_dict()` remains as a
  compatibility wrapper; legacy dict generation is now owned by
  `config_compat.py`.

### Completion

`pass_with_notes`

The second-review implemented scope is complete and locally verified through
`uv run python` compileall, pytest, and ruff check. Remaining items are explicit
deferred deletion/tooling gates, not hidden implementation gaps.
