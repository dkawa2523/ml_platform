# Weighted Ensemble Eval

Mode: weighted ensemble eval
Template: tabular_eval_template
Task ID: fe7e1375415b4e7f8f535888b79103b8
Task URL: http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/fe7e1375415b4e7f8f535888b79103b8
Queue: default
Status: completed

Changed UI parameters:

- `Input/clearml_dataset_id`: dev Dataset ID
- `Input/dataset_file`: `sample_train.csv`
- `Model/artifact_path`: weighted train `model` artifact URL

Metrics:

- mae: 0.4217471182346344
- rmse: 0.5221816897392273
- r2: 0.9750872254371643

Artifacts:

- config
- evaluation_predictions
- manifest
- metrics

Result: pass. Eval consumed the weighted ensemble `model` artifact.
