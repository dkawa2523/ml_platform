# Weighted Ensemble Pipeline

Mode: weighted ensemble pipeline
Template: tabular_pipeline_template
Pipeline task ID: 64737b25d06047d4addad76f1105376a
Pipeline URL: http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/64737b25d06047d4addad76f1105376a
Queue: default
Overall status: completed

Changed UI parameters:

- `Input/clearml_dataset_id`: dev Dataset ID
- `Input/train_dataset_file`: `sample_train.csv`
- `Input/eval_dataset_file`: `sample_train.csv`
- `Input/infer_dataset_file`: `sample_infer.csv`
- `Model/candidates`: all supported V1/V1.1 model names
- `Model/params`: model-keyed params
- `Model/selection_metric`: `rmse`
- `Model/ensemble_enabled`: `true`
- `Model/ensemble_method`: `weighted`
- `Model/ensemble_top_k`: `3`

## Steps

| Step | Task ID | Status | Artifacts |
| --- | --- | --- | --- |
| train | d4d20e6958e34c928a255f5f3b5565ec | completed | leaderboard, ensemble_predictions, base_model_*, model, model_info, metrics, validation_predictions |
| eval | e75119f3e1db4d9f9147d84b839e27e2 | completed | metrics, evaluation_predictions |
| infer | ced1795b0428487998a8e1b7e98a4193 | completed | predictions |

Step URLs:

- train: http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/d4d20e6958e34c928a255f5f3b5565ec
- eval: http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/e75119f3e1db4d9f9147d84b839e27e2
- infer: http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/ced1795b0428487998a8e1b7e98a4193

Metrics:

- train mae: 0.4352474510669708
- train rmse: 0.5405260324478149
- train r2: 0.9738691449165344
- eval mae: 0.4217471182346344
- eval rmse: 0.5221816897392273
- eval r2: 0.9750872254371643

Artifact handoff:

- eval and infer received the train step `model` artifact through `${train.artifacts.model.url}`.

Result: pass. The graph is the intended fixed `train -> eval -> infer` pipeline.
