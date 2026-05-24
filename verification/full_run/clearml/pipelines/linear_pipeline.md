# ClearML Pipeline Full Run: linear

- Template: `tabular_pipeline_template`
- Pipeline task ID: `dc3f88850d854ae087642532fb1e70f9`
- Pipeline URL: `http://localhost:8080/pipelines/57d192f3bb8746acae1a10961ee597ae/experiments/dc3f88850d854ae087642532fb1e70f9`
- Status: completed

## Steps

| Step | Task ID | Status |
| --- | --- | --- |
| train | `cb523a83f3b94d2e9a3b948c50c91900` | completed |
| eval | `74399b0ef4dd4c17a223cd868971f141` | completed |
| infer | `96c99aeb77914427b4bdfa3be853ac9e` | completed |

## Eval Metrics

- MAE: `0.42199715971946716`
- RMSE: `0.5218273997306824`
- R2: `0.975121021270752`

## Decision

Accepted for V1. The fixed train -> eval -> infer graph works for `linear`.
