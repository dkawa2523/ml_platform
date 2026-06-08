# optimization_pipeline

Date: 2026-05-28T22:23:38+09:00
Git commit: `d864267`
Template: `tabular_pipeline_template`
Task ID: `0154d6206bc14677aee172eef89609bf`
Task URL: http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/0154d6206bc14677aee172eef89609bf/output/log
Queue: `default`
Status: `completed`

## Changed UI Parameters

- `Input/clearml_dataset_id`: `<Agent-reachable dev Dataset ID>`
- `Input/train_dataset_file`: `sample_train.csv`
- `Input/eval_dataset_file`: `sample_train.csv`
- `Input/infer_dataset_file`: `sample_infer.csv`
- `Model/name`: `ridge`
- `Model/params`: `{}`
- `Model/search_enabled`: `True`
- `Model/search_method`: `grid`
- `Model/search_space`: `{"alpha":[0.1,1.0,10.0]}`
- `Model/max_trials`: `3`
- `Model/feature_preset`: `basic`

## Artifacts

- <none>

## Console Log Tail

```text
task 0154d6206bc14677aee172eef89609bf pulled by dev worker
repository = https://github.com/dkawa2523/ml_platform.git
branch = main
HEAD is now at d864267 Implement V2 pipeline optimization and inference gates
entry_point = clearml/pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml
Environment setup completed successfully
Starting Task Execution
ClearML results page: http://webserver:80/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/0154d6206bc14677aee172eef89609bf/output/log
ClearML pipeline page: http://webserver:80/pipelines/dff412a3cc954606bd3718c3d1ef8fe2/experiments/0154d6206bc14677aee172eef89609bf
Launching step [train]
train parameters include Model/search_enabled=true, Model/search_method=grid, Model/search_space, and Model/max_trials=3
Launching step [eval]
eval receives Model/artifact_path=${train.artifacts.model.url}
Launching step [infer]
infer receives Model/artifact_path=${train.artifacts.model.url}
Process completed successfully
```

## Notes

Expected graph: train -> eval -> infer. Step task artifacts should include train optimization outputs and infer predictions.

