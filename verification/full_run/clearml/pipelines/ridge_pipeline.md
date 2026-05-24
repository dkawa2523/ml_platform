# ClearML Pipeline Full Run: ridge

- Template: `tabular_pipeline_template`
- Pipeline task ID: `d2cff4a829b44c37a3ce92b8b76117d7`
- Pipeline URL: `http://localhost:8080/pipelines/57d192f3bb8746acae1a10961ee597ae/experiments/d2cff4a829b44c37a3ce92b8b76117d7`
- Status: completed

## Steps

| Step | Task ID | Status |
| --- | --- | --- |
| train | `ac0de01646ed4f149d6f0376c5d1b0dd` | completed |
| eval | `f24112cc151c4956849f60d26be57e0a` | completed |
| infer | `ac76cd068d7143d9a8b873a470a3e0b2` | completed |

## Eval Metrics

- MAE: `0.4216107428073883`
- RMSE: `0.5226283669471741`
- R2: `0.9750446081161499`

## Decision

Accepted for V1. The fixed train -> eval -> infer graph works for `ridge`.
