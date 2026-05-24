# V1 Local Model Verification

## Run Metadata

- Date: 2026-05-24
- Scope: local train/eval/infer/pipeline for V1 official supported models
- Profile: `config/profiles/local.yaml`
- Task configs:
  - `config/tasks/tabular_train.yaml`
  - `config/tasks/tabular_eval.yaml`
  - `config/tasks/tabular_infer.yaml`
  - `config/tasks/tabular_pipeline.yaml`
- Raw logs: not stored
- Outputs: generated under `outputs/` and not committed

## Implementation Checks

| Check | Result |
| --- | --- |
| `linear`, `ridge`, `random_forest`, `gradient_boosting` can be built by `models.py` | pass |
| Model selection uses `model.name` / `model.params` | pass |
| Params are passed as dictionaries to model construction | pass |
| Feature pipeline combines with every model during train | pass |
| `model_info.json` stores `model_name` and `model_params` | pass |
| `model_info.json` stores `feature_columns` and `target_column` | pass |
| eval restores feature columns from model info when not explicitly set | pass |
| infer restores feature columns from model info when not explicitly set | pass |
| ClearML templates are unchanged | pass |

## Model Defaults And Params

| Model | Default behavior | Verification params |
| --- | --- | --- |
| `linear` | internal numpy linear regressor, no params | `{}` |
| `ridge` | internal numpy ridge regressor, default `alpha=1.0` | `{"alpha": 1.0}` |
| `random_forest` | sklearn `RandomForestRegressor`; `n_jobs=1` is set if omitted | `{"n_estimators": 50, "random_state": 42, "n_jobs": 1}` |
| `gradient_boosting` | sklearn `GradientBoostingRegressor` defaults unless specified | `{"n_estimators": 50, "random_state": 42}` |

## Local Execution Matrix

| Model | Train | Eval | Infer | Pipeline | Eval RMSE | Eval R2 |
| --- | --- | --- | --- | --- | ---: | ---: |
| `linear` | pass | pass | pass | pass | `0.5218273825248825` | `0.975121016854341` |
| `ridge` | pass | pass | pass | pass | `0.522628388463519` | `0.9750445796690351` |
| `random_forest` | pass | pass | pass | pass | `0.6283117085198283` | `0.9639314069203292` |
| `gradient_boosting` | pass | pass | pass | pass | `0.5455435326303649` | `0.9728082148686884` |

## Run Directories

| Model | Train run | Eval run | Infer run | Pipeline run |
| --- | --- | --- | --- | --- |
| `linear` | `outputs/tabular_train_20260524T135753Z` | `outputs/tabular_eval_20260524T135754Z` | `outputs/tabular_infer_20260524T135754Z` | `outputs/tabular_pipeline_20260524T135754Z` |
| `ridge` | `outputs/tabular_train_20260524T135755Z` | `outputs/tabular_eval_20260524T135755Z` | `outputs/tabular_infer_20260524T135756Z` | `outputs/tabular_pipeline_20260524T135756Z` |
| `random_forest` | `outputs/tabular_train_20260524T135756Z` | `outputs/tabular_eval_20260524T135757Z` | `outputs/tabular_infer_20260524T135759Z` | `outputs/tabular_pipeline_20260524T135800Z` |
| `gradient_boosting` | `outputs/tabular_train_20260524T135801Z` | `outputs/tabular_eval_20260524T135802Z` | `outputs/tabular_infer_20260524T135803Z` | `outputs/tabular_pipeline_20260524T135804Z` |

## Artifacts Checked

- Train:
  - `model.joblib`
  - `model_info.json`
  - `metrics.json`
  - `manifest.json`
  - `validation_predictions.csv`
- Eval:
  - `metrics.json`
  - `manifest.json`
  - `evaluation_predictions.csv`
- Infer:
  - `predictions.csv`
  - `manifest.json`
- Pipeline:
  - fixed `train -> eval -> infer`
  - train model artifact passed to eval/infer
  - `pipeline_summary.json`
  - `metrics.json`
  - `manifest.json`

## Issues

No failing V1 model was found in local execution.

## Future Scope

The following remain outside V1:

- `Model/candidates`
- all-model training
- runtime leaderboard task
- ensemble, stacking, and weighted ensemble
- LightGBM, XGBoost, CatBoost, and TabPFN

## Decision

All four V1 official supported models are locally executable through the same train/eval/infer/pipeline path.
