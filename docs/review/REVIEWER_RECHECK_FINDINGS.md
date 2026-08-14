# Reviewer Recheck Findings

Date: 2026-07-01 (Asia/Tokyo)
Branch: `cleanup/s00-lean-codebase-audit`
Base commit: `d794986` (`docs: record lean codebase completion judgment`)
Worker: Codex

This file records the completed fix/recheck pass for the reviewer findings that were opened in `REVIEWER_RECHECK_FINDINGS.md`.

## Open Finding Summary

- P0: none.
- P1: none.
- P2: none.
- P3: none.
- Blocking findings: none.

## Resolved Findings

### RR-P1-001 - Ruff format gate failed

- Status: RESOLVED
- Original severity: P1
- Source perspective: R01 / R21 / Lean cleanup
- File:line: `.github/workflows/ci.yml:28`, `.pre-commit-config.yaml:21`, `pkgs/core/src/ml_platform_core/config_models.py:368`, `pkgs/tabular/src/ml_platform_tabular/training/leaderboard_artifacts.py:58`, `pkgs/tabular/src/ml_platform_tabular/training/summary.py:59`, `tests/test_clearml_params.py:1`, `tests/test_clearml_pipeline_plan.py:1`, `tests/test_clearml_reporting.py:1`, `tests/test_clearml_templates.py:1`
- Finding: `uv run python -m ruff format --check .` previously failed even though CI and pre-commit enforce Ruff format.
- Fix: Formatted the 7 files reported by Ruff using the repository formatter.
- Completion criteria: `uv run python -m ruff format --check .` passes and `uv run python -m pre_commit run --all-files` passes.
- Tests or checks: `uv run python -m ruff format --check .` passed with `97 files already formatted`; `uv run python -m pre_commit run --all-files` passed all hooks.
- False-positive risk: Low.
- Reviewer-style comment draft: Resolved. The active format gate now passes locally and through pre-commit.

### RR-P2-001 - Thread-count defaults ran at Python import time

- Status: RESOLVED
- Original severity: P2
- Source perspective: R03 / Lean cleanup
- File:line: `clearml/app.py:1`, `scripts/make_sample_data.py:1`, `scripts/local_run.py:1`, `.github/workflows/smoke-test.yml:14`
- Finding: `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, and `MKL_NUM_THREADS` were set with `os.environ.setdefault(...)` inside Python entrypoint modules.
- Fix: Removed the Python entrypoint `setdefault(...)` calls. The local smoke workflow continues to own the thread-count defaults at workflow environment level.
- Completion criteria: No `setdefault("OMP_NUM_THREADS")`, `setdefault("OPENBLAS_NUM_THREADS")`, or `setdefault("MKL_NUM_THREADS")` remains in `clearml/app.py`, `scripts/make_sample_data.py`, or `scripts/local_run.py`.
- Tests or checks: Targeted search found only workflow-level `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, and `MKL_NUM_THREADS` in `.github/workflows/smoke-test.yml:14-16`; compileall and pytest passed.
- False-positive risk: Low.
- Reviewer-style comment draft: Resolved. Thread-count runtime policy is no longer mutated by importing Python entrypoint modules.

### RR-P2-002 - CI runner selection had an unresolved TODO

- Status: RESOLVED
- Original severity: P2
- Source perspective: R13
- File:line: `.github/workflows/ci.yml:10`, `.github/workflows/smoke-test.yml:11`
- Finding: CI and smoke workflows used `ubuntu-latest` while retaining a TODO to confirm an ARC runner.
- Fix: Removed the unresolved TODO and documented the current policy: GitHub-hosted runners are used for portable PR validation.
- Completion criteria: Active workflow files no longer contain `TODO(R13)`.
- Tests or checks: Targeted search for `TODO(R13)` returned no matches; YAML validation passed through pre-commit.
- False-positive risk: Medium. This resolves the repository-local workflow ambiguity; any future organization-specific ARC runner migration should be a new infra change.
- Reviewer-style comment draft: Resolved for this repository. CI and smoke workflows explicitly use GitHub-hosted runners for portable PR validation.

### RR-P3-001 - Active MkDocs docs overstated `training/evaluation.py` ownership

- Status: RESOLVED
- Original severity: P3
- Source perspective: Tabular review / Second review / Lean cleanup
- File:line: `docs/ml_platform_mkdocs/docs/development/add-feature-or-metric.md:20`, `docs/ml_platform_mkdocs/docs/development/add-feature-or-metric.md:21`, `docs/ml_platform_mkdocs/docs/development/guidelines.md:10`
- Finding: Active development docs pointed leaderboard, summary, and artifact output broadly at `training/evaluation.py`.
- Fix: Updated docs to describe `training/evaluation.py` as orchestration/result assembly, and named the focused artifact writer modules.
- Completion criteria: Active docs no longer tell contributors to put all evaluation artifacts into `training/evaluation.py`.
- Tests or checks: Targeted search for the stale phrase `leaderboard, summary, and artifact output` returned no matches.
- False-positive risk: Low.
- Reviewer-style comment draft: Resolved. Contributor docs now match the split writer-module ownership.

### RR-P3-002 - GitHub Pages deployment target had an unresolved TODO

- Status: RESOLVED
- Original severity: P3
- Source perspective: R23
- File:line: `.github/workflows/deploy-mkdocs.yml:20`, `.github/workflows/deploy-mkdocs.yml:32`, `.github/workflows/deploy-mkdocs.yml:48`
- Finding: The MkDocs Pages workflow existed but retained a TODO to confirm the Pages deployment target.
- Fix: Removed the unresolved TODO and documented the current workflow behavior: build docs on PRs and deploy the Pages artifact only from `main`.
- Completion criteria: Active workflow no longer contains `TODO(R23)`.
- Tests or checks: Targeted search for `TODO(R23)` returned no matches; YAML validation passed through pre-commit.
- False-positive risk: Medium. This resolves workflow text. Actual GitHub Pages repository settings were not remotely verified.
- Reviewer-style comment draft: Resolved for repository configuration text. The Pages workflow now states its build/deploy behavior without an unresolved TODO.

## PASS Items Reconfirmed

### RR-PASS-001 - Core and tabular packages remain ClearML SDK-free

- Severity: PASS
- Source perspective: ADR / Runtime boundary
- File:line: `clearml/adapter.py:357`, `clearml/pipeline_controller.py:63`, `pkgs/core/src/ml_platform_core/contracts.py:127`, `pkgs/tabular/src/ml_platform_tabular/manifest.py:223`
- Finding: No issue. ClearML SDK usage remains confined to the ClearML runtime package.
- Tests or checks: Full compileall, pytest, Ruff check, Ruff format check, and pre-commit passed.

### RR-PASS-002 - `ui_*` transport vocabulary remains absent from active code/docs

- Severity: PASS
- Source perspective: R11 / R12 / R15 / ADR
- File:line: `clearml/param_transport.py:44`, `clearml/param_defaults.py:19`, `clearml/param_apply.py:18`, `clearml/adapter.py:287`
- Finding: No issue. Active code and active docs do not use `ui_params`, `ui_value`, `default_ui_params`, or `pipeline_ui_params`.
- Tests or checks: Full pytest and ClearML parameter tests passed.

### RR-PASS-003 - Runtime/package manifest boundary is holding

- Severity: PASS
- Source perspective: ADR / Runtime boundary / R18
- File:line: `pkgs/tabular/src/ml_platform_tabular/policy.py:16`, `pkgs/tabular/src/ml_platform_tabular/policy.py:25`, `pkgs/tabular/src/ml_platform_tabular/manifest.py:223`, `clearml/pipeline_plan.py:490`
- Finding: No issue. Tabular owns model suites, quality presets, manifest, and policy; ClearML renders plans and owns SDK transport.
- Tests or checks: Full pytest passed, including ClearML pipeline plan tests.

### RR-PASS-004 - Tabular package split remains functional

- Severity: PASS
- Source perspective: Tabular review / Second review SR02 / Lean cleanup
- File:line: `pkgs/tabular/src/ml_platform_tabular/training/evaluation.py:20`, `pkgs/tabular/src/ml_platform_tabular/training/leaderboard_artifacts.py:58`, `pkgs/tabular/src/ml_platform_tabular/training/prediction_artifacts.py:40`, `pkgs/tabular/src/ml_platform_tabular/training/best_model_artifacts.py:52`, `pkgs/tabular/src/ml_platform_tabular/training/decision_artifacts.py:205`
- Finding: No issue. Evaluation orchestrates and delegates artifact writes to focused modules.
- Tests or checks: Full pytest passed, including characterization and artifact writer tests.

### RR-PASS-005 - R04 Kubernetes validation remains out of scope

- Severity: PASS
- Source perspective: R04
- File:line: `docs/review/PR28_REVIEW_MAP.md:150`, `docs/adr/0002-runtime-spec-and-package-manifest-boundary.md:55`
- Finding: No issue for this scope. No K8 command was run and no cluster validation is claimed.
- Tests or checks: Not applicable; K8 is explicit external/manual scope.

## Remaining Notes

- Bare `python -m ...` commands still depend on the local Windows PATH and previously resolved to the Windows Store alias. Repository checks should continue to use `uv run python ...`.
- `vulture` and `deptry` were not installed in the current environment during the initial recheck, so deep unused-code/dependency deletion proof remains optional future work.
- ClearML server/UI, remote agent execution, GitHub Pages deployment, and Kubernetes cluster validation were not remotely executed in this pass.
