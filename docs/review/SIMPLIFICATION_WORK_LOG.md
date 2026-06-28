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
