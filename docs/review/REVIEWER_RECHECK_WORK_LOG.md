# Reviewer Recheck Work Log

Date: 2026-07-01 (Asia/Tokyo)
Branch: `cleanup/s00-lean-codebase-audit`
Worker: Codex
Purpose: fix and verify P1/P2/P3 reviewer recheck findings

## Scope Controls

- Did not push.
- Did not inspect, print, create, or commit secrets, credentials, ClearML API keys, or `.env` contents.
- Did not run `kubectl`, `kustomize`, or `helm`.
- Did not revert unrelated dirty worktree changes.

## Fixes Applied

- P1: Ran Ruff format on the 7 files reported by `ruff format --check`.
- P2: Removed Python entrypoint `os.environ.setdefault(...)` thread-count defaults from `clearml/app.py`, `scripts/make_sample_data.py`, and `scripts/local_run.py`.
- P2: Resolved R13 workflow TODOs by documenting GitHub-hosted runners as the portable PR validation baseline.
- P3: Updated active MkDocs contributor docs to reflect the current tabular artifact writer split.
- P3: Resolved the R23 workflow TODO by documenting PR build and `main`-only Pages deployment behavior.
- Docs: Rewrote the reviewer recheck report/findings/work log to record the resolved state.

## Commands

```text
uv run python -m ruff format pkgs/core/src/ml_platform_core/config_models.py pkgs/tabular/src/ml_platform_tabular/training/leaderboard_artifacts.py pkgs/tabular/src/ml_platform_tabular/training/summary.py tests/test_clearml_params.py tests/test_clearml_pipeline_plan.py tests/test_clearml_reporting.py tests/test_clearml_templates.py
uv run python -m ruff format --check .
uv run python -m compileall clearml pkgs scripts
uv run python -m ruff check .
uv run python -m pytest
uv run python -m pre_commit run --all-files
```

## Results

- `uv run python -m ruff format ...`: passed, 7 files reformatted.
- `uv run python -m ruff format --check .`: passed, `97 files already formatted`.
- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m ruff check .`: passed, `All checks passed!`.
- `uv run python -m pytest`: passed, `128 passed in 5.24s`.
- `uv run python -m pre_commit run --all-files`: passed, all hooks passed.

## Targeted Evidence

- R13 TODO removed and runner policy documented:
  - `.github/workflows/ci.yml:10`
  - `.github/workflows/smoke-test.yml:11`
- R23 TODO removed and Pages workflow behavior documented:
  - `.github/workflows/deploy-mkdocs.yml:20`
  - `.github/workflows/deploy-mkdocs.yml:32`
  - `.github/workflows/deploy-mkdocs.yml:48`
- Thread defaults are workflow-owned for smoke tests:
  - `.github/workflows/smoke-test.yml:14`
  - `.github/workflows/smoke-test.yml:15`
  - `.github/workflows/smoke-test.yml:16`
- Active tabular docs now point artifact changes to writer modules:
  - `docs/ml_platform_mkdocs/docs/development/add-feature-or-metric.md:20`
  - `docs/ml_platform_mkdocs/docs/development/add-feature-or-metric.md:21`
  - `docs/ml_platform_mkdocs/docs/development/guidelines.md:10`

## Failures / Unknowns

- None for P1/P2/P3 local validation.
- Bare `python -m ...` remains host-dependent on this Windows environment; use `uv run python ...`.
- `vulture` and `deptry` were unavailable during the original reviewer recheck.
- ClearML server/UI, remote agent execution, GitHub Pages remote deployment, and Kubernetes validation were not executed.

## Final Judgment

`pass_with_notes`

All open P1/P2/P3 reviewer recheck findings are resolved locally. Full compileall, pytest, Ruff check, Ruff format check, and pre-commit pass.

## Next Action

Commit the fix and review docs. Keep remote infrastructure validation as separate follow-up work.
