# ClearML Task Verification: linear eval

- Model: `linear`
- Task type: eval
- Template: `tabular_eval_template`
- Task ID: `c4910436f6124f58bd2a8573b012ca22`
- URL: `http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/c4910436f6124f58bd2a8573b012ca22/output/log`
- Project: `MLPlatform/Dev`
- Queue: `default`
- Status: completed

## Changed UI Parameters

- `Input/clearml_dataset_id`: Docker-network dev dataset
- `Input/dataset_file`: `sample_train.csv`
- `Model/artifact_path`: linear train model artifact URL

## Metrics

- MAE: `0.4219971587`
- RMSE: `0.5218273825`
- R2: `0.9751210169`

## Artifacts

- `config`
- `evaluation_predictions`
- `manifest`
- `metrics`

## Product Review

Accepted for v1 MVP. Eval works with the model URL produced by linear train.
