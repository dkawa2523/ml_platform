# Simplification Remaining Backlog

Date: 2026-06-30

This backlog organizes the remaining simplification work after the ClearML
parameter, pipeline, source-resolution, reporting, stage, manifest, and
evaluation-writer splits. It is a planning and review aid; it does not authorize
deleting remaining runtime compatibility surfaces by itself.

## Current Signals

| Signal | Current finding |
|---|---|
| Largest file | `tests/test_clearml_pipeline_plan.py`, 596 lines; largest implementation file is `clearml/adapter.py`, 566 lines |
| Remaining format debt | cleared on 2026-06-30; `ruff format --check .` now passes |
| ClearML import boundary | `lint-imports` keeps `pkgs/core` and `pkgs/tabular` ClearML-free |
| Average radon complexity | no C-level functions remain in `clearml`, `pkgs`, or `scripts` |
| Highest live complexity clusters | C-level assertion helpers remain in contract tests; no D-level test functions remain |

## Priority Backlog

| Priority | Area | Problem | Concrete improvement | Guardrail |
|---|---|---|---|---|
| Done | Formatting debt | Formatting check still failed, making later diffs noisy. | Reformatted the 8 known files on 2026-06-30. | Keep future formatting changes separate from behavior changes. |
| Done | ClearML behavior tests | `tests/test_clearml_mapping.py` mixed params, reporting, templates, and pipeline plan tests. | Split into `test_clearml_params.py`, `test_clearml_reporting.py`, `test_clearml_templates.py`, `test_clearml_pipeline_plan.py`, and source resolution tests. `test_clearml_mapping.py` is now 315 lines. | Move tests only; do not weaken assertions. |
| Done | Tabular feature/data selection | `select_features`, `FeatureTransformer.fit/transform`, and data-quality summary carried several branches. | Split column selection, fit-time role detection, transform array generation, and data-quality warning builders on 2026-06-30. | Do not change output column order or schema check behavior. |
| Done | Inference flow | `run_infer`, `_resolve_directory_model_path`, and `_schema_check_summary` mixed source resolution, schema diagnostics, and output assembly. | Split runner context loading/schema/prediction/manifest helpers, selector candidate checks, and schema summary helpers on 2026-06-30. | Preserve `predictions.csv` slim output and schema failure messages. |
| Done | ClearML params / pipeline plan | `clearml/params.py`, `pipeline_plan.py`, and `pipeline_controller.py` contained C-level functions around UI params, graph rendering, metadata, and cleanup. | Grouped model/source param handling, separated domain step rendering from graph metadata, and extracted draft/tag helpers on 2026-06-30. | Parameter names are UI/API surface; require ClearML mapping tests and dry-runs. |
| Done | Training orchestration / ensemble | `_build_ensemble` and `_run_training_pipeline` used to mix sequencing, artifact assembly, and reporting output maps. | Split ensemble internals and pipeline orchestration helpers on 2026-06-30. `_run_training_pipeline` is now a linear coordinator and both files report radon A-level functions. | Preserve live inference-critical artifact names and leaderboard semantics; redundant aliases may be deleted with tests. |
| Done | Tabular model/policy/domain planning | Model candidate normalization, model factory branches, runtime policy defaults, and domain graph construction were harder to scan. | Split candidate parsing, model factory specs, runtime default maps, ensemble method normalization, and domain step builders on 2026-06-30. | Keep supported model names, optional dependency errors, and graph step names stable. |
| Done | Config compatibility / contracts | `config_compat.to_legacy_dict`, contract validation, value coercion, and table-file discovery carried compatibility branches. | Replaced long branch chains with serializer tables and small validation/coercion/path helpers while keeping public wrappers. | Do not remove typed config or manifest validation without replacement tests. |
| Done | Plotting modules | Some plot/table writers mixed filtering, summarizing, and drawing. | Extracted small data-prep and drawing helpers for metric bars, leaderboard panels, Pareto plots, prediction summaries, and candidate metric tables. | ClearML should continue reporting package-produced plot artifacts only. |
| Done | Tabular public facades | `ml_platform_tabular.infer`, `pipeline`, and `plots` were thin compatibility modules after the split. | Migrated runner paths and tests to `ml_platform_tabular.inference`, `training`, and `plotting`, then deleted the facade modules on 2026-06-30. | Port runner path changes together with the deletions. |
| Done | ClearML adapter/template compatibility | `clearml_projects`, metadata application, and template sync mixed data layout, SDK fallback, dry-run printing, and remote sync. | Split project layout, tag/comment application, template settings, dry-run printers, task template sync, and pipeline template sync. | Keep SDK signature fallbacks until remote Agent verification says they can go. |
| Done | Smoke/characterization test contracts | Large contract tests made failures hard to scan. | Split pipeline/stage/characterization assertions into output-key, path-existence, leaderboard, decision, manifest, and inference selector helpers. | Preserve exact artifact/table/plot names and schema assertions. |
| P2 | ClearML SDK compatibility | `_entrypoint_bootstrap.py`, script metadata compatibility helpers, SDK signature fallbacks, and legacy template cleanup remain. | Delete only after remote Agent training/inference templates run without direct-entrypoint bootstrap and old drafts are retired. | Remote ClearML verification required. |
| P2 | Requirements files | `requirements*.txt` may still be used by Docker, ClearML images, docs setup, or legacy onboarding. | Keep until Docker, ClearML, docs, CI, and onboarding checks prove they are unused. | Use deptry plus manual setup-path review before deletion; current tool findings do not prove these are removable. |
| P3 | Contract-test C-level helpers | Some tests still have C-level assertion helpers because they intentionally pin large public surfaces. | Optionally shrink further only when a failure pattern shows the helper is hard to debug. | Do not replace precise contract checks with broad smoke-only checks. |
| P3 | Review/evidence docs | `docs/review/source` is historical evidence and contains old code/text by design. | Do not rewrite as active product docs. Only add current summary docs when useful. | Not a deletion candidate unless explicitly archiving review evidence. |

## Delete / Keep Rules

Delete now only when all are true:

- The symbol/file is not a ClearML template entrypoint, artifact
  name, parameter key, or compatibility setup input.
- Repo grep and tests show no live use.
- If dependency or dead-code related, vulture/deptry or equivalent evidence is
  available and false positives are documented.
- Full tests and ClearML dry-runs pass after removal.

Keep for now:

- `clearml/app.py`, `clearml/pipelines.py`, and `_entrypoint_bootstrap.py`.
- `requirements.txt`, `requirements-dev.txt`, and docs requirements files.
- Existing ClearML parameter names, artifact names, table names, and prediction
  column order.

## Recommended Next Order

1. Re-run vulture/deptry in future deletion passes and document false positives.
2. Handle remote ClearML deletion gates only after actual Agent verification.
3. Review requirements files after target-repo Docker/ClearML/docs usage is known.
4. Optionally shrink C-level test assertion helpers if they become noisy during maintenance.

## Verification Baseline

Use this after each cleanup batch:

```powershell
uv run python -m compileall clearml pkgs scripts
uv run python -m pytest -q
uv run python -m ruff check .
uv run lint-imports --config pyproject.toml
uv run python scripts\clearml_pipeline.py --task config\tasks\tabular_pipeline.yaml --profile config\profiles\clearml-dev.yaml --dry-run
uv run python scripts\sync_clearml_templates.py --profile config\profiles\clearml-dev.yaml --dry-run
uv run --group docs python -m mkdocs build --config-file docs\ml_platform_mkdocs\mkdocs.yml --strict
```

`uv run python -m ruff format --check .` is expected to pass after the
2026-06-30 formatting cleanup.

## Progress Log

- 2026-06-30: Reformatted the 8 known format-debt files. Full
  `ruff format --check .` now passes.
- 2026-06-30: Added `tests/clearml_test_utils.py` and moved ClearML inference
  source resolution tests to `tests/test_clearml_source_resolution.py`.
  `tests/test_clearml_mapping.py` later dropped to 1507 lines.
- 2026-06-30: Split `_build_ensemble()` into candidate selection, per-method
  estimator/evaluation, member tables, prediction artifacts, metrics summary,
  best-copy, reference artifacts, and output-map helpers. The ensemble builder
  no longer has D-level complexity; all functions in `training/ensemble.py`
  report radon A.
- 2026-06-30: Split `_run_training_pipeline()` into search/metric validation,
  pipeline output assembly, summary construction, and final manifest writing.
  The pipeline coordinator now reports radon A and keeps artifact names unchanged.
- 2026-06-30: Split tabular feature/data selection, inference runner/schema/
  resolver, ClearML params/pipeline plan/controller, tabular policy/model/domain
  plan, and data-quality/evaluation helpers. The primary P1 implementation
  hotspots now act as small coordinators with stable artifact and UI parameter
  names.
- 2026-06-30: Split ClearML mapping tests into behavior files, simplified
  ClearML adapter/template compatibility helpers, core config/value/io contracts,
  plotting data-prep/drawing helpers, and smoke/characterization assertion
  helpers. `uv run radon cc clearml pkgs tests -s -n D` now reports no D-level
  functions, and `uv run radon cc clearml pkgs scripts -s -n C` reports no
  C-level implementation functions.
- 2026-06-30: Removed redundant training-output contracts: duplicate candidate
  metrics JSON, duplicate leaderboard decision table, standalone inference
  decision JSON, preprocessing table/plot aliases, and per-method ensemble-info aggregate
  JSON. Evaluation and ensemble artifact writers now own the remaining canonical
  outputs.
- 2026-06-30: Removed confirmed unused model-info loader helpers, the unused
  `EvaluationResult.to_dict()` compatibility wrapper, ClearML profile `queue`
  aliases, and the stale review README contents. Remaining vulture findings are
  config-field and runner-path false positives.
- 2026-06-30: Migrated tabular runner paths to implementation packages and
  deleted the old `ml_platform_tabular.infer`, `pipeline`, and `plots` facade
  modules.
