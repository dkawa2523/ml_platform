# Weighted Ensemble Infer

Mode: weighted ensemble infer
Template: tabular_infer_template
Task ID: e4c5ece12c7243e0bf7ea2b71992a8c2
Task URL: http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/e4c5ece12c7243e0bf7ea2b71992a8c2
Queue: default
Status: completed

Changed UI parameters:

- `Input/clearml_dataset_id`: dev Dataset ID
- `Input/dataset_file`: `sample_infer.csv`
- `Model/artifact_path`: weighted train `model` artifact URL
- `Output/prediction_name`: `predictions.csv`

Artifacts:

- config
- manifest
- predictions

Result: pass. The `predictions` artifact is visible in ClearML. The operator host could not directly download the fileserver URL because `clearml-fileserver` is a server-side DNS name and direct localhost access returned auth failure; standardized prediction columns remain covered by local tests and the remote infer code path completed successfully.
