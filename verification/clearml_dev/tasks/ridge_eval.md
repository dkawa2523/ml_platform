# ClearML Task Verification: ridge eval

- Model: `ridge`
- Task type: eval
- Template: `tabular_eval_template`
- Task ID: `1a29f200df3245a092b4382b1324cb9a`
- URL: `http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/1a29f200df3245a092b4382b1324cb9a/output/log`
- Project: `MLPlatform/Dev`
- Queue: `default`
- Status: completed

## Changed UI Parameters

- `Input/clearml_dataset_id`: Docker-network dev dataset
- `Input/dataset_file`: `sample_train.csv`
- `Model/artifact_path`: ridge train model artifact URL

## Metrics

- MAE: `0.4216107571`
- RMSE: `0.5226283885`
- R2: `0.9750445797`

## Artifacts

- `config`
- `evaluation_predictions`
- `manifest`
- `metrics`

## Product Review

Accepted for v1 MVP. The model artifact produced by train can be evaluated through the ClearML task UI.
