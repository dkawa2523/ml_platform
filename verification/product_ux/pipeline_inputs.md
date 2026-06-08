# Pipeline Input UX Verification

Date: 2026-06-08

Scope: Phase 3 ClearML Pipeline New Run parameter surface.

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
- `Model/ensemble_method`
- `Model/ensemble_top_k`
- `Output/report_plots`

Experimental parameters:

- Experimental model names in `Model/candidates`, only when optional model
  dependencies are installed.

Future / hidden from primary Pipeline UI:

- `Run/pipeline_mode`
- search / optimization params
- model-specific templates
- `Output/artifact_name`

## Dry-run Surface

`sync_clearml_templates.py --dry-run` shows the training pipeline template with
these groups only:

- `Input`
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
- `Model/candidates`
- `Model/model_params_by_name`
- `Model/evaluation_metrics`
- `Model/selection_metric`
- `Model/ensemble_enabled`
- `Model/ensemble_method`
- `Model/ensemble_top_k`
- `Model/feature_preset`
- `Output/report_plots`

The Pipeline template params do not include:

- `Run/task`
- `Run/pipeline_mode`
- `Model/params`
- `Model/search_enabled`
- `Model/search_method`
- `Model/search_space`
- `Model/max_trials`
- `Output/artifact_name`

## Commands

```powershell
python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest -q
git diff --check
rg -n "pipeline_mode|Model/search_|Model/max_trials" clearml config/tasks README.md docs tests
```

## Result

- Template dry-run: pass.
- Pipeline stage overrides carry `Model/evaluation_metrics` and
  `Output/report_plots`.
- `Output/report_plots=false` skips ClearML media reporting while preserving
  plot artifact upload.
- Tests: `58 passed`.
- Static search: primary Pipeline UI does not expose pipeline mode or
  optimization params. Remaining hits are compatibility/future code or tests.
- Remote ClearML execution: not run in this phase.
