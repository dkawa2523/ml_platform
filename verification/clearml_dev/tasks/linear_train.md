# ClearML Task Verification: linear train

- Model: `linear`
- Task type: train
- Template: `tabular_train_template`
- Task ID: `de2549c0d3d343f1871b8dcb2b0dafc2`
- URL: `http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/de2549c0d3d343f1871b8dcb2b0dafc2/output/log`
- Project: `MLPlatform/Dev`
- Queue: `default`
- Status: completed

## Changed UI Parameters

- `Input/clearml_dataset_id`: Docker-network dev dataset
- `Input/dataset_file`: `sample_train.csv`
- `Model/name`: `linear`
- `Model/params`: `{}`

## Metrics

- MAE: `0.4354112291`
- RMSE: `0.5402973080`
- R2: `0.9738912607`

## Artifacts

- `config`
- `manifest`
- `metrics`
- `model`
- `model_info`
- `validation_predictions`

## Product Review

Accepted for v1 MVP. Linear works through the same train template without adding model-specific templates.
