# V2.1 Local Optimization Verification

Date: 2026-05-26 JST

## Commands

```powershell
.\.venv\Scripts\python.exe scripts/make_sample_data.py
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_train.yaml --profile config/profiles/local.yaml
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_eval.yaml --profile config/profiles/local.yaml
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml

$space='{alpha: [0.1, 1.0, 10.0]}'
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_train.yaml --profile config/profiles/local.yaml --set "model.params={}" --set "model.search.enabled=true" --set "model.search.method=grid" --set "model.search.max_trials=3" --set "model.search.search_space=$space"
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_eval.yaml --profile config/profiles/local.yaml
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml

$space='{alpha: [0.1, 1.0, 10.0, 100.0]}'
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_train.yaml --profile config/profiles/local.yaml --set "model.params={}" --set "model.search.enabled=true" --set "model.search.method=random" --set "model.search.max_trials=2" --set "model.search.search_space=$space"

$space='{alpha: [0.1, 1.0]}'
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set "model.params={}" --set "model.search.enabled=true" --set "model.search.method=grid" --set "model.search.max_trials=2" --set "model.search.search_space=$space"

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\pytest.exe -q
```

## Results

| Check | Status | Notes |
| --- | --- | --- |
| Existing train/eval/infer/pipeline smoke | pass | Sequential local runs completed. |
| Single-model grid search train | pass | `optimization_trials.csv`, `optimization_summary.json`, `best_params.json`, retrained best `model.joblib`, and `model_info.json` were produced. |
| Grid best model eval/infer | pass | Eval and infer consumed `outputs/latest_train/model.joblib` from the grid search run. |
| Single-model random search train | pass | `max_trials=2` limited the random sample and produced the same standard HPO artifacts. |
| Search pipeline | pass | Train produced `train_optimization_trials`, `train_optimization_summary`, and `train_best_params`; eval/infer consumed the best train model. |
| Pytest | pass | 41 passed. |
| pkgs ClearML boundary | pass | No ClearML imports found in `pkgs`. |

## Artifact Expectations

Train search outputs:

- `model.joblib`
- `model_info.json`
- `metrics.json`
- `optimization_trials.csv`
- `optimization_summary.json`
- `best_params.json`
- `manifest.json`

Pipeline search outputs:

- `train_optimization_trials`
- `train_optimization_summary`
- `train_best_params`
- `eval_evaluation_predictions`
- `infer_predictions`
- standard train `model` handoff to eval/infer

## Notes

V2.1 search is train-time HPO only. It does not create per-trial model artifacts, ClearML child tasks, Optuna runs, or a new optimize template.

V2.1 local optimization status: ready.
