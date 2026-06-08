# ClearML Task Full Run: ridge train

- Model: `ridge`
- Params: `{"alpha": 1.0}`
- Template: `tabular_train_template`
- Cloned task name: `v1_ridge_train_20260524T133409Z`
- Task ID: `102084a83f8f42b9a40238f5875cf3a3`
- URL: `http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/102084a83f8f42b9a40238f5875cf3a3/output/log`
- Project: `MLPlatform/Dev`
- Queue: `default`
- Agent worker: `a8415e1b0aea:2`
- Status: completed

## Changed UI Parameters

- `Input/clearml_dataset_id`: Agent-reachable dev Dataset
- `Input/dataset_file`: `sample_train.csv`
- `Input/local_path`: empty
- `Model/name`: `ridge`
- `Model/params`: `{"alpha": 1.0}`
- `Model/feature_preset`: `basic`

## Metrics

- MAE: `0.4351933300`
- RMSE: `0.5406374335`
- R2: `0.9738583565`

## Artifacts

- `config`
- `manifest`
- `metrics`
- `model`
- `model_info`
- `validation_predictions`

## Model Artifact

`http://clearml-fileserver:8081/MLPlatform/Dev/v1_ridge_train_20260524T133409Z.102084a83f8f42b9a40238f5875cf3a3/artifacts/model/model.joblib`

## Review

Accepted for v1. Dataset resolution and artifact upload succeeded.
