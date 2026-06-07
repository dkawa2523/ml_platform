# Inference Task Reference Verification

Date: 2026-06-04

## Scope

Phase D completes `tabular_infer_template` as the inference entrypoint. Inference
is not a pipeline.

Supported source types implemented in this pass:

- `task_id`
- `artifact_url`
- `clearml_model_id`
- `local_path`

Selectors:

- `best`
- `ensemble`
- supported model names such as `linear`, `ridge`, `random_forest`, and
  `gradient_boosting`

## Local Verification

Commands:

```powershell
.\.venv\Scripts\python.exe scripts\local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest -q
```

Expected artifacts:

- `predictions`
- `manifest`
- optional `model_info`
- optional `feature_spec`
- optional `preprocess_bundle`

Result: pass

Observed local result:

- resolved model:
  `outputs/latest_training_pipeline/evaluate_models/best_model.joblib`
- resolved metadata:
  `outputs/latest_training_pipeline/evaluate_models/best_model.json`
- resolved feature spec:
  `outputs/latest_training_pipeline/preprocess_features/feature_spec.json`
- resolved preprocess bundle:
  `outputs/latest_training_pipeline/preprocess_features/preprocess_bundle.joblib`

## ClearML Dry-Run

Command:

```powershell
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
```

Expected UI parameters on `tabular_infer_template`:

- `Model/source_type`
- `Model/source_task_id`
- `Model/model_selector`
- `Model/model_artifact_url`
- `Model/clearml_model_id`
- `Model/local_model_path`
- `Model/artifact_path`

Result: pass

`tabular_infer_template` exposes the expected source parameters while remaining
a task template, not a Pipeline-tab draft.

## Remote Verification

Result: not run

Remote dev server execution still needs to be performed for:

- `source_type=task_id`, `model_selector=best`
- `source_type=task_id`, `model_selector=ensemble`

Do not promote this remote inference source path to supported until that
evidence is recorded.
