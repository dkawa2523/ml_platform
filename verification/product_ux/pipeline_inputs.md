# Pipeline Input UX Verification

Date: 2026-06-09

Scope: Phase 2 ClearML Pipeline New Run parameter surface.

## Parameter Classification

Required for local training:

- `Input/local_path`
- `Input/target_column`

Required for ClearML remote training:

- `Input/clearml_dataset_id`
- `Input/dataset_file`
- `Input/target_column`

Optional primary parameters:

- `Input/feature_columns`
- `Input/id_columns`
- `Run/name`
- `Run/seed`
- `Model/candidates`
- `Model/model_params_by_name`
- `Model/evaluation_metrics`
- `Model/selection_metric`
- `Model/ensemble_enabled`
- `Model/ensemble_methods`
- `Model/ensemble_method` compatibility alias
- `Model/ensemble_top_k`
- `Output/report_plots`
- `Split/valid_size`
- `Features/preset`
- `Features/numeric_impute_strategy`
- `Features/categorical_impute_strategy`
- `Features/categorical_encoder`
- `Features/scaling`
- `Features/drop_columns`
- `Features/passthrough_columns`

Supported optional-dependency parameters:

- `lightgbm`, `xgboost`, and `catboost` in `Model/candidates`, only when the
  optional GBM dependencies are installed.

Future / hidden from primary Pipeline UI:

- `Run/pipeline_mode`
- search / optimization params
- `Output/artifact_name`
- model-specific templates
- `Model/feature_preset` as a normal Pipeline New Run parameter

## Dry-run Surface

`sync_clearml_templates.py --dry-run` shows the training pipeline template with
these product groups:

- `Input`
- `Split`
- `Features`
- `Run`
- `Model`
- `Output`

The Pipeline template params include:

- `Run/name`
- `Run/seed`
- `Input/local_path`
- `Input/clearml_dataset_id`
- `Input/dataset_file`
- `Input/target_column`
- `Input/feature_columns`
- `Input/id_columns`
- `Split/valid_size`
- `Features/preset`
- `Features/numeric_impute_strategy`
- `Features/categorical_impute_strategy`
- `Features/categorical_encoder`
- `Features/scaling`
- `Features/drop_columns`
- `Features/passthrough_columns`
- `Model/candidates`
- `Model/model_params_by_name`
- `Model/evaluation_metrics`
- `Model/selection_metric`
- `Model/ensemble_enabled`
- `Model/ensemble_methods`
- `Model/ensemble_method`
- `Model/ensemble_top_k`
- `Output/report_plots`

The Pipeline template params do not include:

- `Run/task`
- `Run/pipeline_mode`
- `Model/params`
- `Model/search_enabled`
- `Model/search_method`
- `Model/search_space`
- `Model/max_trials`
- `Model/feature_preset`

Feature settings are visible in the user-facing Pipeline New Run surface. Legacy
`Model/feature_preset` remains a compatibility alias only.

## Commands

```powershell
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
.\.venv\Scripts\python.exe scripts\make_sample_data.py
.\.venv\Scripts\python.exe scripts\local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest -q
git diff --check
rg -n "pipeline_mode|Model/search_|Model/max_trials|Model/feature_preset" clearml config/tasks README.md docs tests
```

## Result

- Template dry-run: pass.
- Pipeline stage overrides carry `Model/evaluation_metrics`, `Output/report_plots`,
  `Split/valid_size`, and `Features/*`.
- `Output/report_plots=false` skips ClearML plot reporting while preserving
  plot artifact upload, tables, and scalars.
- Tests: `52 passed`.
- Static search: primary Pipeline UI does not expose pipeline mode or
  optimization params. Remaining `Model/feature_preset` hits are compatibility
  mapping only.
- Remote ClearML execution: not run in this phase.
