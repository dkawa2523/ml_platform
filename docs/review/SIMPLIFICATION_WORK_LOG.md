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
rg -n "def _metric_name|def _metric_names|def _safe_name|def _build_ensemble|def _train_model|def _preprocess_features|def _ranked_results|def evaluate_model_candidates|def _best_vs_ensemble_rows|def _decision_summary_payload|class EvaluationResult" pkgs/tabular/src/ml_platform_tabular/training pkgs/tabular/src/ml_platform_tabular/inference
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

- `stage.py` imports `_build_ensemble`, `evaluate_model_candidates`, metric helpers,
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

## 2026-06-29 - CLEAN-S06/S07 docs and dependency setup cleanup

- Date: 2026-06-29
- Branch: `cleanup/s00-lean-codebase-audit`
- Worker: Codex
- Purpose: prune obsolete active setup and architecture docs, clarify
  requirements-file compatibility, and leave dependency deletion gated by
  dependency-audit tooling.

## Changed Files

- `README.md`
- `clearml/README.md`
- `docs/CODEX_HANDOFF.md`
- `docs/ml_platform_mkdocs/README_DOCS.md`
- `docs/ml_platform_mkdocs/docs/architecture/repository-structure.md`
- `docs/ml_platform_mkdocs/docs/development/add-feature-or-metric.md`
- `docs/ml_platform_mkdocs/docs/development/add-model.md`
- `docs/ml_platform_mkdocs/docs/development/guidelines.md`
- `docs/ml_platform_mkdocs/docs/development/testing.md`
- `docs/ml_platform_mkdocs/docs/operations/checklist.md`
- `docs/ml_platform_mkdocs/docs/reference/models.md`
- `docs/ml_platform_mkdocs/docs/setup/clearml-preparation.md`
- `docs/ml_platform_mkdocs/docs/setup/environment.md`
- `docs/ml_platform_mkdocs/docs/setup/index.md`
- `docs/ml_platform_mkdocs/docs/setup/local-run.md`
- `docs/ml_platform_mkdocs/docs/usage/local-training.md`
- `docs/review/PORTING_GUIDE.md`
- `docs/review/SIMPLIFICATION_AUDIT.md`
- `docs/review/SIMPLIFICATION_FIX_MAP.md`
- `docs/review/SIMPLIFICATION_WORK_LOG.md`

## Commands

```powershell
git status --short
rg -n "ui_params|ui_value|_entrypoint_bootstrap|sys\\.path|requirements\\.txt|pip install -r|plots\\.py|infer\\.py|pipeline\\.py|Registry|Kubernetes|k8s|kubectl|kustomize" README.md docs clearml pkgs scripts tests --glob "!docs/review/source/**"
Get-Content -Raw pyproject.toml
Get-Content -Raw requirements.txt
Get-Content -Raw requirements-dev.txt
uv run python -m deptry .
rg -n "python scripts/|pytest -q|pip install -r|uv pip install -r|pipeline\\.py|infer\\.py|plots\\.py|_entrypoint_bootstrap|sys\\.path|ui_params" README.md docs/CODEX_HANDOFF.md docs/ml_platform_mkdocs docs/SPEC.md docs/CLEARML_UI_SPEC.md docs/ROADMAP.md clearml/README.md --glob "!docs/review/source/**"
rg -n "uv pip install|requirements-dev|requirements-docs|requirements\\.txt|pip install" README.md docs/CODEX_HANDOFF.md docs/ml_platform_mkdocs clearml/README.md docs/SPEC.md --glob "!docs/review/source/**"
python -m compileall clearml pkgs scripts
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m deptry .
uv run python -m compileall clearml pkgs scripts
uv run python -m pytest
uv run python -m ruff check .
uv run python -m ruff format --check .
uv run python -m deptry .
uv run --group docs python -m mkdocs build --config-file docs\ml_platform_mkdocs\mkdocs.yml --strict
git diff --check
```

## Results

- No dependency was removed because `deptry` is not installed.
- Active setup commands now prefer:
  - `uv sync --group dev`
  - `uv sync --group docs`
  - `uv run python ...`
  - `uv run --group docs python -m mkdocs ...`
- `requirements.txt`, `requirements-dev.txt`, and
  `docs/ml_platform_mkdocs/requirements-docs.txt` remain as compatibility
  files.
- MkDocs active architecture/development/reference pages now describe
  `training`, `inference`, and `plotting` as the implementation packages.
- `infer.py`, `pipeline.py`, and `plots.py` are documented as compatibility
  facades where they remain relevant.
- Bare `python -m ...` verification commands failed on this workstation because
  `python` resolves to the Windows Store alias. The canonical `uv run python`
  checks below were used for this cleanup.
- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m pytest`: passed, 120 tests.
- `uv run python -m ruff check .`: passed.
- `uv run --group docs python -m mkdocs build --config-file docs\ml_platform_mkdocs\mkdocs.yml --strict`:
  passed; generated `docs/ml_platform_mkdocs/site/` output was removed after
  the check.
- `git diff --check`: passed, with only the existing CRLF normalization warning
  for `docs/review/PORTING_GUIDE.md`.
- `docs/review/source/*` was not changed.
- Kubernetes / K8 work was not performed.

## Failures / Unknowns

- `uv run python -m deptry .` failed because `deptry` is not installed.
- Bare `python -m compileall`, `python -m pytest`, `python -m ruff ...`, and
  `python -m deptry .` failed because `python` resolves to the Windows Store
  alias in this workstation.
- `uv run python -m ruff format --check .` failed on known formatting debt in
  11 pre-existing files outside this docs cleanup.
- Dependency deletion remains `needs_confirmation`.
- Review history and response draft docs still mention old states by design.

## Next Action

CLEAN-FINAL should:

1. Re-run full compile, test, ruff, and docs checks.
2. Record remaining `ruff format --check` debt.
3. Decide whether to add temporary dependency-audit tooling.
4. Confirm no active docs point users to obsolete setup commands.

## 2026-06-29 - CLEAN-FINAL lean codebase completion judgment

- Date: 2026-06-29
- Branch: `cleanup/s00-lean-codebase-audit`
- Worker: Codex
- Purpose: lean codebase final completion judgment without new implementation,
  code deletion, or Kubernetes / K8 work.

## Commands

```powershell
git status --short
git branch --show-current
git log --oneline --decorate -n 50
python -m compileall clearml pkgs scripts
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m pre_commit run --all-files
python -m radon cc clearml pkgs scripts -s -a
python -m vulture clearml pkgs scripts tests --min-confidence 80
python -m deptry .
uv run python -m compileall clearml pkgs scripts
uv run python -m pytest
uv run python -m ruff check .
uv run python -m ruff format --check .
uv run python -m pre_commit run --all-files
uv run python -m radon cc clearml pkgs scripts -s -a
uv run python -m radon mi clearml pkgs scripts -s
uv run python -m vulture clearml pkgs scripts tests --min-confidence 80
uv run python -m deptry .
rg -n "TODO|FIXME|deprecated|Backward-compatible|compat|legacy|temporary|workaround" clearml pkgs scripts tests docs
rg -n "ui_params|ui_value|default_ui_params|pipeline_ui_params" clearml pkgs scripts tests docs
rg -n "sys\\.path|_entrypoint_bootstrap|add_clearml_entrypoint_paths" clearml pkgs scripts tests docs
rg -n "Registry|set_dotted_path" .
rg -n "print\\(" clearml pkgs scripts tests
```

## Results

- Starting status: clean.
- Branch: `cleanup/s00-lean-codebase-audit`.
- Bare `python -m ...` commands failed because `python` resolves to the
  Windows Store alias on this workstation.
- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m pytest`: passed, 120 tests.
- `uv run python -m ruff check .`: passed.
- `uv run python -m radon cc clearml pkgs scripts -s -a`: ran, average
  complexity A (4.98).
- `uv run python -m radon mi clearml pkgs scripts -s`: ran; remaining C
  maintainability modules are `clearml/adapter.py`, `clearml/pipelines.py`,
  `clearml/reports.py`, and `pkgs/core/src/ml_platform_core/config_models.py`.
- `uv run python -m ruff format --check .`: failed on known 11-file formatting
  debt outside this completion docs update.
- `uv run python -m pre_commit run --all-files`: failed only on the same ruff
  format-check debt; other hooks passed and the worktree was unchanged.
- `uv run python -m vulture ...`: failed because `vulture` is not installed.
- `uv run python -m deptry .`: failed because `deptry` is not installed.
- Residual searches found expected compatibility surfaces:
  - ClearML `ui_params` argument names in pipeline helpers and tests.
  - ClearML direct-entrypoint bootstrap and SDK shadow guard.
  - Public tabular compatibility facades.
  - Operator-facing `print()` calls in scripts and ClearML dry-run/sync code.
  - `Registry` and `set_dotted_path` only in docs/review history, tests, and
    future-scope wording, not live removed code.

## Completion

`pass_with_notes`

The Lean cleanup is complete for this repository scope. Code behavior checks
pass through the uv-managed interpreter, and the remaining items are documented
as external confirmation or isolated formatting/tooling work.

## Remaining Items

- S01 remains `needs_confirmation`: broad unused-code deletion needs `vulture`
  or equivalent tooling.
- S02 remains `needs_confirmation`: public facades and ClearML compatibility
  paths require target-import and remote/template confirmation.
- S06 remains `needs_confirmation`: dependency pruning needs `deptry` or manual
  dependency proof.
- S08 remains `needs_confirmation`: ClearML remote Agent execution must be
  verified before removing `_entrypoint_bootstrap.py` or renaming `clearml/`.
- Ruff format debt remains in 11 pre-existing files and should be handled in a
  standalone no-behavior formatting commit.
- Kubernetes / K8 verification remains excluded.

## Next Action

Commit the final completion docs, then either:

1. Port Lean cleanup commits to the target repo in the documented order.
2. Run optional `vulture` / `deptry` tooling in a separate cleanup branch.
3. Address ruff formatting debt in an isolated formatting-only commit.
