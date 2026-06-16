# Model Policy Verification

Date: 2026-06-16

## Scope

Verify Phase 1 model and dependency policy for tabular scalar regression.

ClearML template default candidates:

- `linear`
- `ridge`
- `lasso`
- `elasticnet`
- `random_forest`
- `extra_trees`
- `gradient_boosting`
- `lightgbm`
- `xgboost`
- `catboost`

Dependency-free local subset:

- `linear`
- `ridge`
- `lasso`
- `elasticnet`
- `random_forest`
- `extra_trees`
- `gradient_boosting`

Out of scope:

- `knn`
- `svr`
- `mlp`
- `gaussian_process`
- `tabpfn`

## Commands

```powershell
.\.venv\Scripts\python.exe scripts\make_sample_data.py
.\.venv\Scripts\python.exe scripts\local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set "model.candidates=[linear,ridge,lasso,elasticnet,random_forest,extra_trees,gradient_boosting]"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
.\.venv\Scripts\python.exe scripts\clearml_pipeline.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
git diff --check
rg -n "from clearml|import clearml|PipelineController|StorageManager" pkgs/core pkgs/tabular
```

## Results

- sample data generation: pass
- local training pipeline: pass
- local run alias: `outputs\latest_training_pipeline`
- pytest: `89 passed`
- template sync dry-run: pass
- pipeline dry-run: pass
- `git diff --check`: pass; only line-ending warnings were printed
- ClearML import boundary: pass; `rg` returned no matches under `pkgs/core` or `pkgs/tabular`

## Observed Candidates

The local smoke run uses the dependency-free subset and reported
`candidate_count=7`:

- `linear`
- `ridge`
- `lasso`
- `elasticnet`
- `random_forest`
- `extra_trees`
- `gradient_boosting`

The ClearML pipeline dry-run produced the full supported graph:

```text
preprocess_features
  -> train_linear
  -> train_ridge
  -> train_lasso
  -> train_elasticnet
  -> train_random_forest
  -> train_extra_trees
  -> train_gradient_boosting
  -> train_lightgbm
  -> train_xgboost
  -> train_catboost
  -> build_ensemble_mean_topk
  -> build_ensemble_weighted
  -> build_ensemble_median
  -> evaluate_models
```

## Policy Checks

- KNN / SVR / MLP are not supported candidates.
- KNN / SVR / MLP are rejected as out of current product scope.
- LightGBM / XGBoost / CatBoost are supported optional-dependency models in
  the ClearML template default.
- Optional GBM packages are not in `requirements.txt` or `requirements-dev.txt`.
- Synced ClearML templates install optional GBM packages into the remote task
  venv.
- Dependency-free model flow runs without optional GBM dependencies installed.
- No model-specific ClearML templates or model-specific config files were added.

## Result

Pass for local and dry-run model policy. Remote ClearML execution remains a
separate product verification gate.
