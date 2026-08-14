# Inference Task Reference Verification

Date: 2026-08-14

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
- `schema_check_summary`
- `manifest`
- `model_info`

Expected behavior:

- local default resolves `outputs/latest_training_pipeline` when no
  `local_model_path` is provided
- `model_selector=best` resolves `evaluate_models/best_model.joblib`
- `model_selector=ensemble` resolves the best ensemble artifact
- `model_selector=ensemble:<method>` resolves the named ensemble method artifact
- feature alignment uses `model_info.json` and the serialized estimator

Observed local result:

- run alias: `outputs\latest_infer`
- resolved model:
  `outputs\latest_training_pipeline\evaluate_models\best_model.joblib`
- resolved metadata:
  `outputs\latest_training_pipeline\evaluate_models\model_info.json`
- predictions:
  `outputs\latest_infer\predictions.csv`
- current local contract writes `schema_check_summary.json` and
  `schema_check_summary.csv`; `predictions.csv` contains only `row_index`,
  available ID columns, and `prediction`
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

Result: see the current repository test run; historical counts are not a release gate.

## Remote Verification

Result: pass for `source_type=task_id`, `model_selector=best`

- synced inference template: `ecd6aebae5b746ce88b4f63f770a16c7`
- completed inference task: `448867d1353d4582b7d422a0e6cd13fd`
- clean-image verification task: `bef08e98a3b54ecdac10f44f67917244`
- source evaluate task: `aa8c9d0bc3c1448ebd3419ab9810a6bd`
- resolved model: `linear`; schema status: `ok`
- required/provided features: 3/3; missing and extra columns: none
- predictions: 200 rows, zero null values
- template and both runs used commit
  `e06b0fdd83ab1a8e691014acf551919bb574002f`, `python3.11`, and
  `ml-platform-clearml-agent:dev`
- clean Agent execution reported zero Git editable requirements

`model_selector=ensemble` remains a separate scenario because this P1/P2
verification intentionally disabled ensemble construction.
