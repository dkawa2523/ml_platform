# ClearML Task Verification: ridge infer

- Model: `ridge`
- Task type: infer
- Template: `tabular_infer_template`
- Task ID: `c4c96f962a804b86986c452b1f8385ed`
- URL: `http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/c4c96f962a804b86986c452b1f8385ed/output/log`
- Project: `MLPlatform/Dev`
- Queue: `default`
- Status: completed

## Changed UI Parameters

- `Input/clearml_dataset_id`: Docker-network dev dataset
- `Input/dataset_file`: `sample_infer.csv`
- `Model/artifact_path`: ridge train model artifact URL
- `Output/prediction_name`: `predictions.csv`

## Artifacts

- `config`
- `manifest`
- `predictions`

## Product Review

Accepted for v1 MVP. The prediction artifact is present and named clearly.
