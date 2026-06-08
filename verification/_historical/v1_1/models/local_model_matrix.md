# V1.1 Local Model Matrix

Run date: 2026-05-25 00:22:45 +09:00
Git commit: 0756d3b

## Commands

```powershell
.\.venv\Scripts\python.exe scripts\make_sample_data.py
```

For each model, the following task sequence was executed with `model.name` and `model.params` overrides:

```powershell
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_train.yaml --profile config\profiles\local.yaml --set model.name=<model> --set model.params=<params>
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_eval.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_infer.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_pipeline.yaml --profile config\profiles\local.yaml --set model.name=<model> --set model.params=<params>
```

Regression checks:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\pytest.exe -q
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config\profiles\clearml-dev.yaml --dry-run
rg -n "from clearml|import clearml|PipelineController|StorageManager" pkgs
```

## Local Results

| Model | Params | Train | Eval | Infer | Pipeline | Train RMSE | Eval RMSE | Train R2 | Predictions |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| `lasso` | `{alpha: 0.01, max_iter: 5000}` | pass | pass | pass | pass | 0.541205 | 0.522691 | 0.973803 | 50 |
| `elasticnet` | `{alpha: 0.01, l1_ratio: 0.5, max_iter: 5000, random_state: 42}` | pass | pass | pass | pass | 0.542114 | 0.523422 | 0.973715 | 50 |
| `extra_trees` | `{n_estimators: 50, random_state: 42, n_jobs: 1}` | pass | pass | pass | pass | 0.853965 | 0.381905 | 0.934777 | 50 |
| `knn` | `{n_neighbors: 5, weights: distance}` | pass | pass | pass | pass | 0.923455 | 0.412982 | 0.923730 | 50 |
| `svr` | `{kernel: rbf, C: 1.0, epsilon: 0.1, gamma: scale}` | pass | pass | pass | pass | 1.068177 | 1.050571 | 0.897952 | 50 |
| `mlp` | `{hidden_layer_sizes: [32], solver: lbfgs, max_iter: 500, random_state: 42}` | pass | pass | pass | pass | 0.902105 | 0.473188 | 0.927216 | 50 |

## Artifact Checks

For each model, the run produced the expected local artifacts:

- `outputs/latest_train/model.joblib`
- `outputs/latest_train/model_info.json`
- `outputs/latest_train/metrics.json`
- `outputs/latest_train/manifest.json`
- `outputs/latest_train/validation_predictions.csv`
- `outputs/latest_eval/metrics.json`
- `outputs/latest_eval/evaluation_predictions.csv`
- `outputs/latest_infer/predictions.csv`
- `outputs/latest_pipeline/pipeline_summary.json`

`model_info.json` recorded the selected model name and parameters for each model.

## Regression Results

- Pytest: `28 passed`.
- ClearML template dry-run: pass; templates remained `tabular_train_template`, `tabular_eval_template`, `tabular_infer_template`, and `tabular_pipeline_template`.
- ClearML boundary check: no matches under `pkgs`.

## Findings

- V1.1 local execution is ready.
- MLP can emit a sklearn convergence warning with the small smoke default, but it exits successfully and writes all expected artifacts.
- ClearML dev task and pipeline execution should be verified next after template sync and Agent image rebuild.
