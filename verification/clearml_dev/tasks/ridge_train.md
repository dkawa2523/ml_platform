# ClearML Task Verification: ridge train

- Model: `ridge`
- Task type: train
- Template: `tabular_train_template`
- Cloned task name: `ridge_train_clearml_dev_success_candidate`
- Task ID: `4fe2add8d23a472fba4523eb8ae22c5b`
- URL: `http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/4fe2add8d23a472fba4523eb8ae22c5b/output/log`
- Project: `MLPlatform/Dev`
- Queue: `default`
- Status: completed

## Changed UI Parameters

- `Input/clearml_dataset_id`: Docker-network dev dataset
- `Input/dataset_file`: `sample_train.csv`
- `Model/name`: `ridge`
- `Model/params`: `{"alpha": 1.0}`

## Metrics

- MAE: `0.4351933423`
- RMSE: `0.5406374502`
- R2: `0.9738583770`

## Artifacts

- `config`
- `manifest`
- `metrics`
- `model`
- `model_info`
- `validation_predictions`

## Product Review

Accepted for v1 MVP. Metrics and model artifacts are visible, and the task uses only the four intended UI parameter groups.
