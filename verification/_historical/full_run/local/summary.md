# Local V1 Full Model Summary

## Successful Models

| Model | Train | Eval | Infer | Pipeline | V1 official |
| --- | --- | --- | --- | --- | --- |
| `linear` | pass | pass | pass | pass | yes |
| `ridge` | pass | pass | pass | pass | yes |
| `random_forest` | pass | pass | pass | pass | yes |
| `gradient_boosting` | pass | pass | pass | pass | yes |

## Pipeline Metrics

| Model | Train RMSE | Eval RMSE | Train R2 | Eval R2 |
| --- | --- | --- | --- | --- |
| `linear` | `0.5402973079870903` | `0.5218273825248825` | `0.9738912606564274` | `0.975121016854341` |
| `ridge` | `0.5406374501969393` | `0.522628388463519` | `0.9738583769845428` | `0.9750445796690351` |
| `random_forest` | `1.1137118773680839` | `0.6283117085198283` | `0.8890656615829372` | `0.9639314069203292` |
| `gradient_boosting` | `0.9494244655990696` | `0.5455435326303649` | `0.9193803083551461` | `0.9728082148686884` |

## Review

- Local execution uses the same task configs and model overrides for all V1 models.
- `outputs/` contains generated evidence only and remains excluded from commit.
- `scikit-learn` is now part of the V1 runtime dependency set.
- A local pipeline params bug was fixed so root `model.params` replaces the default train task params instead of merging stale keys such as `alpha`.

## Decision

Local full model execution passed for all V1 official models.
