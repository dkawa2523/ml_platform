# ClearML Task Verification: linear infer

- Model: `linear`
- Task type: infer
- Template: `tabular_infer_template`
- Task ID: `127d36461dfa41ab81a29b0624f7809b`
- URL: `http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/127d36461dfa41ab81a29b0624f7809b/output/log`
- Project: `MLPlatform/Dev`
- Queue: `default`
- Status: completed

## Changed UI Parameters

- `Input/clearml_dataset_id`: Docker-network dev dataset
- `Input/dataset_file`: `sample_infer.csv`
- `Model/artifact_path`: linear train model artifact URL
- `Output/prediction_name`: `predictions.csv`

## Artifacts

- `config`
- `manifest`
- `predictions`

## Product Review

Accepted for v1 MVP. The same infer template works for linear by changing the model artifact URL only.
