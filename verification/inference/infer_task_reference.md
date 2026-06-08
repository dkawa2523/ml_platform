# Inference Task Reference Verification

Date: 2026-06-08

## Scope

`tabular_infer_template` is the inference entrypoint. Inference is separate
from the training pipeline and is not a Pipeline-tab draft.

Primary source paths:

- `source_type=task_id` with `source_task_id` and `model_selector`
- `source_type=local_path` with `local_model_path`

Future / experimental source paths:

- `artifact_url`
- `clearml_model_id`

These future paths can remain in code for explicit compatibility checks, but
they are not primary ClearML UI template parameters.

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

Expected behavior:

- local default resolves `outputs/latest_training_pipeline` when no
  `local_model_path` is provided
- `model_selector=best` resolves `evaluate_models/best_model.joblib`
- `model_selector=ensemble` resolves `build_ensemble/model.joblib`
- feature alignment uses explicit feature columns, model metadata,
  `feature_spec.json`, or `preprocess_bundle` metadata when available

Observed local result:

- run dir: `outputs\tabular_infer_20260608T033408Z`
- resolved model:
  `outputs\latest_training_pipeline\evaluate_models\best_model.joblib`
- resolved metadata:
  `outputs\latest_training_pipeline\evaluate_models\best_model.json`
- resolved feature spec:
  `outputs\latest_training_pipeline\preprocess_features\feature_spec.json`
- resolved preprocess bundle:
  `outputs\latest_training_pipeline\preprocess_features\preprocess_bundle.joblib`
- predictions:
  `outputs\tabular_infer_20260608T033408Z\predictions.csv`
- ensemble selector run dir: `outputs\tabular_infer_20260608T033517Z`
- ensemble resolved model:
  `outputs\latest_training_pipeline\build_ensemble\model.joblib`
- ensemble artifact kind: `ensemble`

Result: pass

## ClearML Dry-Run

Command:

```powershell
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
```

Expected primary UI parameters on `tabular_infer_template`:

- `Model/source_type`
- `Model/source_task_id`
- `Model/model_selector`
- `Model/local_model_path`
- `Output/prediction_name`
- `Output/chunk_size`

Expected absent primary UI parameters:

- `Model/model_artifact_url`
- `Model/clearml_model_id`
- `Model/artifact_path`
- `Model/info_path`

Result: pass

Observed:

- `tabular_infer_template` exposes only primary source fields:
  `Model/source_type`, `Model/source_task_id`, `Model/model_selector`, and
  `Model/local_model_path`
- `Model/model_artifact_url`, `Model/clearml_model_id`,
  `Model/artifact_path`, and `Model/info_path` are absent from the primary
  template UI

## Tests

Command:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest -q
```

Result: `56 passed`

## Remote Verification

Result: not run

Remote dev server execution still needs to be performed for:

- `source_type=task_id`, `model_selector=best`
- `source_type=task_id`, `model_selector=ensemble`

Do not promote this remote inference source path to supported until that
evidence is recorded.
