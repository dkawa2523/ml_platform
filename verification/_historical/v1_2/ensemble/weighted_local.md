# V1.2 Weighted Ensemble Local Verification

Run date: 2026-05-25 08:06:21 +09:00  
Git commit: 0756d3b

## Scope

This verifies the V1.2 `weighted` ensemble locally. The method uses the existing
comparison leaderboard, selects the top-k models, derives deterministic weights
from `model.selection_metric`, and saves one standard `model.joblib` artifact.
It does not perform weight optimization, stacking, or train_ensemble_full.

## Commands

Baseline single-model path:

```powershell
.\.venv\Scripts\python.exe scripts\make_sample_data.py
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_train.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_eval.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_infer.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_pipeline.yaml --profile config\profiles\local.yaml
```

Comparison and ensemble:

```powershell
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_train.yaml --profile config\profiles\local.yaml --set "model.candidates=[linear, ridge, random_forest, gradient_boosting, lasso, elasticnet, extra_trees, knn, svr, mlp]" --set "model.params={ridge: {alpha: 1.0}, random_forest: {n_estimators: 50, random_state: 42, n_jobs: 1}, gradient_boosting: {n_estimators: 50, random_state: 42}, lasso: {alpha: 0.01, max_iter: 5000}, elasticnet: {alpha: 0.01, l1_ratio: 0.5, max_iter: 5000, random_state: 42}, extra_trees: {n_estimators: 50, random_state: 42, n_jobs: 1}, knn: {n_neighbors: 5, weights: distance}, svr: {kernel: rbf, C: 1.0, epsilon: 0.1, gamma: scale}, mlp: {hidden_layer_sizes: [32], solver: lbfgs, max_iter: 500, random_state: 42}}" --set "model.selection_metric=rmse"
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_train.yaml --profile config\profiles\local.yaml --set "model.candidates=[linear, ridge, random_forest, gradient_boosting, lasso, elasticnet, extra_trees, knn, svr, mlp]" --set "model.params={ridge: {alpha: 1.0}, random_forest: {n_estimators: 50, random_state: 42, n_jobs: 1}, gradient_boosting: {n_estimators: 50, random_state: 42}, lasso: {alpha: 0.01, max_iter: 5000}, elasticnet: {alpha: 0.01, l1_ratio: 0.5, max_iter: 5000, random_state: 42}, extra_trees: {n_estimators: 50, random_state: 42, n_jobs: 1}, knn: {n_neighbors: 5, weights: distance}, svr: {kernel: rbf, C: 1.0, epsilon: 0.1, gamma: scale}, mlp: {hidden_layer_sizes: [32], solver: lbfgs, max_iter: 500, random_state: 42}}" --set "model.selection_metric=rmse" --set "model.ensemble={enabled: true, method: mean_topk, top_k: 3}"
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_train.yaml --profile config\profiles\local.yaml --set "model.candidates=[linear, ridge, random_forest, gradient_boosting, lasso, elasticnet, extra_trees, knn, svr, mlp]" --set "model.params={ridge: {alpha: 1.0}, random_forest: {n_estimators: 50, random_state: 42, n_jobs: 1}, gradient_boosting: {n_estimators: 50, random_state: 42}, lasso: {alpha: 0.01, max_iter: 5000}, elasticnet: {alpha: 0.01, l1_ratio: 0.5, max_iter: 5000, random_state: 42}, extra_trees: {n_estimators: 50, random_state: 42, n_jobs: 1}, knn: {n_neighbors: 5, weights: distance}, svr: {kernel: rbf, C: 1.0, epsilon: 0.1, gamma: scale}, mlp: {hidden_layer_sizes: [32], solver: lbfgs, max_iter: 500, random_state: 42}}" --set "model.selection_metric=rmse" --set "model.ensemble={enabled: true, method: weighted, top_k: 3}"
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_eval.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_infer.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_pipeline.yaml --profile config\profiles\local.yaml --set "model.candidates=[linear, ridge, random_forest, gradient_boosting, lasso, elasticnet, extra_trees, knn, svr, mlp]" --set "model.params={ridge: {alpha: 1.0}, random_forest: {n_estimators: 50, random_state: 42, n_jobs: 1}, gradient_boosting: {n_estimators: 50, random_state: 42}, lasso: {alpha: 0.01, max_iter: 5000}, elasticnet: {alpha: 0.01, l1_ratio: 0.5, max_iter: 5000, random_state: 42}, extra_trees: {n_estimators: 50, random_state: 42, n_jobs: 1}, knn: {n_neighbors: 5, weights: distance}, svr: {kernel: rbf, C: 1.0, epsilon: 0.1, gamma: scale}, mlp: {hidden_layer_sizes: [32], solver: lbfgs, max_iter: 500, random_state: 42}}" --set "model.selection_metric=rmse" --set "model.ensemble={enabled: true, method: weighted, top_k: 3}"
```

Regression:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\pytest.exe -q
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config\profiles\clearml-dev.yaml --dry-run
rg -n "from clearml|import clearml|PipelineController|StorageManager" pkgs
```

## Results

| Check | Result |
| --- | --- |
| single model train/eval/infer/pipeline | pass |
| comparison train without ensemble | pass |
| mean_topk train | pass |
| weighted train | pass |
| weighted eval | pass |
| weighted infer | pass |
| weighted pipeline | pass |
| pytest | `31 passed` |
| template dry-run | pass, four templates only |
| pkgs ClearML boundary | pass, no matches |

The `mlp` candidate emitted an sklearn convergence warning with the intentionally
small verification default. The run still completed successfully.

## Weighted Artifact

`model_info.json` confirms:

- `artifact_kind`: `ensemble`
- `model_name`: `weighted`
- `ensemble_method`: `weighted`
- `top_k`: `3`
- `selection_metric`: `rmse`
- selected base models: `linear`, `ridge`, `lasso`
- weights: `0.333590`, `0.333380`, `0.333030`

Saved base model artifacts:

- `base_models/01_linear.joblib`
- `base_models/02_ridge.joblib`
- `base_models/03_lasso.joblib`

## Metrics

| Metric | Value |
| --- | ---: |
| `mae` | 0.435247 |
| `rmse` | 0.540526 |
| `r2` | 0.973869 |

Eval using the weighted artifact:

| Metric | Value |
| --- | ---: |
| `mae` | 0.421747 |
| `rmse` | 0.522182 |
| `r2` | 0.975087 |

## Leaderboard

Top rows:

| Rank | Model | RMSE | MAE | R2 |
| ---: | --- | ---: | ---: | ---: |
| 1 | `linear` | 0.540297 | 0.435411 | 0.973891 |
| 2 | `weighted` | 0.540526 | 0.435247 | 0.973869 |
| 3 | `ridge` | 0.540637 | 0.435193 | 0.973858 |
| 4 | `lasso` | 0.541205 | 0.436075 | 0.973803 |
| 5 | `elasticnet` | 0.542114 | 0.436264 | 0.973715 |
| 6 | `extra_trees` | 0.853965 | 0.709748 | 0.934777 |

`weighted` is included in `leaderboard.csv` with artifact name `model`.

## Decision

Local V1.2 `weighted` ensemble is ready. Real ClearML dev task and pipeline
execution remain the next operational verification gate.
