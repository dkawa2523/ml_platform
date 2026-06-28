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
