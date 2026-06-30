# Pipeline Input UX Verification

Date: 2026-06-16

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

- `Basic/model_suite`
- `Basic/quality_mode`
- `Basic/use_ensemble`
- `Basic/notes`
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
- `Model/ensemble_top_k`
- `Output/upload_plots`
- `Split/method`
- `Split/valid_size`
- `Split/group_column`
- `Split/time_column`
- `Split/valid_filter_column`
- `Split/valid_filter_value`
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
- `Model/ensemble_method` as a normal Pipeline New Run parameter

Compatibility / internal only:

- `Model/ensemble_method` remains accepted by the mapping layer and is used in
  per-stage overrides, but the user-facing Pipeline New Run surface uses
  `Model/ensemble_methods`.
- `Model/ensemble_enabled` remains visible as a detailed override. It is blank
  by default; explicit `true` or `false` takes precedence over
  `Basic/use_ensemble`.

## Dry-run Surface

`sync_clearml_templates.py --dry-run` shows the training pipeline template with
these product groups:

- `Basic`
- `Input`
- `Split`
- `Features`
- `Run`
- `Model`
- `Output`

The Pipeline template params include:

- `Basic/model_suite`
- `Basic/quality_mode`
- `Basic/use_ensemble`
- `Basic/notes`
- `Run/name`
- `Run/seed`
- `Input/local_path`
- `Input/clearml_dataset_id`
- `Input/dataset_file`
- `Input/target_column`
- `Input/feature_columns`
- `Input/id_columns`
- `Split/method`
- `Split/valid_size`
- `Split/group_column`
- `Split/time_column`
- `Split/valid_filter_column`
- `Split/valid_filter_value`
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
- `Model/ensemble_top_k`
- `Output/upload_plots`

The Pipeline template params do not include:

- `Run/task`
- `Run/pipeline_mode`
- `Model/params`
- `Model/ensemble_method`
- `Model/search_enabled`
- `Model/search_method`
- `Model/search_space`
- `Model/max_trials`

Feature settings are visible through `Features/*` in the user-facing Pipeline
New Run surface.

## Commands

```powershell
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
.\.venv\Scripts\python.exe scripts\make_sample_data.py
.\.venv\Scripts\python.exe scripts\local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest -q
git diff --check
rg -n "pipeline_mode|Model/search_|Model/max_trials|Model/ensemble_method" clearml config/tasks README.md docs tests
```

## Result

- Template dry-run: pass.
- Pipeline stage overrides carry `Model/evaluation_metrics`, `Output/upload_plots`,
  `Split/valid_size`, and `Features/*`.
- `Basic/model_suite` changes generated `train_<model>` steps while preserving
  direct `Model/candidates` control for `custom` and default detailed use.
- `Basic/use_ensemble=false` removes ensemble steps unless
  `Model/ensemble_enabled` is explicitly set.
- `Output/upload_plots=false` skips ClearML plot media upload while preserving
  plot artifact upload, tables, and scalars.
- Tests: `89 passed`.
- Static search: primary Pipeline UI does not expose pipeline mode or
  optimization params. Remaining `Model/ensemble_method` hits are internal
  stage mapping only.
- Remote ClearML execution: not run in this phase.
