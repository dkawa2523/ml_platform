# V1.1 Local Leaderboard Verification

Run date: 2026-05-25 00:39:39 +09:00
Git commit: 0756d3b

## Scope

This verifies the V1.1 comparison mode as a product feature without adding ensemble, train_ensemble_full, a leaderboard task, or model-specific templates.

## Command Summary

```powershell
.\.venv\Scripts\python.exe scripts\make_sample_data.py
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_train.yaml --profile config\profiles\local.yaml --set "model.candidates=[linear, ridge, random_forest, gradient_boosting, lasso, elasticnet, extra_trees, knn, svr, mlp]" --set "model.params={ridge: {alpha: 1.0}, random_forest: {n_estimators: 50, random_state: 42, n_jobs: 1}, gradient_boosting: {n_estimators: 50, random_state: 42}, lasso: {alpha: 0.01, max_iter: 5000}, elasticnet: {alpha: 0.01, l1_ratio: 0.5, max_iter: 5000, random_state: 42}, extra_trees: {n_estimators: 50, random_state: 42, n_jobs: 1}, knn: {n_neighbors: 5, weights: distance}, svr: {kernel: rbf, C: 1.0, epsilon: 0.1, gamma: scale}, mlp: {hidden_layer_sizes: [32], solver: lbfgs, max_iter: 500, random_state: 42}}" --set "model.selection_metric=rmse"
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_eval.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_infer.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_pipeline.yaml --profile config\profiles\local.yaml --set "model.candidates=[linear, ridge, random_forest, gradient_boosting, lasso, elasticnet, extra_trees, knn, svr, mlp]" --set "model.params={ridge: {alpha: 1.0}, random_forest: {n_estimators: 50, random_state: 42, n_jobs: 1}, gradient_boosting: {n_estimators: 50, random_state: 42}, lasso: {alpha: 0.01, max_iter: 5000}, elasticnet: {alpha: 0.01, l1_ratio: 0.5, max_iter: 5000, random_state: 42}, extra_trees: {n_estimators: 50, random_state: 42, n_jobs: 1}, knn: {n_neighbors: 5, weights: distance}, svr: {kernel: rbf, C: 1.0, epsilon: 0.1, gamma: scale}, mlp: {hidden_layer_sizes: [32], solver: lbfgs, max_iter: 500, random_state: 42}}" --set "model.selection_metric=rmse"
```

Regression checks:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\pytest.exe -q
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config\profiles\clearml-dev.yaml --dry-run
rg -n "from clearml|import clearml|PipelineController|StorageManager" pkgs
```

## Result

| Check | Result |
| --- | --- |
| comparison train | pass |
| best model eval | pass |
| best model infer | pass |
| comparison pipeline | pass |
| `leaderboard.csv` | pass |
| best model artifact | pass |
| `model_info.json` best model fields | pass |
| `metrics.json` comparison summary | pass |
| `manifest.json` leaderboard table entry | pass |
| pytest | `28 passed` |
| template dry-run | pass, four templates only |
| pkgs ClearML boundary | pass, no matches |

## Leaderboard Summary

| Rank | Model | RMSE | MAE | R2 |
| ---: | --- | ---: | ---: | ---: |
| 1 | `linear` | 0.540297 | 0.435411 | 0.973891 |
| 2 | `ridge` | 0.540637 | 0.435193 | 0.973858 |
| 3 | `lasso` | 0.541205 | 0.436075 | 0.973803 |
| 4 | `elasticnet` | 0.542114 | 0.436264 | 0.973715 |
| 5 | `extra_trees` | 0.853965 | 0.709748 | 0.934777 |

The full `leaderboard.csv` contained 10 rows for:

- `linear`
- `ridge`
- `random_forest`
- `gradient_boosting`
- `lasso`
- `elasticnet`
- `extra_trees`
- `knn`
- `svr`
- `mlp`

## Artifacts

The comparison train produced:

- `model.joblib`
- `model_info.json`
- `metrics.json`
- `manifest.json`
- `validation_predictions.csv`
- `leaderboard.csv`

`model_info.json` contains:

- `model_name`
- `model_params`
- `best_model_name`
- `best_model_params`

`metrics.json` contains numeric best-model metrics and:

```json
{
  "comparison": {
    "enabled": true,
    "selection_metric": "rmse",
    "best_model_name": "linear",
    "candidate_count": 10
  }
}
```

## Notes

An initial single train and pipeline check was accidentally launched in parallel, which caused a Windows file lock while both processes updated `outputs/latest_train`. The sequential rerun passed. This is not a product logic failure; local latest directories are not intended as a concurrent execution target.

## Decision

Local leaderboard behavior is ready for V1.1. It remains a best-single-model selector and comparison artifact, not an ensemble.
