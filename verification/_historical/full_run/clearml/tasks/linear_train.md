# ClearML Task Full Run: linear train

- Model: `linear`
- Params: `{}`
- Template: `tabular_train_template`
- Cloned task name: `v1_linear_train_20260524T133238Z`
- Task ID: `f529c70234f34f58a095a0da63577829`
- URL: `http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/f529c70234f34f58a095a0da63577829/output/log`
- Project: `MLPlatform/Dev`
- Queue: `default`
- Status: completed

## Changed UI Parameters

- `Input/clearml_dataset_id`: Agent-reachable dev Dataset
- `Input/dataset_file`: `sample_train.csv`
- `Input/local_path`: empty
- `Model/name`: `linear`
- `Model/params`: `{}`
- `Model/feature_preset`: `basic`

## Metrics

- MAE: `0.4354112148`
- RMSE: `0.5402973294`
- R2: `0.9738912582`

## Artifacts

- `config`
- `manifest`
- `metrics`
- `model`
- `model_info`
- `validation_predictions`

## Model Artifact

`http://clearml-fileserver:8081/MLPlatform/Dev/v1_linear_train_20260524T133238Z.f529c70234f34f58a095a0da63577829/artifacts/model/model.joblib`

## Review

Accepted for v1. Linear model switching works through the same train template.
