# Lasso Train

Model: lasso
Mode: single model train
Template: tabular_train_template
Task ID: a74d0c2ebdb540feb2f557f1153a434a
Task URL: http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/a74d0c2ebdb540feb2f557f1153a434a
Queue: default
Status: completed

Changed UI parameters:

- `Input/clearml_dataset_id`: dev Dataset ID
- `Input/dataset_file`: `sample_train.csv`
- `Model/name`: `lasso`
- `Model/params`: `{"alpha": 0.01, "max_iter": 5000}`

Metrics:

- mae: 0.4360749423503876
- rmse: 0.5412046909332275
- r2: 0.9738035202026367

Artifacts:

- config
- manifest
- metrics
- model
- model_info
- validation_predictions

Result: pass. V1.1 sample model training is acceptable for V1.3 remote gate.
