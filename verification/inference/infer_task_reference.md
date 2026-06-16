# Inference Task Reference Verification

Date: 2026-06-16

## Scope

`tabular_infer_template` is the inference entrypoint. Inference is separate
from the training pipeline and is not a Pipeline-tab draft.

Primary source paths:

- `source_type=task_id` with `source_task_id` and `model_selector`
- `source_type=local_path` with `local_model_path`

Selectors:

- `best`
- `ensemble`
- `ensemble:<method>` such as `ensemble:median`
- supported model names such as `linear`, `ridge`, `lasso`, `elasticnet`,
  `random_forest`, `extra_trees`, `gradient_boosting`, `lightgbm`, `xgboost`,
  and `catboost`

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
- `model_selector=ensemble` resolves the best ensemble artifact
- `model_selector=ensemble:<method>` resolves the named ensemble method artifact
- feature alignment uses explicit feature columns, model metadata,
  `feature_spec.json`, or `preprocess_bundle` metadata when available

Observed local result:

- run alias: `outputs\latest_infer`
- resolved model:
  `outputs\latest_training_pipeline\evaluate_models\best_model.joblib`
- resolved metadata:
  `outputs\latest_training_pipeline\evaluate_models\best_model.json`
- resolved feature spec:
  `outputs\latest_training_pipeline\preprocess_features\feature_spec.json`
- resolved preprocess bundle:
  `outputs\latest_training_pipeline\preprocess_features\preprocess_bundle.joblib`
- predictions:
  `outputs\latest_infer\predictions.csv`
- current local contract writes `schema_check_summary.json` and
  `schema_check_summary.csv`; `predictions.csv` is slim and contains
  `row_index`, available ID columns, `prediction`, and lightweight model
  metadata instead of all input features
- pytest coverage confirms `model_selector=ensemble` and
  `model_selector=ensemble:<method>` resolve ensemble artifacts with artifact
  kind `ensemble`.

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

Result: pass

Observed:

- `tabular_infer_template` exposes only primary source fields:
  `Model/source_type`, `Model/source_task_id`, `Model/model_selector`, and
  `Model/local_model_path`
- under ClearML profiles, `Model/source_type` defaults to `task_id` so New Run
  starts on the recommended `source_task_id + model_selector` path; the local
  YAML default remains `local_path`

## Tests

Command:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest -q
```

Result: `89 passed`

## Remote Verification

Result: not run

Remote dev server execution still needs to be performed for:

- `source_type=task_id`, `model_selector=best`
- `source_type=task_id`, `model_selector=ensemble`

Remote execution evidence remains the release gate for ClearML server behavior;
the template contract and local behavior are covered by dry-run and tests.
