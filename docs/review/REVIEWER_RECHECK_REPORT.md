# Reviewer Recheck Report

## Review Metadata

- Review date: 2026-07-01 (Asia/Tokyo)
- Branch: `cleanup/s00-lean-codebase-audit`
- Base commit: `d794986` (`docs: record lean codebase completion judgment`)
- Worker: Codex
- Scope: fix and recheck P1/P2/P3 findings from the reviewer-style recheck.
- Overall judgment: `pass_with_notes`

## Source Review Documents

Read during the original recheck and used again for the fix pass:

- `docs/review/source/pr28_review_consolidated.md`
- `docs/review/source/repository_review_transcription_current.md`
- `docs/review/source/tabular_package_review_analysis.md`
- `docs/adr/0002-runtime-spec-and-package-manifest-boundary.md`
- `docs/review/PR28_REVIEW_MAP.md`
- `docs/review/SECOND_REVIEW_MAP.md`
- `docs/review/SIMPLIFICATION_FIX_MAP.md`
- `AGENTS.md`

## Scope

This pass fixed the open P1/P2/P3 items recorded by the reviewer recheck:

- P1 Ruff format gate failure.
- P2 import-time thread env defaults.
- P2 unresolved R13 workflow runner TODO.
- P3 stale tabular ownership docs.
- P3 unresolved R23 Pages workflow TODO.

No git push was performed. No secrets, credentials, ClearML API keys, or `.env` contents were inspected. No Kubernetes/K8 commands were run.

## Commands Executed

```text
uv run python -m ruff format pkgs/core/src/ml_platform_core/config_models.py pkgs/tabular/src/ml_platform_tabular/training/leaderboard_artifacts.py pkgs/tabular/src/ml_platform_tabular/training/summary.py tests/test_clearml_params.py tests/test_clearml_pipeline_plan.py tests/test_clearml_reporting.py tests/test_clearml_templates.py
uv run python -m ruff format --check .
uv run python -m compileall clearml pkgs scripts
uv run python -m ruff check .
uv run python -m pytest
uv run python -m pre_commit run --all-files
```

Targeted searches:

```text
Select-String ... -Pattern 'TODO(R13)','TODO(R23)','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','leaderboard, summary, and artifact output'
rg -n "GitHub-hosted runner|Ruff format check" .github/workflows/ci.yml .github/workflows/smoke-test.yml
rg -n "Build documentation|Upload Pages artifact|Deploy to GitHub Pages" .github/workflows/deploy-mkdocs.yml
rg -n "evaluation orchestration|leaderboard_artifacts|Evaluation artifacts" docs/ml_platform_mkdocs/docs/development
```

## Test Results

| Check | Result | Notes |
| --- | --- | --- |
| `uv run python -m ruff format ...` | passed | 7 files reformatted. |
| `uv run python -m ruff format --check .` | passed | `97 files already formatted`. |
| `uv run python -m compileall clearml pkgs scripts` | passed | Changed Python files compiled. |
| `uv run python -m ruff check .` | passed | `All checks passed!` |
| `uv run python -m pytest` | passed | `128 passed in 5.24s`. |
| `uv run python -m pre_commit run --all-files` | passed | All hooks passed, including Ruff format check. |

## Overall Judgment

`pass_with_notes`

Rationale:

- P0/P1/P2/P3 open findings are now closed.
- Full compileall, pytest, Ruff lint, Ruff format, and pre-commit all pass via `uv`.
- Remaining notes are external or environment-scoped: bare `python` PATH behavior, optional `vulture`/`deptry` availability, ClearML remote/UI checks, GitHub Pages remote deployment, and Kubernetes validation.

## Summary By Area

### R01/R21 Tooling

Resolved. The Ruff format debt was fixed and both the direct format check and pre-commit hook pass.

Evidence:

- `.github/workflows/ci.yml:28`
- `.pre-commit-config.yaml:21`
- `uv run python -m ruff format --check .`
- `uv run python -m pre_commit run --all-files`

### R03 Runtime Thread Defaults

Resolved for Python import-time behavior. Thread defaults are no longer set inside `clearml/app.py`, `scripts/make_sample_data.py`, or `scripts/local_run.py`. The smoke workflow keeps environment-level thread defaults.

Evidence:

- `.github/workflows/smoke-test.yml:14`
- `clearml/app.py:1`
- `scripts/make_sample_data.py:1`
- `scripts/local_run.py:1`

### R13 Workflow Runner

Resolved for repository-local workflow text. CI and smoke workflows now explicitly state that GitHub-hosted runners are used for portable PR validation.

Evidence:

- `.github/workflows/ci.yml:10`
- `.github/workflows/smoke-test.yml:11`

### R23 Docs Workflow

Resolved for repository-local workflow text. The MkDocs workflow now states that documentation builds on PRs and deploys the Pages artifact only from `main`.

Evidence:

- `.github/workflows/deploy-mkdocs.yml:20`
- `.github/workflows/deploy-mkdocs.yml:32`
- `.github/workflows/deploy-mkdocs.yml:48`

### Tabular Package Structure Docs

Resolved. Active contributor docs now describe `training/evaluation.py` as orchestration/result assembly and direct artifact work to the focused writer modules.

Evidence:

- `docs/ml_platform_mkdocs/docs/development/add-feature-or-metric.md:20`
- `docs/ml_platform_mkdocs/docs/development/add-feature-or-metric.md:21`
- `docs/ml_platform_mkdocs/docs/development/guidelines.md:10`

## Remaining Risks

- Bare `python -m ...` commands may still fail on this Windows host because `python` resolves to the Windows Store alias. Use `uv run python ...` for repository validation.
- `vulture` and `deptry` were unavailable during the reviewer recheck; unused-code/dependency deletion proof can be revisited in a separate tool-backed pass.
- ClearML server/UI, remote agent execution, GitHub Pages remote deployment, and Kubernetes cluster validation were not executed in this local pass.

## Recommended Next Actions

1. Commit the fix and updated reviewer recheck docs.
2. Keep any future ARC runner migration, Pages settings verification, ClearML remote validation, and K8 validation as separate infrastructure tasks.

Recommended commit message:

```text
chore: close reviewer recheck findings

Review-Refs: R01-R27,TABULAR-SPLIT,SECOND-REVIEW,LEAN
Portability: target-repo-sync
```
