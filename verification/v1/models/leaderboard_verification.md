# V1 Leaderboard Verification

## Run Metadata

- Date: 2026-05-24
- Scope: local and ClearML dev train compare mode and pipeline compare mode
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

## ClearML Dev Train Result

- Template: `tabular_train_template`
- Task ID: `6b3393de1c3749d59024da4128f4c175`
- Task URL: `http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/6b3393de1c3749d59024da4128f4c175/output/log`
- Status: completed
- Artifacts: `config`, `leaderboard`, `manifest`, `metrics`, `model`, `model_info`, `validation_predictions`
- Scalars: best model `mae`, `rmse`, `r2`
- Raw console log: not stored

## ClearML Dev Pipeline Result

- Template: `tabular_pipeline_template`
- Pipeline task ID: `f4f502a3a3e2410691f5e2ae85d0ce6f`
- Pipeline URL: `http://localhost:8080/projects/57d192f3bb8746acae1a10961ee597ae/experiments/f4f502a3a3e2410691f5e2ae85d0ce6f/output/log`
- Status: completed
- Steps:
  - `train`: completed, artifacts `config`, `leaderboard`, `manifest`, `metrics`, `model`, `model_info`, `validation_predictions`
  - `eval`: completed, artifacts `config`, `evaluation_predictions`, `manifest`, `metrics`
  - `infer`: completed, artifacts `config`, `manifest`, `predictions`
- The train step selected the best model and passed its `model` artifact to eval and infer through the existing pipeline handoff.
- Raw console logs: not stored

## Decision

The V1 leaderboard design is accepted for local and ClearML dev execution. It compares candidate models inside the existing train task, uploads naturally as a table artifact, and does not add ensemble behavior or new ClearML templates.
