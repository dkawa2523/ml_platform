# ClearML Task Full Run: ridge eval

- Model: `ridge`
- Template: `tabular_eval_template`
- Cloned task name: `v1_ridge_eval_20260524T133439Z`
- Task ID: `449e03d117b3452b89b6213dbd967d37`
- URL: `http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/449e03d117b3452b89b6213dbd967d37/output/log`
- Project: `MLPlatform/Dev`
- Queue: `default`
- Status: completed

## Changed UI Parameters

- `Input/clearml_dataset_id`: Agent-reachable dev Dataset
- `Input/dataset_file`: `sample_train.csv`
- `Input/local_path`: empty
- `Model/artifact_path`: ridge train model artifact URL

## Metrics

- MAE: `0.4216107428`
- RMSE: `0.5226283669`
- R2: `0.9750446081`

## Artifacts

- `config`
- `evaluation_predictions`
- `manifest`
- `metrics`

## Review

Accepted for v1. The train model artifact URL was resolved by the Agent and evaluated successfully.
