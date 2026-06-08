# ClearML Task Full Run: linear infer

- Model: `linear`
- Template: `tabular_infer_template`
- Cloned task name: `v1_linear_infer_20260524T133339Z`
- Task ID: `6ee2e3d23c8d432bb157737e64423288`
- URL: `http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/6ee2e3d23c8d432bb157737e64423288/output/log`
- Project: `MLPlatform/Dev`
- Queue: `default`
- Status: completed

## Changed UI Parameters

- `Input/clearml_dataset_id`: Agent-reachable dev Dataset
- `Input/dataset_file`: `sample_infer.csv`
- `Input/local_path`: empty
- `Model/artifact_path`: linear train model artifact URL
- `Output/prediction_name`: `predictions.csv`

## Artifacts

- `config`
- `manifest`
- `predictions`

## Review

Accepted for v1. Infer works for linear by changing only the model artifact URL.
