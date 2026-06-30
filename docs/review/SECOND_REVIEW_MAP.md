# Second Review Response Map

Additional reviewer findings after the PR28 response are tracked here as
`SR01` through `SR10`. These items are intentionally separate from the original
`R01` through `R27` review map and from the lean-codebase `Sxx` cleanup map.

Scope rules:

- Items are marked `done` only after implementation and verification are recorded
  in `SECOND_REVIEW_WORK_LOG.md`.
- Kubernetes / K8 verification remains out of scope.
- Deletion candidates require explicit gates before removal.
- ClearML template runner compatibility must be preserved until verified.
- `docs/review/source/` is evidence and is not a deletion candidate.

## Priority Order

| Priority | Items | Intended order |
|---|---|---|
| P1 | SR01, SR02 | Completed first. These were the highest-impact readability and ownership issues. |
| P2 | SR03, SR05 | Completed after P1 because they depend on clearer artifact/config ownership. |
| P2 deferred | SR04 | Do only after ClearML Remote Agent template execution is verified. |
| P3 | SR06 | Completed after the larger splits stabilized. |
| Deletion gated | SR07, SR08 | Do only after internal, target-repo, and external usage gates pass. |
| Cleanup | SR09, SR10 | SR09 is covered by the Lean docs cleanup; SR10 remains deferred until vulture/deptry are run. |

## Final Completion Status - 2026-06-30

Completion: `pass_with_notes`

- Done: SR01, SR02, SR03, SR05, SR06, SR09.
- Deferred: SR04, SR07, SR08, SR10.
- Needs confirmation: none as an active status; deletion gates remain documented.
- Blocked: none.
- Notes: local `uv run python` verification passes for compileall, pytest, and
  ruff check. Bare `python` resolves to the Windows Store alias in this
  environment. Ruff format / pre-commit still fail only on known formatting
  debt outside this finalization pass.

## ClearML Expert Notes

- The repository correctly keeps ClearML SDK usage outside `pkgs/core` and
  `pkgs/tabular`; that boundary should remain.
- The top-level `clearml/` directory is kept for existing direct-entrypoint
  template compatibility, but it can shadow the official ClearML SDK name and
  should remain a long-term rename candidate only after remote verification.
- ClearML task parameters are part of the runtime API surface. Their mapping
  should have one canonical owner and should avoid tabular policy decisions.
- ClearML reporting should prefer reporting already-produced artifacts over
  reconstructing tabular domain plots from CSV files.

## SR Items

| ID | Priority | Target files | Problem | Proposed action | Status | Risk | Required tests | Deletion gate | Commit | Reviewer reply draft | Porting note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SR01 | P1 | `clearml/adapter.py`, `clearml/pipelines.py`, `clearml/params.py`, `pkgs/tabular/src/ml_platform_tabular/policy.py` | `default_runtime_params` and `apply_runtime_params` combined ClearML parameter transport, config mutation, type conversion, and compatibility handling. | Added `clearml/params.py` as the ClearML parameter transport owner. Kept tabular defaults and model-suite policy in tabular policy/manifest modules. | done | High: parameter names are ClearML UI/API surface and affect existing templates. | `uv run python -m pytest tests/test_clearml_mapping.py -q`; `uv run python -m compileall clearml pkgs scripts`; `uv run python -m pytest`; `uv run python -m ruff check .`; `uv run python -m ruff format --check .` | N/A | pending commit | ClearML parameter transport is now isolated in `clearml/params.py`; `adapter.py` delegates default generation and config application while retaining SDK operations. | Port before SR02 if cherry-picking; conflicts are likely in `clearml/adapter.py`, `clearml/pipelines.py`, and `tests/test_clearml_mapping.py`. |
| SR02 | P1 | `pkgs/tabular/src/ml_platform_tabular/training/evaluation.py`, `training/leaderboard_artifacts.py`, `training/prediction_artifacts.py`, `training/best_model_artifacts.py`, `training/decision_artifacts.py` | `evaluate_model_candidates` owned ranking, leaderboard, prediction table, plots, best-model copy, decision guidance, decision summary, and report JSON. | Split artifact writing into focused leaderboard, prediction, best-model, and decision/report writers while keeping evaluation ranking and result assembly in `evaluation.py`. | done | High: training output artifacts are user-facing and ClearML reporting consumes them. | `uv run python -m pytest tests/test_evaluation_artifact_writers.py tests/test_tabular_characterization.py tests/test_pipeline_smoke.py::test_local_training_pipeline_default_graph_and_artifacts`; `uv run python -m compileall clearml pkgs scripts`; `uv run python -m pytest`; `uv run python -m ruff check .`; `uv run python -m ruff format --check .` | N/A | pending commit | Evaluation artifact writers are split and covered by writer/unit and characterization tests. Active artifact/table/plot names, `EvaluationResult`, and `evaluate_model_candidates()` public API are covered by tests; redundant aliases were removed in the simplification pass. | Port after SR01. Preserve the four writer modules with `evaluation.py` so artifact paths and result assembly stay aligned. |
| SR03 | P2 | `clearml/reports.py`, `tests/test_clearml_mapping.py`, `pkgs/tabular/src/ml_platform_tabular/plotting/*` | ClearML reporting read CSV outputs and reconstructed prediction/leaderboard plots, duplicating tabular plotting logic. | Removed ClearML-side domain plot reconstruction. `clearml/reports.py` now uploads artifacts/tables, publishes scalar metrics, and reports existing plot artifacts generated by the tabular package. | done | Medium: ClearML UI behavior can regress if reported artifacts change shape. Manual ClearML UI verification is still useful. | `uv run python -m pytest tests/test_clearml_mapping.py -q`; `uv run python -m compileall clearml pkgs scripts`; `uv run python -m pytest`; `uv run python -m ruff check .`; grep confirms removed plot reconstruction helpers. | N/A | pending commit | ClearML reporting no longer rebuilds tabular plots from CSV data. It keeps ClearML-specific upload/table/image/scalar API calls and reports tabular-owned plot artifacts. | Port after SR02 so the writer-produced plot artifact names exist before reporting is simplified. |
| SR04 | P2 deferred | `clearml/_entrypoint_bootstrap.py`, `clearml/app.py`, `clearml/pipelines.py`, `clearml/templates.py` | Direct-entrypoint `sys.path` bootstrap remains for ClearML remote/template compatibility. | Delete bootstrap only after Remote Agent template execution confirms package/module entrypoints work without it. | deferred | High: removing this too early can break remote ClearML templates. | ClearML template sync dry-run; pipeline dry-run; actual remote training template; actual remote inference template. | Remote Agent verification completed and old direct-entrypoint templates retired. | pending | We agree this bootstrap is technical debt. It is intentionally deferred until ClearML Remote Agent execution is verified, because the current templates still rely on direct-entrypoint compatibility. | Do not include in portable patch sets unless the target repo has verified remote Agent execution. |
| SR05 | P2 | `pkgs/core/src/ml_platform_core/config_models.py`, `pkgs/core/src/ml_platform_core/config_compat.py`, `tests/test_config_models.py` | `RunConfig` mixed typed config behavior with legacy dict compatibility serialization. | Added `config_compat.py` as the owner for legacy dict serialization and present-section helpers. Kept `to_dict()` methods as thin compatibility wrappers that delegate to the new module. | done | Medium: local scripts and tests may still depend on dict shape, so wrappers remain until callers migrate. | `uv run python -m pytest tests/test_config_models.py -q`; `uv run python -m compileall clearml pkgs scripts`; `uv run python -m pytest`; `uv run python -m ruff check .`; `uv run python -m ruff format --check .` | N/A | pending commit | Typed config models now keep field definitions, parsing, and validation. Legacy dict serialization lives in `config_compat.py`; existing `.to_dict()` APIs remain as compatibility wrappers. | Port after SR01 if parameter application depends on typed config behavior. Include `config_compat.py` and config model tests together. |
| SR06 | P3 | `pkgs/tabular/src/ml_platform_tabular/models.py`, `tests/test_tabular_smoke.py` | Optional dependency import handling used broad `except Exception`, which could hide package-internal errors. | Added `OptionalDependencyError`, narrowed dependency catches to `ModuleNotFoundError` / `ImportError`, handled missing optional model classes via `AttributeError`, and let unexpected runtime errors surface. | done | Low to medium: optional GBM behavior must still degrade clearly when dependencies are absent. | `uv run python -m pytest tests/test_tabular_smoke.py -k optional_dependency`; `uv run python -m compileall clearml pkgs scripts`; `uv run python -m pytest`; `uv run python -m ruff check .`; `uv run python -m ruff format --check .` | N/A | pending commit | Optional dependency failures now distinguish missing package, import failure, missing estimator class, and internal runtime errors. Messages mention `uv sync --extra gbm`, editable tabular extra install, and ClearML Agent images. | Small, low-conflict patch. Port with tests so target repos preserve optional dependency behavior. |
| SR07 | cleanup | `ml_platform_tabular.plots`, `ml_platform_tabular.infer`, `ml_platform_tabular.pipeline` | Public compatibility facades remained after module split. | Migrated repo runner paths and tests to implementation packages, then deleted the facade modules. | done | Medium: external imports may need target-repo migration. | Repo-wide import grep; runner path check; full tests. | N/A | pending | Current runner paths are `ml_platform_tabular.inference:run_infer` and `ml_platform_tabular.training:run_pipeline`; plot helpers live under `ml_platform_tabular.plotting`. | In target repos, port imports/runner paths before deleting the old modules. |
| SR08 | deletion gated | `requirements.txt`, `requirements-dev.txt` | Requirements files can become duplicate dependency management beside `pyproject.toml` and `uv.lock`. | Remove only after Docker, ClearML remote setup, docs setup, and CI are confirmed uv-only. | deferred | Medium: downstream setup scripts may still use pip requirements files. | `uv sync --group dev`; docs build; ClearML remote setup check; CI setup check; search for `pip install -r`. | All setup paths use uv or pyproject groups; no Docker/ClearML/docs/CI consumer remains. | pending | We agree duplicate dependency files are a maintenance risk. We will keep them until all setup paths are verified uv-only. | Target repo may still depend on requirements files; confirm before deletion. |
| SR09 | cleanup | `README.md`, `docs/*` | Future-scope notes and roadmap items still appeared in multiple active docs. | Lean cleanup S06/S07 pruned obsolete setup and architecture notes; README is operational and ROADMAP remains the future-scope home. | done | Low: docs-only, but user-facing instructions must stay current. | README command review; docs grep during Lean cleanup; `uv run python -m pytest`; `uv run python -m ruff check .`. | N/A | `8d3b726` | Active docs are kept operational and concise. Future-scope details are left in ROADMAP or review evidence instead of repeated in README. | Port after code-facing SRs so docs describe the final structure. |
| SR10 | cleanup | repository-wide | Unused code and dependency deletion still needs vulture/deptry confirmation. | Run vulture/deptry in a temporary or agreed dev-tool setup, triage false positives, and turn confirmed removals into small patches. | deferred | Medium: static tools can report false positives for entrypoints and public facades. | `python -m vulture ...`; `python -m deptry .`; full tests after each removal; entrypoint/template grep. | Tools available and false positives triaged; public entrypoints excluded. | pending | We agree further deletion should be tool-backed. This finalization does not delete more code without vulture/deptry evidence. | Keep separate from feature fixes; port small confirmed-removal commits after structural patches. |

## Deletion Candidate Gates

| Candidate | Gate before deletion |
|---|---|
| ClearML bootstrap (`clearml/_entrypoint_bootstrap.py`) | Remote Agent template train/infer execution works without direct-entrypoint path injection. |
| Public tabular facades (`infer`, `pipeline`, `plots`) | Repo grep, target-repo grep, ClearML template runner paths, and external import checks show no remaining dependency. |
| Requirements files | Docker, ClearML remote setup, docs, CI, and onboarding docs all use uv/pyproject only. |
| Unused code/dependencies | vulture/deptry results are triaged and tests pass after each removal. |

## Next Implementation Batches

1. SR10: run vulture/deptry in a dedicated cleanup pass before further deletion.
2. SR04, SR07, SR08: deletion-gated work after external confirmation.
