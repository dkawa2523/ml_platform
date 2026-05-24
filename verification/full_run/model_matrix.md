# V1 Model Matrix

## Run Metadata

- Date: 2026-05-24
- Verified commit: `0d4b2eb`
- Environment: local `.venv` and ClearML dev Agent
- `scikit-learn`: required V1 runtime dependency

## Matrix

| Model | Local | ClearML task | ClearML pipeline | Required dependency | Params | V1 status |
| --- | --- | --- | --- | --- | --- | --- |
| `linear` | pass | pass | pass | `numpy` | `{}` | official supported |
| `ridge` | pass | pass | pass | `numpy` | `{"alpha": 1.0}` | official supported |
| `random_forest` | pass | pass | pass | `scikit-learn` | `{"n_estimators": 50, "random_state": 42, "n_jobs": 1}` | official supported |
| `gradient_boosting` | pass | pass | pass | `scikit-learn` | `{"n_estimators": 50, "random_state": 42}` | official supported |

## Decision

V1 official support is limited to these four verified models.
Model switching remains `Model/name` plus `Model/params`; `Model/candidates` and all-model training are future scope.
