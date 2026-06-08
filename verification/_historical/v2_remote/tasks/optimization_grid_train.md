# optimization_grid_train

Date: 2026-05-28T22:23:38+09:00
Git commit: `d864267`
Template: `tabular_train_template`
Task ID: `cf5616f7025d4bd498fa8d7be8cb2528`
Task URL: http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/cf5616f7025d4bd498fa8d7be8cb2528/output/log
Queue: `default`
Status: `completed`

## Changed UI Parameters

- `Input/clearml_dataset_id`: `<Agent-reachable dev Dataset ID>`
- `Input/dataset_file`: `sample_train.csv`
- `Input/target_column`: `target`
- `Model/name`: `ridge`
- `Model/params`: `{}`
- `Model/search_enabled`: `True`
- `Model/search_method`: `grid`
- `Model/search_space`: `{"alpha":[0.1,1.0,10.0]}`
- `Model/max_trials`: `3`

## Artifacts

- best_params
- config
- manifest
- metrics
- model
- model_info
- optimization_summary
- optimization_trials
- validation_predictions

## Console Log Tail

```text
task cf5616f7025d4bd498fa8d7be8cb2528 pulled by dev worker
repository = https://github.com/dkawa2523/ml_platform.git
branch = main
HEAD is now at d864267 Implement V2 pipeline optimization and inference gates
entry_point = clearml/app.py --task config/tasks/tabular_train.yaml --profile config/profiles/clearml-dev.yaml
Environment setup completed successfully
Starting Task Execution
ClearML results page: http://webserver:80/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/cf5616f7025d4bd498fa8d7be8cb2528/output/log
Dataset.get completed for the dev dataset
Process completed successfully
```

## Notes

Expected artifacts: optimization_trials, optimization_summary, best_params, model, model_info, metrics, manifest.

