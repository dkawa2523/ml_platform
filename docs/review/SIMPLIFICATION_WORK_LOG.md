# Simplification Work Log

## 2026-06-29 - LEAN-S00 audit

- Date: 2026-06-29 08:23:59 +09:00
- Branch: `cleanup/s00-lean-codebase-audit`
- Worker: Codex
- Purpose: add a lean-codebase simplification audit without code deletion,
  implementation refactors, or Kubernetes / K8 work.

## Changed Files

- `docs/review/SIMPLIFICATION_AUDIT.md`
- `docs/review/SIMPLIFICATION_FIX_MAP.md`
- `docs/review/SIMPLIFICATION_WORK_LOG.md`
- `docs/adr/0003-lean-codebase-guidelines.md`

Pre-existing modified files were intentionally not edited by this audit:

- `docs/review/CODEX_WORK_LOG.md`
- `docs/review/REVIEW_RESPONSE_DRAFTS.md`

## Commands

```powershell
git status --short
git branch --show-current
git log --oneline -n 8
uv run python --version
uv run python -m pytest --version
uv run python -m ruff --version
uv run python -m radon --version
uv run python -m vulture --version
uv run python -m deptry --version
uv run python -m compileall clearml pkgs scripts
uv run python -m pytest
uv run python -m ruff check .
uv run python -m ruff format --check .
uv run python -m radon cc clearml pkgs scripts -s -a
uv run python -m radon mi clearml pkgs scripts -s
uv run python -m vulture clearml pkgs scripts tests --min-confidence 70
uv run python -m deptry .
rg -n "TODO|FIXME|deprecated|Backward-compatible|compat|legacy|unused|YAGNI|temporary|workaround" clearml pkgs scripts tests docs
rg -n "Any|getattr\(|setattr\(|globals\(\)|locals\(\)|importlib|sys\.path|__getattr__" clearml pkgs scripts tests
rg -n "ui_params|ui_value|default_ui_params|pipeline_ui_params" clearml pkgs scripts tests docs
rg -n "Registry|Provider|Protocol|Manifest|Spec|Contract" pkgs clearml scripts tests docs
rg -n "print\(" clearml pkgs scripts tests
```

## Results

- Branch: `cleanup/s00-lean-codebase-audit`
- Python via uv: 3.13.12
- pytest: 9.1.1
- ruff: 0.15.20
- radon: 6.0.1
- `compileall`: passed
- `pytest`: passed, 117 tests
- `ruff check`: passed
- `ruff format --check`: failed because 16 existing files would be reformatted
- `radon cc`: ran, average complexity A
- `radon mi`: ran, C maintainability for `clearml/adapter.py`,
  `clearml/pipelines.py`, `clearml/reports.py`, and
  `pkgs/core/src/ml_platform_core/config_models.py`
- `vulture`: unavailable
- `deptry`: unavailable

## Findings

- Large-file pressure remains in ClearML runtime modules and mapping tests.
- Highest complexity is concentrated in adapter parameter handling, ClearML
  report generation, tabular evaluation, feature selection, ensemble building,
  and orchestration.
- Compatibility wrappers and facades are present by design and should not be
  removed before external import and ClearML template compatibility checks.
- The R18 contract/manifest boundary is useful but may be broader than current
  one-domain usage requires.
- Unused-code deletion needs `vulture`, `deptry`, or equivalent confirmation.
- `ruff format --check` debt should be isolated from behavior cleanup.

## Failures / Unknowns

- `uv run python -m vulture ...`: failed because `vulture` is not installed.
- `uv run python -m deptry .`: failed because `deptry` is not installed.
- `uv run python -m ruff format --check .`: failed on pre-existing format
  debt in 16 files.
- ClearML remote execution and external imports were not verified in this audit.
- Kubernetes / K8 verification was intentionally not performed.

## Next Action

Start CLEAN-1 with S06 or S09:

1. Decide whether to add or temporarily run `vulture` / `deptry`.
2. Migrate internal tabular tests and `stage.py` away from private facade
   imports.
3. Keep all facade and ClearML runner path removals gated by confirmation.

## 2026-06-29 - CLEAN-1 confirmed stale wrapper removal

- Date: 2026-06-29
- Branch: `cleanup/s00-lean-codebase-audit`
- Worker: Codex
- Purpose: remove confirmed one-line stale compatibility wrappers under S01/S02
  without touching public runner paths, ClearML template entrypoints,
  `docs/review/source`, or Kubernetes / K8 assets.

## Changed Files

- `clearml/adapter.py`
- `clearml/pipelines.py`
- `clearml/templates.py`
- `tests/test_clearml_mapping.py`
- `docs/review/SIMPLIFICATION_AUDIT.md`
- `docs/review/SIMPLIFICATION_FIX_MAP.md`
- `docs/review/SIMPLIFICATION_WORK_LOG.md`

Pre-existing modified files from earlier review-document work remain separate:

- `docs/review/CODEX_WORK_LOG.md`
- `docs/review/REVIEW_RESPONSE_DRAFTS.md`

## Commands

```powershell
git status --short
git branch --show-current
rg -n "Backward-compatible|compat|deprecated|legacy|temporary|workaround" clearml pkgs scripts tests docs
rg -n "Registry|set_dotted_path|as_list|default_ui_params|grouped_ui_params|apply_ui_params|pipeline_ui_params|_task_ui_params|_ui_value" .
uv run python -m vulture clearml pkgs scripts tests --min-confidence 80
uv run python -m ruff check .
git grep -n "default_ui_params\|grouped_ui_params\|apply_ui_params\|pipeline_ui_params\|_task_ui_params\|as_list" -- ':!docs/review/source/*'
uv run python -m pytest tests/test_clearml_mapping.py
uv run python -m ruff check clearml tests/test_clearml_mapping.py
rg -n "def as_list|def default_ui_params|def grouped_ui_params|def apply_ui_params|def pipeline_ui_params|def _task_ui_params" clearml tests
uv run python -m compileall clearml pkgs scripts
uv run python -m pytest
uv run python -m ruff check .
uv run python -m ruff format --check .
uv run python -m vulture clearml pkgs scripts tests --min-confidence 80
python -m compileall clearml pkgs scripts
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m vulture clearml pkgs scripts tests --min-confidence 80
```

## Results

- Removed confirmed one-line wrappers:
  - `as_list`
  - `default_ui_params`
  - `grouped_ui_params`
  - `apply_ui_params`
  - `pipeline_ui_params`
  - `_task_ui_params`
- Migrated active tests to current runtime helper names.
- Added assertions that removed wrapper names are no longer exposed from the
  ClearML adapter/pipeline modules.
- `uv run python -m pytest tests/test_clearml_mapping.py`: passed, 49 tests.
- `uv run python -m ruff check clearml tests/test_clearml_mapping.py`: passed.
- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m pytest`: passed, 117 tests.
- `uv run python -m ruff check .`: passed.
- `uv run python -m ruff format --check .`: failed only on the pre-existing
  16-file format debt; `tests/test_clearml_mapping.py` was manually adjusted so
  this patch does not add new format debt.
- The uv-managed interpreter remains the verified path for Python commands in
  this workstation.

## Failures / Unknowns

- `uv run python -m vulture ...`: failed because `vulture` is not installed.
- Bare `python -m compileall`, `python -m pytest`, `python -m ruff check`,
  `python -m ruff format --check`, and `python -m vulture` failed with exit
  9009 because the `python` command resolves to the Windows Store alias in this
  workstation.
- Broad unused-code deletion remains `needs_confirmation`.
- ClearML direct-entrypoint bootstrap, script metadata compatibility helpers,
  and tabular compatibility facades were not removed because they are referenced
  by active runtime paths, tests, porting notes, or require external ClearML
  remote confirmation.

## Next Action

CLEAN-2 should focus on one of:

1. S09: migrate internal tabular tests and `stage.py` away from private facade
   helper imports.
2. S06: decide whether `vulture` / `deptry` should be temporary audit tools or
   permanent dev dependencies.
3. S04: simplify duplicated ClearML diagnostics and reporting helpers with
   behavior-preserving tests.

## 2026-06-29 - CLEAN-S03 runtime contract surface simplification

- Date: 2026-06-29
- Branch: `cleanup/s00-lean-codebase-audit`
- Worker: Codex
- Purpose: simplify excessive runtime contracts while preserving the
  runtime/package manifest boundary and excluding Kubernetes / K8 work.

## Changed Files

- `pkgs/core/src/ml_platform_core/contracts.py`
- `pkgs/core/src/ml_platform_core/runtime_types.py`
- `pkgs/tabular/src/ml_platform_tabular/manifest.py`
- `tests/test_runtime_manifest.py`
- `docs/review/SIMPLIFICATION_AUDIT.md`
- `docs/review/SIMPLIFICATION_FIX_MAP.md`
- `docs/review/SIMPLIFICATION_WORK_LOG.md`
- `docs/adr/0002-runtime-spec-and-package-manifest-boundary.md`
- `docs/adr/0003-lean-codebase-guidelines.md`

## Commands

```powershell
git status --short
rg -n "class .*Spec|class .*Contract|class .*Protocol|Protocol\)|PackageManifest|TaskSpec|StageSpec|ArtifactSpec|ParameterSpec|RunResult|DomainPipelinePlan|DomainStepPlan" pkgs clearml tests docs
rg -n "runtime_types|contracts|manifest|policy" pkgs clearml tests docs
uv run python -m pytest tests/test_runtime_manifest.py
uv run python -m ruff check pkgs/core/src/ml_platform_core/contracts.py pkgs/tabular/src/ml_platform_tabular/manifest.py tests/test_runtime_manifest.py
uv run python -m ruff format --check pkgs/core/src/ml_platform_core/contracts.py pkgs/tabular/src/ml_platform_tabular/manifest.py tests/test_runtime_manifest.py
python -m compileall clearml pkgs scripts
python -m pytest
python -m ruff check .
python -m ruff format --check .
uv run python -m compileall clearml pkgs scripts
uv run python -m pytest
uv run python -m ruff check .
uv run python -m ruff format --check .
rg -n "runtime_types|runtime_features|supports_local_run|supports_remote_run|entry_stage_key|supports_partial_stage_run|description=|\.description|DomainStepPlan\.tags|DomainPipelinePlan\.tags" pkgs tests clearml docs/adr docs/review/SIMPLIFICATION_AUDIT.md docs/review/SIMPLIFICATION_FIX_MAP.md docs/review/SIMPLIFICATION_WORK_LOG.md
```

## Results

- Deleted unused `ml_platform_core.runtime_types` Protocol scaffold.
- Removed descriptive-only or unused contract fields:
  - `description` fields on specs/plans
  - `StageSpec.supports_local_run`
  - `StageSpec.supports_remote_run`
  - `PipelineSpec.entry_stage_key`
  - `PipelineSpec.supports_partial_stage_run`
  - `TaskSpec.runtime_features`
  - `TaskSpec.user_facing`
  - `DomainStepPlan.tags`
  - `DomainPipelinePlan.tags`
- Kept the runtime boundary types that are actively consumed:
  - manifest specs for task/stage/pipeline/artifact/parameter validation
  - `DomainStepPlan` and `DomainPipelinePlan` for ClearML DAG rendering
- `uv run python -m pytest tests/test_runtime_manifest.py`: passed, 10 tests.
- `uv run python -m ruff check ...`: passed on changed code/test files.
- `uv run python -m ruff format --check ...`: passed on changed code/test
  files.
- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m pytest`: passed, 118 tests.
- `uv run python -m ruff check .`: passed.
- `uv run python -m ruff format --check .`: failed only on the known
  pre-existing 16-file format debt.

## Failures / Unknowns

- The requested bare `python -m ...` commands failed on this workstation
  because `python` resolves to the Windows Store alias. Use `uv run python`.
- Full-suite validation is recorded in the final command pass for this cleanup.
- R18 live ClearML UI/remote verification remains outside this cleanup scope.

## Next Action

CLEAN-3 should focus on one of:

1. S08: simplify the ClearML runtime plan/render surface without changing
   template entrypoints.
2. S05: split tabular manifest constants from plan construction if readability
   remains poor.
3. S06: decide whether `vulture` / `deptry` should be added for confirmed
   unused-code cleanup.

## 2026-06-29 - CLEAN-S04 diagnostics and reporting error handling

- Date: 2026-06-29
- Branch: `cleanup/s00-lean-codebase-audit`
- Worker: Codex
- Purpose: simplify diagnostics and error handling by separating best-effort
  artifact parsing from ClearML logger failures.

## Changed Files

- `clearml/adapter.py`
- `clearml/reports.py`
- `tests/test_clearml_mapping.py`
- `docs/review/SIMPLIFICATION_AUDIT.md`
- `docs/review/SIMPLIFICATION_FIX_MAP.md`
- `docs/review/SIMPLIFICATION_WORK_LOG.md`

## Commands

```powershell
git status --short
rg -n "print\(|warnings\.warn|logger\.|raise .*Error|except Exception|except BaseException|traceback|diagnostic|summary|decision" clearml pkgs scripts tests
rg -n "print\(|warnings\.warn|logger\.|raise .*Error|except Exception|except BaseException|traceback" clearml/adapter.py clearml/reports.py clearml/templates.py clearml/pipelines.py
uv run python -m pytest tests/test_clearml_mapping.py
uv run python -m ruff check clearml/adapter.py clearml/reports.py tests/test_clearml_mapping.py
uv run python -m ruff format clearml/adapter.py clearml/reports.py tests/test_clearml_mapping.py
uv run python -m ruff format --check clearml/adapter.py clearml/reports.py tests/test_clearml_mapping.py
python -m compileall clearml pkgs scripts
python -m pytest
python -m ruff check .
python -m ruff format --check .
uv run python -m compileall clearml pkgs scripts
uv run python -m pytest
uv run python -m ruff check .
uv run python -m ruff format --check .
```

## Results

- Replaced repeated broad CSV-read catches in `clearml/reports.py` with
  `_read_csv_or_none()`.
- Narrowed JSON parsing fallbacks to `OSError`, `UnicodeDecodeError`, and
  `json.JSONDecodeError`.
- Narrowed runtime parameter/stage input JSON decoding fallbacks in
  `clearml/adapter.py`.
- ClearML logger calls now surface runtime failures instead of swallowing them.
- ClearML logger signature fallback still catches `TypeError`, then raises a
  concise unsupported-signature message if no supported signature works.
- Operator-facing dry-run/sync `print()` output was reviewed and retained.
- `uv run python -m pytest tests/test_clearml_mapping.py`: passed, 51 tests.
- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m pytest`: passed, 120 tests.
- `uv run python -m ruff check .`: passed.
- Changed files pass `ruff format --check`.
- Full `uv run python -m ruff format --check .`: failed only on known
  pre-existing 14-file format debt.

## Failures / Unknowns

- The requested bare `python -m ...` commands failed because `python` resolves
  to the Windows Store alias in this workstation. Use `uv run python`.
- `clearml_dataset_exists()` still catches broad ClearML SDK exceptions for
  missing-dataset probing because SDK versions do not expose one stable
  exception class here.
- ClearML remote/UI behavior remains manual verification outside this cleanup.

## Next Action

CLEAN-4 should focus on one of:

1. S08: simplify ClearML pipeline/template rendering while preserving runner
   paths.
2. S05: reduce remaining mixed responsibilities in `clearml/reports.py` or
   tabular evaluation.
3. S06: decide whether unused/dependency audit tools should become dev
   dependencies.

## 2026-06-29 - CLEAN-S05/S08/S09 module facade and responsibility cleanup

- Date: 2026-06-29
- Branch: `cleanup/s00-lean-codebase-audit`
- Worker: Codex
- Purpose: remove private helper imports through old tabular facades, shrink
  runner facades to public API, and reduce duplicated ClearML entrypoint
  bootstrap loading without changing runner paths.

## Changed Files

- `clearml/app.py`
- `clearml/pipelines.py`
- `clearml/templates.py`
- `pkgs/tabular/src/ml_platform_tabular/infer.py`
- `pkgs/tabular/src/ml_platform_tabular/pipeline.py`
- `pkgs/tabular/src/ml_platform_tabular/stage.py`
- `tests/test_decision_summary.py`
- `tests/test_infer_schema_check.py`
- `tests/test_tabular_characterization.py`
- `tests/test_tabular_plots.py`
- `docs/review/PORTING_GUIDE.md`
- `docs/review/SIMPLIFICATION_AUDIT.md`
- `docs/review/SIMPLIFICATION_FIX_MAP.md`
- `docs/review/SIMPLIFICATION_WORK_LOG.md`

## Commands

```powershell
git status --short
git branch --show-current
rg -n "from \\.pipeline import|from ml_platform_tabular\\.pipeline import|from ml_platform_tabular\\.infer import|from ml_platform_tabular\\.plots import|_load_entrypoint_bootstrap|importlib\\.util" pkgs tests clearml scripts docs --glob "!docs/review/source/**"
rg -n "def _metric_name|def _metric_names|def _safe_name|def _build_ensemble|def _train_model|def _preprocess_features|def _ranked_results|def _evaluate_models|def _best_vs_ensemble_rows|def _decision_summary_payload|def _recommendation_payload|class EvaluationResult" pkgs/tabular/src/ml_platform_tabular/training pkgs/tabular/src/ml_platform_tabular/inference
uv run python -m ruff check clearml/app.py clearml/templates.py clearml/pipelines.py pkgs/tabular/src/ml_platform_tabular/stage.py pkgs/tabular/src/ml_platform_tabular/infer.py pkgs/tabular/src/ml_platform_tabular/pipeline.py tests/test_decision_summary.py tests/test_infer_schema_check.py tests/test_tabular_plots.py tests/test_tabular_characterization.py
uv run python -m pytest tests/test_infer_schema_check.py tests/test_decision_summary.py tests/test_tabular_plots.py
uv run python -m pytest tests/test_stage_smoke.py tests/test_tabular_characterization.py tests/test_runtime_manifest.py
uv run python -m pytest tests/test_clearml_mapping.py
uv run python -m ruff format clearml/app.py clearml/templates.py pkgs/tabular/src/ml_platform_tabular/stage.py
uv run python -m pytest
uv run python -m ruff check .
uv run python -m ruff format --check clearml/app.py clearml/templates.py clearml/pipelines.py pkgs/tabular/src/ml_platform_tabular/stage.py pkgs/tabular/src/ml_platform_tabular/infer.py pkgs/tabular/src/ml_platform_tabular/pipeline.py tests/test_decision_summary.py tests/test_infer_schema_check.py tests/test_tabular_plots.py tests/test_tabular_characterization.py
uv run python -m ruff format --check .
uv run python -m compileall clearml pkgs scripts
```

## Results

- `stage.py` imports `_build_ensemble`, `_evaluate_models`, metric helpers,
  preprocessing, ranking, and candidate training from `training.*` modules
  instead of `pipeline.py`.
- Tests that exercise private inference, summary, and plotting helpers now
  import the implementation packages directly.
- `infer.py` was reduced to the `run_infer` compatibility runner facade.
- `pipeline.py` was reduced to public training exports:
  `run_pipeline`, `evaluate_model_candidates`, and `EvaluationResult`.
- `plots.py` remains as the public plotting compatibility facade for external
  imports.
- `clearml/app.py`, `clearml/pipelines.py`, and `clearml/templates.py` no
  longer duplicate `spec_from_file_location()` bootstrap loader functions.
  They still preserve direct entrypoint compatibility via
  `_entrypoint_bootstrap.py`.
- Targeted tabular facade tests passed: 9 tests.
- Stage/characterization/runtime-manifest tests passed: 15 tests.
- ClearML mapping tests passed: 51 tests.
- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m pytest`: passed, 120 tests.
- `uv run python -m ruff check .`: passed.
- Changed code/test files pass `ruff format --check`.

## Failures / Unknowns

- `uv run python -m ruff format --check .` still fails on known unrelated
  11-file format debt.
- ClearML remote Agent execution was not verified, so `_entrypoint_bootstrap.py`,
  SDK shadow guards, and ClearML script metadata compatibility helpers remain.
- External imports of `ml_platform_tabular.plots`, `ml_platform_tabular.infer`,
  and `ml_platform_tabular.pipeline` were not audited outside this repository.

## Next Action

CLEAN-5 should focus on one of:

1. S05: split a cohesive part of `clearml/reports.py` or tabular
   `training/evaluation.py` if call sites become simpler.
2. S06: decide whether `vulture` / `deptry` should become temporary audit tools
   or dev dependencies.
3. S10: run final lean validation and update porting notes after the remaining
   cleanup batch.
