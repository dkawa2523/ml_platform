# Comparison Train

Mode: model comparison
Template: tabular_train_template
Task ID: 835ea98a27fb4c238290fca084c6ed17
Task URL: http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/835ea98a27fb4c238290fca084c6ed17
Queue: default
Status: completed

Candidates:

- linear
- ridge
- random_forest
- gradient_boosting
- lasso
- elasticnet
- extra_trees
- knn
- svr
- mlp

Changed UI parameters:

- `Input/clearml_dataset_id`: dev Dataset ID
- `Input/dataset_file`: `sample_train.csv`
- `Model/candidates`: all supported V1/V1.1 model names
- `Model/params`: model-keyed params
- `Model/selection_metric`: `rmse`
- `Model/ensemble_enabled`: `false`

Best model metrics:

- mae: 0.4354112148284912
- rmse: 0.5402973294258118
- r2: 0.9738912582397461

Artifacts:

- config
- leaderboard
- manifest
- metrics
- model
- model_info
- validation_predictions

Result: pass. `leaderboard` and best `model` artifacts are visible in ClearML.
