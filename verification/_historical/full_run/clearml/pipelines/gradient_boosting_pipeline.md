# ClearML Pipeline Full Run: gradient_boosting

- Template: `tabular_pipeline_template`
- Pipeline task ID: `d4c80526d83543b8bc17425c2a43e341`
- Pipeline URL: `http://localhost:8080/pipelines/57d192f3bb8746acae1a10961ee597ae/experiments/d4c80526d83543b8bc17425c2a43e341`
- Status: completed

## Steps

| Step | Task ID | Status |
| --- | --- | --- |
| train | `70baf5dd540a4beeaf3881e12839282a` | completed |
| eval | `83a31917af9d4a3ca6a864544ab83995` | completed |
| infer | `f5c3ca48fe114bca95dc2b252a9769e9` | completed |

## Eval Metrics

- MAE: `0.4104173481464386`
- RMSE: `0.5455435514450073`
- R2: `0.9728082418441772`

## Decision

Accepted for V1. The fixed train -> eval -> infer graph works for `gradient_boosting`.
