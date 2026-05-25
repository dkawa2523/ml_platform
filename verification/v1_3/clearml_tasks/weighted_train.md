# Weighted Ensemble Train

Mode: weighted ensemble train
Template: tabular_train_template
Task ID: a87b0c2bde0b44bb9a613227f7f368c7
Task URL: http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/a87b0c2bde0b44bb9a613227f7f368c7
Queue: default
Status: completed

Changed UI parameters:

- `Input/clearml_dataset_id`: dev Dataset ID
- `Input/dataset_file`: `sample_train.csv`
- `Model/candidates`: all supported V1/V1.1 model names
- `Model/params`: model-keyed params
- `Model/selection_metric`: `rmse`
- `Model/ensemble_enabled`: `true`
- `Model/ensemble_method`: `weighted`
- `Model/ensemble_top_k`: `3`

Metrics:

- mae: 0.4352474510669708
- rmse: 0.5405260324478149
- r2: 0.9738691449165344

Artifacts:

- base_model_1_linear
- base_model_2_ridge
- base_model_3_lasso
- config
- ensemble_predictions
- leaderboard
- manifest
- metrics
- model
- model_info
- validation_predictions

Result: pass. Weighted ensemble artifact is visible as the standard `model` artifact.
