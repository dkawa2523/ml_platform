# Baseline environment report

このファイルは、`docs/review` を配置したあと、現在repoの初期状態を記録するためのものです。Codexまたは人手でコマンドを実行し、結果を貼り付けてください。

## Generated at

- Scaffold date: 2026-06-28
- Baseline updated: 2026-06-28
- Prompt 0-B update: 2026-06-28
- Target repository state: `review/r00-setup-review-tracking`

## Git baseline

```bash
git status --short
git branch --show-current
git remote -v
git log --oneline -n 20
```

### Result

```text
git status --short
 M AGENTS.md
?? docs/adr/0002-runtime-spec-and-package-manifest-boundary.md
?? docs/review/

git branch --show-current
review/r00-setup-review-tracking

git remote -v
origin  https://github.com/dkawa2523/ml_platform.git (fetch)
origin  https://github.com/dkawa2523/ml_platform.git (push)

git log --oneline -n 20
e315d7d Translate README to Japanese
2dac015 Add MkDocs documentation site
1899003 Simplify ClearML tabular workflow
46f05fe Record ClearML remote verification evidence
2d5e2f6 Harden ClearML template runtime defaults
647bcdf Fix CI smoke defaults and pipeline run tags
62fb911 Simplify ClearML New Run template handling
262210c Rebuild ClearML pipeline draft on template sync
544c304 Harden ClearML Agent GBM runtime
f3422d7 Expose execution image packages to ClearML tasks
1b05c5c Install GBM packages in ClearML remote venv
b7080a5 Split ClearML controller and stage queues
db9c532 Upgrade stale ClearML pipeline clones at runtime
59e03b2 Delete stale ClearML pipeline drafts on sync
c859df6 Reference execution image in ClearML templates
bed4897 Reuse existing ClearML pipeline drafts
014a9d2 Simplify product baseline docs and defaults
09ea4a1 Refine ClearML plot reporting UX
fe3846a Improve ClearML leaderboard plot UX
50e6942 Improve leaderboard and inference plot UX
```

Prompt 0-A initial check saw only `?? docs/review/`. Prompt 0-B runs after
review rules and ADR edits, so the current status also includes `AGENTS.md`
and `docs/adr/0002-runtime-spec-and-package-manifest-boundary.md`.

### Review document presence

```text
OK: docs/review/source/repository_review_transcription_current.md
OK: docs/review/source/pr28_review_consolidated.md
OK: docs/review/source/tabular_package_review_analysis.md
OK: docs/review/PR28_REVIEW_MAP.md
OK: docs/review/CODEX_WORK_LOG.md
OK: docs/review/BASELINE_ENV_REPORT.md
OK: docs/review/PORTING_GUIDE.md
OK: docs/review/REVIEW_FIX_BRANCH_PLAN.md
OK: docs/review/CODEX_PROMPTS.md
```

## Python / package manager baseline

```bash
python --version
python -m pip --version
uv --version || true
```

### Result

```text
python --version
Python was not found; run without arguments to install from the Microsoft Store, or disable this shortcut from Settings > Apps > Advanced app settings > App execution aliases.

python -m pip --version
Python was not found; run without arguments to install from the Microsoft Store, or disable this shortcut from Settings > Apps > Advanced app settings > App execution aliases.

uv --version
uv 0.11.16 (135a36367 2026-05-21 x86_64-pc-windows-msvc)

.\.venv\Scripts\python.exe --version
Python 3.13.12

.\.venv\Scripts\python.exe -m pip --version
pip 25.3 from C:\Users\user\Desktop\ml_project\ml_platform\.venv\Lib\site-packages\pip (python 3.13)
```

Notes:

- PATH `python` resolves to the Windows Store execution alias, not the project Python.
- Project-local `.venv\Scripts\python.exe` is available and was used for verification.
- `uv.lock` is missing.

## Repository files baseline

```bash
git ls-files .github .vscode docs pkgs clearml scripts pyproject.toml requirements.txt requirements-dev.txt uv.lock .pre-commit-config.yaml .gitlint .gitattributes '*.code-workspace'
find .github -maxdepth 3 -type f -print | sort || true
find .vscode -maxdepth 2 -type f -print | sort || true
```

### Result

```text
Tracked relevant files include `.github/workflows/ci.yml`, `clearml/**`,
`docs/**`, `pkgs/**`, `scripts/**`, `pyproject.toml`, `requirements.txt`,
and `requirements-dev.txt`.

Project/dependency files:
- `pyproject.toml`: present
- `pkgs/core/pyproject.toml`: present
- `pkgs/tabular/pyproject.toml`: present
- `requirements.txt`: present
- `requirements-dev.txt`: present
- `uv.lock`: missing

Missing from current tree:
- `.vscode/`
- `uv.lock`
- `.pre-commit-config.yaml`
- `.gitlint`
- `.gitattributes`
- `*.code-workspace`

find .github -maxdepth 3 -type f -print | sort
.github\workflows\ci.yml

find .vscode -maxdepth 2 -type f -print | sort
.vscode missing
```

## Tool availability

```bash
python -m pytest --version || true
python -m ruff --version || true
python -m mypy --version || true
python -m pre_commit --version || true
python -m radon --version || true
python -m lint_imports --version || true
```

### Result

```text
.\.venv\Scripts\python.exe -m pytest --version
pytest 9.0.3

.\.venv\Scripts\python.exe -m ruff --version
No module named ruff

.\.venv\Scripts\python.exe -m mypy --version
No module named mypy

.\.venv\Scripts\python.exe -m pre_commit --version
No module named pre_commit

.\.venv\Scripts\python.exe -m gitlint --version
No module named gitlint

.\.venv\Scripts\python.exe -m radon --version
No module named radon

.\.venv\Scripts\python.exe -m lint_imports --version
No module named lint_imports
```

`requirements-dev.txt` currently contains `pytest>=8.0` and does not define
ruff, mypy, pre-commit, gitlint, radon, or import-linter. Treat restoration of
these tools as R01/R21 follow-up work.

## Initial verification commands

```bash
python -m compileall clearml pkgs scripts
python -m pytest
```

### Result

```text
.\.venv\Scripts\python.exe -m compileall clearml pkgs scripts
Result: success

.\.venv\Scripts\python.exe -m pytest
Result: failed during collection

Summary:
- collected 87 items / 1 error
- failing module: tests/test_core_smoke.py
- import chain reaches pandas through ml_platform_core.io
- pandas import fails while loading pandas._libs.indexing
- Windows error: DLL load failed because the file was blocked by application control policy

Classification:
- environment/import issue
- not a test assertion failure
- no code fix attempted in Phase 0-A
```

## uv baseline

```text
uv sync --all-extras --dev --dry-run
Result: success; no environment changes made
Summary: would create uv.lock, download 5 packages, uninstall 20 packages, install 5 packages.

uv sync --all-extras --dev --check
Result: failed
Summary: environment is outdated; uv would create uv.lock and change packages.
```

Do not run `uv sync --all-extras --dev` without explicit approval in this
phase. R02 should decide the uv workspace / lockfile policy.

## Lint baseline

```text
.\.venv\Scripts\python.exe -m ruff check .
Result: failed; No module named ruff

.\.venv\Scripts\python.exe -m ruff format --check .
Result: failed; No module named ruff

python -m pre_commit run --all-files
Result: skipped; `.pre-commit-config.yaml` is absent and pre_commit is not installed.
```

## R01-R27 target search summary

```text
ui_* terminology:
- clearml/adapter.py: 9 matches
- clearml/pipelines.py: 63 matches
- clearml/templates.py: 13 matches
- clearml/app.py: 5 matches
- tests/test_clearml_mapping.py: 25 matches

sys.path / _entrypoint_bootstrap / import_clearml_sdk / getattr / Any:
- present in clearml/_entrypoint_bootstrap.py and scripts/_bootstrap.py
- heavily present in clearml/adapter.py, clearml/pipelines.py, clearml/templates.py
- present across pkgs/core and pkgs/tabular due current dict[str, Any] style

Registry / set_dotted_path / TABLE_SUFFIXES:
- pkgs/core/src/ml_platform_core/registry.py
- pkgs/core/src/ml_platform_core/config.py
- pkgs/core/src/ml_platform_core/io.py

BLAS/OpenMP thread env:
- clearml/app.py
- scripts/local_run.py
- scripts/make_sample_data.py
```

## ClearML / Kubernetes manual checks

- ClearML localhost UI: manual verification required
- ClearML task / pipeline execution: manual verification required
- Kubernetes target cluster rollout: manual verification required

## Notes

- uvがない場合、Phase 0では原則としてglobal installしない。R02でuv workspace化を検討する。
- dev toolsが不足してpytest/lintが実行できない場合、失敗として記録し、Phase 1またはPhase 2で対応する。

## Prompt 1-A tooling / CI investigation

### Git state

```text
git status --short
<clean>

git branch --show-current
review/r01-tooling-ci
```

### Current files

```text
Tracked Phase 1 target files:
- .github/workflows/ci.yml

Missing Phase 1 target files:
- .github/workflows/smoke-test.yml
- .github/workflows/deploy-mkdocs.yml
- .pre-commit-config.yaml
- .gitlint
- .gitattributes
- .vscode/
- *.code-workspace
```

### History investigation

```text
History candidates found:
- .github/workflows/ci.yml at 647bcdf Fix CI smoke defaults and pipeline run tags
- .github/workflows/ci.yml at 6637119 Initial ml_platform MVP

No history candidates found in this repository:
- .github/workflows/smoke-test.yml
- .github/workflows/deploy-mkdocs.yml
- .pre-commit-config.yaml
- .gitlint
- .gitattributes
- .vscode/*
- *.code-workspace
```

The current `ci.yml` and the `647bcdf` history candidate both call removed task
configs:

```text
config/tasks/tabular_train.yaml     missing
config/tasks/tabular_eval.yaml      missing
config/tasks/tabular_1d_output.yaml missing
```

Current task configs are:

```text
config/tasks/tabular_pipeline.yaml
config/tasks/tabular_stage.yaml
config/tasks/tabular_infer.yaml
```

### Runner and workflow notes

- Current `ci.yml` uses `runs-on: ubuntu-latest`.
- Review source mentions `arc-runner-set-spdml-ml-pipeline`.
- This local repository cannot confirm whether that runner set is available.
- Prompt 1-B should keep runner choice as `needs_confirmation` unless repository/organization settings confirm it.
- Package common CI and smoke workflow should be separated.

### Tool availability

```text
python --version
Result: failed; Windows Store execution alias

python -m <tool> commands
Result: failed; Windows Store execution alias

.\.venv\Scripts\python.exe --version
Python 3.13.12

.\.venv\Scripts\python.exe -m pytest --version
pytest 9.0.3

.\.venv\Scripts\python.exe -m ruff --version
Result: failed; No module named ruff

.\.venv\Scripts\python.exe -m pre_commit --version
Result: failed; No module named pre_commit

.\.venv\Scripts\python.exe -m gitlint --version
Result: failed; No module named gitlint

.\.venv\Scripts\python.exe -m radon --version
Result: failed; No module named radon

.\.venv\Scripts\python.exe -m lint_imports --version
Result: failed; No module named lint_imports
```

One investigation command failed due PowerShell glob handling:

```text
rg ... requirements*.txt ...
Result: failed; PowerShell passed the glob in a way that produced an invalid path.
Next action: use explicit `requirements.txt requirements-dev.txt` paths in Prompt 1-B.
```

### Prompt 1-B minimum restoration direction

- Restore `ci.yml` as common package CI: install, compileall, pytest, and lint hooks once tooling is present.
- Add separate `smoke-test.yml`: sample data, `tabular_pipeline.yaml`, and `tabular_infer.yaml`.
- Do not call removed `tabular_train.yaml`, `tabular_eval.yaml`, or `tabular_1d_output.yaml`.
- Add minimal `.pre-commit-config.yaml`, `.gitlint`, `.gitattributes`, `.vscode/*`, and `ml_platform.code-workspace` based on current repo needs.
- Keep uv migration in R02; do not perform it in Phase 1.

## Prompt 1-B Phase 1 tooling restoration baseline

### Restored files

```text
.github/workflows/ci.yml
.github/workflows/smoke-test.yml
.github/workflows/deploy-mkdocs.yml
.pre-commit-config.yaml
.gitlint
.gitattributes
.vscode/extensions.json
.vscode/settings.json
ml_platform.code-workspace
pyproject.toml
requirements-dev.txt
```

### Tool install result

```text
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Result: success

Installed/restored dev tools:
- ruff 0.15.20
- pre-commit 4.6.0
- gitlint 0.19.1
- radon 6.0.1
- import-linter 2.12
```

This install was project-local to `.venv`. It was done because Phase 1 restored
the current requirements-based dev tooling. This is not the R02 uv migration.

`ty` was not installed or configured in this phase; keep as
`needs_confirmation` for R01.

### Verification results

```text
.\.venv\Scripts\python.exe -m compileall clearml pkgs scripts
Result: success

.\.venv\Scripts\python.exe -m pytest
Result: success; 89 passed

.\.venv\Scripts\python.exe -m ruff check .
Result: failed
Summary:
- E402 in clearml/app.py, clearml/pipelines.py, clearml/templates.py, scripts/local_run.py
- F841 in pkgs/tabular/src/ml_platform_tabular/infer.py
- F401 in pkgs/tabular/src/ml_platform_tabular/pipeline.py
Classification:
- restored tool found existing code issues
- do not fix in Phase 1
- route E402 to R16/R17 and unused-symbol cleanup to later type/config cleanup

.\.venv\Scripts\python.exe -m ruff format --check .
Result: failed
Summary: 20 files would be reformatted
Classification: formatting baseline debt; do not mass-format implementation code in Phase 1.

.\.venv\Scripts\python.exe -m pre_commit run --all-files
Result: failed
Summary:
- initial run failed on MkDocs Python YAML tag and deploy multi-document YAML
- mutating hooks touched out-of-scope source/historical docs; those changes were reverted
- after config adjustment, exact command still fails because `ruff` executable is not on PATH when `.venv` is not activated

$env:PATH = (Resolve-Path .\.venv\Scripts).Path + ';' + $env:PATH; .\.venv\Scripts\python.exe -m pre_commit run --all-files
Result: failed
Summary:
- basic hooks pass
- Ruff check and Ruff format hooks fail on the existing Ruff issues listed above

.\.venv\Scripts\python.exe -m radon cc clearml pkgs scripts -s -a
Result: success
Summary:
- 378 blocks analyzed
- average complexity: B (5.341269841269841)
- high-complexity findings include clearml/adapter.py apply_ui_params F(60),
  clearml/pipelines.py _build_training_plan D(28), clearml/reports.py
  _report_prediction_plots D(27), and pkgs/tabular pipeline/data/stage functions.

.\.venv\Scripts\python.exe -m lint_imports --config pyproject.toml
Result: failed
Summary: No module named lint_imports
Classification: invocation issue; import-linter exposes a console script.

.\.venv\Scripts\lint-imports.exe --config pyproject.toml
Result: success
Summary: 1 contract kept, 0 broken.

.\.venv\Scripts\python.exe -m pre_commit run check-yaml --files .github/workflows/ci.yml .github/workflows/smoke-test.yml .github/workflows/deploy-mkdocs.yml .pre-commit-config.yaml
Result: success

.\.venv\Scripts\python.exe -m pre_commit run check-json --files .vscode/settings.json .vscode/extensions.json ml_platform.code-workspace
Result: success

git diff --check
Result: success; Git printed CRLF-to-LF warnings for modified review docs.
```

### PATH python / console script notes

```text
python --version
Result: failed; Windows Store execution alias

python -m ruff --version
Result: failed; Windows Store execution alias

.\.venv\Scripts\python.exe -m gitlint --version
Result: failed; gitlint has no module entrypoint

.\.venv\Scripts\gitlint.exe --version
Result: success; gitlint, version 0.19.1
```

Use `.venv\Scripts\python.exe` or activate `.venv` locally. CI can use
`python` after `actions/setup-python`.

### Manual verification required

- R13 runner set: `arc-runner-set-spdml-ml-pipeline` availability requires GitHub repository/organization confirmation.
- R23 GitHub Pages: repository Pages settings and deployment target require confirmation.
- ClearML localhost UI: manual verification required.
- ClearML remote execution: manual verification required.
- Kubernetes / ClearML remote target cluster: manual verification required.

## Prompt 2-A dependency/import investigation

### Git and environment state

```text
git status --short
<clean>

git branch --show-current
review/r02-dependency-import-runtime

python --version
Result: failed; Windows Store execution alias

python -m pip --version
Result: failed; Windows Store execution alias

.\.venv\Scripts\python.exe --version
Python 3.13.12

.\.venv\Scripts\python.exe -m pip --version
pip 25.3 from .venv

uv --version
uv 0.11.16 (135a36367 2026-05-21 x86_64-pc-windows-msvc)
```

### Dependency management state

```text
Root pyproject.toml:
- project name: ml-platform-mvp
- runtime dependencies: empty list
- optional clearml extra: clearml>=1.14
- pytest pythonpath still points at pkgs/core/src, pkgs/tabular/src, and repo root
- Ruff and import-linter config exists from Phase 1

requirements.txt:
- pandas>=2.0
- numpy>=1.24
- pyyaml>=6.0
- scikit-learn>=1.3
- pillow>=10.0
- clearml==2.1.7

requirements-dev.txt:
- includes requirements.txt
- pytest>=8.0
- ruff>=0.8
- pre-commit>=4.0
- gitlint>=0.19
- radon>=6.0
- import-linter>=2.0

pkgs/core/pyproject.toml:
- package dependencies include pandas and pyyaml

pkgs/tabular/pyproject.toml:
- package dependencies include ml-platform-core, pandas, numpy, scikit-learn, and pillow
- optional gbm extras include lightgbm, xgboost, and catboost

uv.lock:
- missing
```

`requirements.txt` is still used outside local development:

```text
deploy/base/Dockerfile:
- installs requirements.txt and clearml-agent
- installs editable pkgs/core and pkgs/tabular[gbm]

deploy/base/configmap.yaml:
- CLEARML_AGENT_FORCE_SYSTEM_SITE_PACKAGES is true

clearml/templates.py:
- remote package list still includes GBM packages for ClearML Agent venvs
```

Classification:

- R02 is `in_progress`.
- Prompt 2-B should make `pyproject.toml` / `uv.lock` the source of truth.
- Keep requirements files as compatibility files for Docker and ClearML remote execution rather than deleting them in the same change.

### uv dry-run/check

```text
uv sync --all-extras --dev --dry-run
Result: success; no mutation performed
Summary:
- would use project environment `.venv`
- would create `uv.lock`
- would download 5 packages
- would uninstall 42 packages
- would install 5 packages
- would upgrade packages including clearml from 2.1.7 to 2.1.9

uv sync --all-extras --dev --check
Result: failed
Summary:
- environment is outdated
- lockfile would be created
```

Actual `uv sync` was not run in Prompt 2-A because it would mutate `.venv` and
create `uv.lock`. That mutation is deferred to Prompt 2-B.

### Bootstrap and import structure

Manual path bootstrap remains:

```text
clearml/_entrypoint_bootstrap.py
- prepends clearml directory
- prepends pkgs/core/src
- prepends pkgs/tabular/src

scripts/_bootstrap.py
- prepends pkgs/core/src
- prepends pkgs/tabular/src
- prepends clearml
```

Files importing after bootstrap:

```text
clearml/app.py
clearml/pipelines.py
clearml/templates.py
scripts/local_run.py
scripts/sync_clearml_templates.py
scripts/clearml_pipeline.py
```

Dynamic ClearML SDK import/shadow handling remains:

```text
clearml/adapter.py
- _without_repo_clearml_shadow()
- import_clearml_sdk()
- import_clearml_automation()
- import_clearml_symbol()
```

Sibling imports still depend on the current entrypoint layout:

```text
clearml/app.py          -> from adapter import ...
clearml/pipelines.py    -> from adapter import ...
clearml/templates.py    -> from adapter import ..., from pipelines import ...
```

Tests currently load ClearML entrypoint modules by file path:

```text
tests/test_clearml_mapping.py
tests/test_deploy_config.py
```

These facts explain why imports cannot all be moved to the file top before the
package install/entrypoint strategy is normalized.

### Import probe

```text
.\.venv\Scripts\python.exe <import probe>

ml_platform_core ok
ml_platform_tabular ok
import clearml resolved to:
C:\Users\user\Desktop\ml_project\ml_platform\.venv\Lib\site-packages\clearml\__init__.py
```

Current `.venv` resolves `import clearml` to the official SDK, but the local
`clearml/` directory name remains a shadow risk for direct script execution,
test file loaders, and ClearML remote templates.

### Verification results

```text
.\.venv\Scripts\python.exe -m compileall clearml pkgs scripts
Result: success

.\.venv\Scripts\python.exe -m pytest
Result: success; 89 passed

.\.venv\Scripts\python.exe -m ruff check .
Result: failed
Summary:
- E402 in clearml/app.py, clearml/pipelines.py, clearml/templates.py, scripts/local_run.py
- F841 in pkgs/tabular/src/ml_platform_tabular/infer.py
- F401 in pkgs/tabular/src/ml_platform_tabular/pipeline.py

.\.venv\Scripts\python.exe -m ruff format --check .
Result: failed
Summary:
- 20 files would be reformatted
```

Classification:

- E402 belongs to R16/R17 dependency/import normalization.
- F841/F401 should be handled in the later type/config cleanup phase or a small focused cleanup.
- Broad formatting should not be mixed into Prompt 2-A/2-B unless explicitly planned.

### Prompt 2-B minimum direction

- Add uv workspace/lock metadata at the root while keeping `pkgs/core` and `pkgs/tabular` as workspace members.
- Add `uv.lock` via `uv lock`.
- Keep `requirements.txt` and `requirements-dev.txt` as compatibility files and mark them as derived/compatibility inputs where practical.
- Move local script execution toward package-installed imports and reduce `scripts/_bootstrap.py` reliance.
- Do not rename the local `clearml/` directory in Phase 2.
- Normalize `adapter.import_clearml_sdk()` toward a simpler lazy official SDK import only after confirming local shadow behavior.
- Keep `clearml/_entrypoint_bootstrap.py` until direct script execution, `spec_from_file_location` tests, synced ClearML templates, and ClearML remote execution are verified.

### Manual verification required

- ClearML localhost UI: manual verification required.
- ClearML remote template execution for `clearml/app.py` and `clearml/pipelines.py`: manual verification required.
- Kubernetes / ClearML remote target cluster: manual verification required.
- Full removal of `clearml/_entrypoint_bootstrap.py`: needs confirmation after remote/template compatibility checks.

## Prompt 2-B dependency/import implementation baseline

### Files changed

```text
pyproject.toml
uv.lock
requirements.txt
requirements-dev.txt
.github/workflows/ci.yml
.github/workflows/smoke-test.yml
.github/workflows/deploy-mkdocs.yml
clearml/adapter.py
scripts/local_run.py
scripts/sync_clearml_templates.py
scripts/clearml_pipeline.py
scripts/_bootstrap.py (deleted)
docs/review/PR28_REVIEW_MAP.md
docs/review/CODEX_WORK_LOG.md
docs/review/BASELINE_ENV_REPORT.md
docs/review/REVIEW_RESPONSE_DRAFTS.md
docs/adr/0002-runtime-spec-and-package-manifest-boundary.md
```

### Dependency state after implementation

```text
pyproject.toml:
- root project is uv package=false
- workspace members: pkgs/core, pkgs/tabular
- workspace sources: ml-platform-core, ml-platform-tabular
- root dependencies: ml-platform-core, ml-platform-tabular
- extras: clearml, gbm
- dependency groups: dev, docs

uv.lock:
- generated successfully

requirements.txt / requirements-dev.txt:
- retained as compatibility files
- comments now state that pyproject.toml plus uv.lock is the source of truth
```

`gitlint` note:

```text
gitlint remains in requirements-dev.txt but is not in the uv dev group.
Reason:
- gitlint 0.19.x depends on gitlint-core
- gitlint-core pins sh==1.14.3
- sh==1.14.3 imports fcntl during build metadata generation on Windows
- uv lock fails on this dependency from the Windows workstation
```

### Bootstrap/import state after implementation

```text
Removed:
- scripts/_bootstrap.py
- scripts/local_run.py dependency on scripts/_bootstrap.py
- scripts/sync_clearml_templates.py dependency on scripts/_bootstrap.py
- scripts/clearml_pipeline.py dependency on scripts/_bootstrap.py

Retained:
- clearml/_entrypoint_bootstrap.py
```

Reason for retained bootstrap:

```text
ClearML remote templates still directly execute:
- clearml/app.py
- clearml/pipelines.py

These files need the operations directory and workspace packages importable
before sibling imports. Full removal is blocked until ClearML remote/template
direct-entrypoint behavior is manually verified.
```

Ruff import-order state:

```text
Ruff E402 is no longer reported.
Documented per-file E402 ignores remain only for:
- clearml/app.py
- clearml/pipelines.py
- clearml/templates.py
```

### Verification results

```text
python -m compileall clearml pkgs scripts
Result: failed; Windows Store execution alias

python -m pytest
Result: failed; Windows Store execution alias

python -m ruff check .
Result: failed; Windows Store execution alias

python -m ruff format --check .
Result: failed; Windows Store execution alias

uv lock
Result: success after leaving gitlint in requirements compatibility file only

uv sync --all-extras --dev
Result: success

uv run python -m compileall clearml pkgs scripts
Result: success

uv run python -m pytest
Result: success; 89 passed

uv run python -m ruff check .
Result: failed
Summary:
- F841 local variable data_cfg assigned but never used in pkgs/tabular/src/ml_platform_tabular/infer.py
- F401 numpy imported but unused in pkgs/tabular/src/ml_platform_tabular/pipeline.py
Classification:
- out of R02/R08/R16/R17 scope
- route to Phase 3 type/config cleanup or a focused lint cleanup

uv run python -m ruff format --check .
Result: failed
Summary:
- 19 files would be reformatted
Classification:
- broad formatting debt; do not mix into Phase 2

uv run lint-imports --config pyproject.toml
Result: success; 1 contract kept, 0 broken

uv run python scripts/make_sample_data.py
Result: success

uv run python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set "model.candidates=[linear,ridge,lasso,elasticnet,random_forest,extra_trees,gradient_boosting]"
Result: success

uv run python scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
Result: success

uv run python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
Result: success

uv run python scripts/clearml_pipeline.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
Result: success

PowerShell here-string import probe piped into uv run python -
Result: success
Summary:
- clearml resolves to .venv site-packages official SDK
- ml_platform_core resolves to pkgs/core/src
- ml_platform_tabular resolves to pkgs/tabular/src

uv run gitlint --version
Result: failed; program not found
Classification:
- expected after excluding gitlint from uv dev group due Windows lock issue

git diff --check
Result: success; Git printed a CRLF-to-LF warning for the ADR file

rg -n "from _bootstrap|add_repo_paths|scripts/_bootstrap|scripts\\_bootstrap" scripts clearml tests
Result: no matches

uv run python -m ruff check clearml scripts
Result: success

uv run python -m pre_commit run check-yaml --files .github/workflows/ci.yml .github/workflows/smoke-test.yml .github/workflows/deploy-mkdocs.yml
Result: success

uv run python -m pre_commit run check-toml --files pyproject.toml
Result: success

uv run python -m pre_commit run check-added-large-files --files uv.lock
Result: success

uv run python -m pre_commit run end-of-file-fixer --files <changed text files>
Result: success
```

### Manual verification required

- ClearML localhost UI: manual verification required.
- ClearML remote execution of `clearml/app.py` and `clearml/pipelines.py`: manual verification required.
- Kubernetes / ClearML remote target cluster: manual verification required.
- Removal of `clearml/_entrypoint_bootstrap.py`: needs confirmation after remote/template compatibility checks.
