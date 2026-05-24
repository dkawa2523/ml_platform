# V1 Leaderboard Verification

## Run Metadata

- Date: 2026-05-24
- Scope: local train compare mode and local pipeline compare mode
- Raw logs: not stored
- Outputs: generated under `outputs/` and not committed

## Candidates

```yaml
model:
  candidates:
    - name: linear
      params: {}
    - name: ridge
      params: {alpha: 1.0}
    - name: random_forest
      params: {n_estimators: 20, random_state: 42, n_jobs: 1}
    - name: gradient_boosting
      params: {n_estimators: 20, random_state: 42}
  selection_metric: rmse
```

## Local Train Result

- Run directory: `outputs/tabular_train_20260524T140932Z`
- `leaderboard.csv`: present
- Best model artifact: `model.joblib`
- Best model info: `model_name=linear`, `model_params={}`

| Rank | Model | RMSE | R2 | Selected |
| --- | --- | ---: | ---: | --- |
| 1 | `linear` | `0.5402973079870903` | `0.9738912606564274` | yes |
| 2 | `ridge` | `0.5406374501969393` | `0.9738583769845428` | no |
| 3 | `random_forest` | `1.1633267280515684` | `0.8789614512611483` | no |
| 4 | `gradient_boosting` | `1.4481573650913309` | `0.8124349963581267` | no |

## Local Pipeline Result

- Pipeline run directory: `outputs/tabular_pipeline_20260524T140942Z`
- Train step run directory: `outputs/tabular_pipeline_20260524T140942Z_1`
- Train step `leaderboard.csv`: present
- Eval and infer used the best model artifact from the train step.

## Decision

The V1 leaderboard design is accepted locally. It compares candidate models inside the existing train task, uploads naturally as a table artifact, and does not add ensemble behavior or new ClearML templates.
