# ClearML Pipeline Full Run: random_forest

- Template: `tabular_pipeline_template`
- Pipeline task ID: `cb4795e92d044b7ea51b9a0c8ce031b0`
- Pipeline URL: `http://localhost:8080/pipelines/57d192f3bb8746acae1a10961ee597ae/experiments/cb4795e92d044b7ea51b9a0c8ce031b0`
- Status: completed

## Steps

| Step | Task ID | Status |
| --- | --- | --- |
| train | `c5fd47a647ba41f3bd2c900dc58b6e36` | completed |
| eval | `aec772f626b1490d974394647121182b` | completed |
| infer | `ff3693ce1062404e9f1ed8f3c34d1d6c` | completed |

## Eval Metrics

- MAE: `0.4248252511024475`
- RMSE: `0.6283116936683655`
- R2: `0.9639313817024231`

## Decision

Accepted for V1. The fixed train -> eval -> infer graph works for `random_forest`.
