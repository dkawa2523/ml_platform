# Simplification Fix Map

This map tracks cleanup work separately from PR review IDs. LEAN-S00 only
creates tickets; no ticket is marked done in this audit.

Allowed statuses:

- `todo`
- `in_progress`
- `done`
- `needs_confirmation`
- `blocked`
- `deferred`

## Sxx Tickets

| ID | Category | Target files | Problem | Proposed action | Deletion allowed | Risk | Required tests | Status | Commit | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| S01 | confirmed unused code removal | repository-wide Python code | Dedicated unused-code tools are not installed, so broad live unused code cannot be safely confirmed yet. | Run `vulture` and targeted `rg` / import checks before deleting broader unused code. | No, not until confirmed by tools and tests. | Medium | `uv run python -m pytest`, import smoke tests, targeted entrypoint checks | needs_confirmation | pending | CLEAN-1 confirmed and removed only the one-line stale wrappers covered under S02. `vulture` remains unavailable. Do not treat `docs/review/source` matches as deletion candidates. |
| S02 | stale compatibility wrapper removal | `clearml/adapter.py`, `clearml/pipelines.py`, `clearml/templates.py`, `pkgs/tabular/src/ml_platform_tabular/{plots.py,infer.py,pipeline.py}` | Deprecated UI-named wrappers and facade modules remained after review-response migrations. | Remove confirmed one-line aliases now; keep public facades and ClearML script compatibility until external/template usage is confirmed. | Partially. One-line aliases are removed; public facades and ClearML script compatibility are not deletion-safe yet. | High | full pytest, `tests/test_clearml_mapping.py`, tabular characterization tests, ClearML dry-run | needs_confirmation | pending | CLEAN-1 removed `as_list`, `default_ui_params`, `grouped_ui_params`, `apply_ui_params`, `pipeline_ui_params`, and `_task_ui_params`. Remaining S02 candidates need external import or ClearML remote confirmation. |
| S03 | excessive contract/spec simplification | `pkgs/core/src/ml_platform_core/contracts.py`, `pkgs/tabular/src/ml_platform_tabular/manifest.py`, docs | One-implementation runtime Protocols and descriptive-only contract fields added cognitive load without an active runtime consumer. | Removed the unused `runtime_types.py` Protocol scaffold and trimmed manifest contracts to fields used for runner resolution, schema validation, artifact/parameter declarations, and domain plan rendering. | Yes, for the confirmed unused Protocol module and descriptive-only fields. | Medium | `tests/test_runtime_manifest.py`, fake renderer tests, full pytest | done | pending | Remaining manifest/policy module-size cleanup is tracked under S05/S08, not S03. |
| S04 | diagnostics and error handling simplification | `clearml/adapter.py`, `clearml/reports.py`, tests, docs | Reporting code mixed malformed output files with ClearML logger failures and silently swallowed broad errors. | Centralized JSON/CSV best-effort parsing, limited parse fallbacks to file/encoding/value errors, and stopped silencing non-`TypeError` ClearML logger failures. | Yes, for broad catch blocks and duplicate parsing helpers covered by tests. | Medium | ClearML mapping tests, report behavior tests, compileall, pytest | done | pending | Operator-facing dry-run/sync `print()` output remains. `clearml_dataset_exists()` keeps a broad SDK existence check because ClearML raises version-specific missing-dataset errors. |
| S05 | file responsibility cleanup after split | `clearml/adapter.py`, `clearml/pipelines.py`, `clearml/reports.py`, `training/evaluation.py`, `training/orchestrator.py`, `stage.py` | Large files still mix orchestration, IO, rendering, policy, and compatibility behavior. | Continue extracting cohesive private modules only where call sites become simpler. | No broad deletion; refactor only with characterization coverage. | Medium | full pytest, tabular characterization tests, targeted smoke tests | todo | pending | Avoid replacing one large context dict with many thin wrappers. |
| S06 | dependency and dev-tool pruning | `pyproject.toml`, `uv.lock`, `requirements*.txt`, `.pre-commit-config.yaml` | `vulture` and `deptry` are unavailable; ruff format debt remains. | Decide whether audit tools become dev deps; fix formatting separately if desired. | No dependency deletion until `deptry` or manual proof exists. | Medium | `uv lock`, `uv sync --frozen`, `uv run python -m pytest`, pre-commit | todo | pending | Keep requirements compatibility files unless Docker/ClearML paths change. |
| S07 | obsolete docs and comments cleanup | `docs/review/*.md`, `docs/adr/*.md`, non-source docs | Review docs contain historical notes, stale failure snapshots, and some garbled text outside source evidence. | Clean current-facing docs while preserving source evidence and review history. | Yes, for duplicate or stale current-facing docs after review. | Low | docs grep, link/path spot checks | todo | pending | Do not delete or rewrite `docs/review/source/*`. |
| S08 | ClearML runtime surface simplification | `clearml/_entrypoint_bootstrap.py`, `clearml/app.py`, `clearml/pipelines.py`, `clearml/templates.py`, `clearml/adapter.py` | Direct-entrypoint compatibility and SDK shadow guards keep runtime surface broad. | Confirm ClearML remote execution model, then reduce bootstrap and dynamic import paths. | Only after ClearML remote/template verification. | High | ClearML template dry-run, local script smoke, remote Agent manual verification, full pytest | needs_confirmation | pending | Do not rename `clearml/` in this cleanup branch. |
| S09 | tabular training/inference facade cleanup | `pkgs/tabular/src/ml_platform_tabular/{infer.py,pipeline.py,plots.py}`, `inference/*`, `training/*`, `plotting/*`, `stage.py`, tests | Compatibility facades re-export private helpers and tests still import them. | Migrate tests and `stage.py` to implementation packages; keep only true public facade exports. | Only after runner paths and external imports are confirmed. | High | `tests/test_tabular_characterization.py`, `tests/test_infer_schema_check.py`, `tests/test_stage_smoke.py`, full pytest | needs_confirmation | pending | Preserve `run_infer` and `run_pipeline` runner paths until intentionally migrated. |
| S10 | final lean validation and porting notes | docs and repository-wide checks | Cleanup needs a final pass to prove no behavior or porting contracts regressed. | Re-run all checks, update porting notes, and record residual failures explicitly. | N/A | Low | compileall, pytest, ruff check, ruff format check, radon, optional vulture/deptry | todo | pending | Kubernetes / K8 remains excluded. |

## First Recommended Cleanup Batch

1. S06: decide whether to add temporary or permanent `vulture` / `deptry`.
2. S09: migrate internal tests away from private facade helpers.
3. S02: keep remaining facades and ClearML script compatibility until target-import and remote-template confirmation.
4. S04/S05: reduce ClearML/reporting and tabular evaluation complexity in small
   behavior-preserving commits.
5. S10: run final validation and update porting notes.
