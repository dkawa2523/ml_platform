# V2 Remote Gate ClearML UI Parameter Sets

Date: 2026-05-28

Use only the existing four ClearML templates and the current UI parameters. Do
not add `Run/profile`, `Run/output_dir`, `Output/artifact_name`,
`Output/report_plots`, or `Output/register_model`; they are not part of the
current UI surface.

Use `<Agent-reachable dev Dataset ID>` for the dev Dataset ID. For infer tasks,
use the `model` artifact URL produced by the selected optimization train task.

## Random Search Train

Task name: `v2_remote_optimization_random_train`  
Template: `tabular_train_template`

| Group | Parameter | Value |
| --- | --- | --- |
| Input | `Input/clearml_dataset_id` | `<Agent-reachable dev Dataset ID>` |
| Input | `Input/dataset_file` | `sample_train.csv` |
| Input | `Input/target_column` | `target` |
| Model | `Model/name` | `ridge` |
| Model | `Model/params` | `{}` |
| Model | `Model/search_enabled` | `true` |
| Model | `Model/search_method` | `random` |
| Model | `Model/search_space` | `{"alpha":[0.1,1.0,10.0,100.0]}` |
| Model | `Model/max_trials` | `2` |
| Model | `Model/selection_metric` | `rmse` |

Expected artifacts: `optimization_trials`, `optimization_summary`,
`best_params`, `model`, `model_info`, `metrics`, `manifest`,
`validation_predictions`, `config`.

Expected metrics: `mae`, `rmse`, `r2`.

Success criteria: task completes; `optimization_trials.csv` has 2 completed
trials; `best_params.json` exists; `model` is the best trial model; ClearML
Scalars and `metrics.json` show best trial metrics.

## Grid Search Train

Task name: `v2_remote_optimization_grid_train`  
Template: `tabular_train_template`

| Group | Parameter | Value |
| --- | --- | --- |
| Input | `Input/clearml_dataset_id` | `<Agent-reachable dev Dataset ID>` |
| Input | `Input/dataset_file` | `sample_train.csv` |
| Input | `Input/target_column` | `target` |
| Model | `Model/name` | `ridge` |
| Model | `Model/params` | `{}` |
| Model | `Model/search_enabled` | `true` |
| Model | `Model/search_method` | `grid` |
| Model | `Model/search_space` | `{"alpha":[0.1,1.0,10.0]}` |
| Model | `Model/max_trials` | `3` |
| Model | `Model/selection_metric` | `rmse` |

Expected artifacts: `optimization_trials`, `optimization_summary`,
`best_params`, `model`, `model_info`, `metrics`, `manifest`,
`validation_predictions`, `config`.

Expected metrics: `mae`, `rmse`, `r2`.

Success criteria: task completes; `optimization_trials.csv` has 3 completed
trials; `best_params.json` exists; `model` is downloadable and usable by
eval/infer; ClearML Scalars and `metrics.json` show best trial metrics.

## Optimized Best Model Infer

Task name: `v2_remote_optimized_best_infer`  
Template: `tabular_infer_template`

| Group | Parameter | Value |
| --- | --- | --- |
| Input | `Input/clearml_dataset_id` | `<Agent-reachable dev Dataset ID>` |
| Input | `Input/dataset_file` | `sample_infer.csv` |
| Model | `Model/artifact_path` | `<model artifact URL from random or grid train>` |
| Output | `Output/prediction_name` | `predictions.csv` |

Leave `Output/chunk_size` empty for non-chunked infer.

Expected artifacts: `predictions`, `manifest`, `config`, and `model_info` when
available from the model artifact package/path.

Expected metrics: none required for pure infer.

Success criteria: task completes; `predictions.csv` is uploaded as
`predictions`; output includes input columns plus `prediction`, `model_name`,
`artifact_kind`, `model_artifact_id`, and `prediction_run_id`; console log shows
model artifact resolution and Dataset access completed.

## Chunked Infer

Task name: `v2_remote_chunked_infer_grid_best`  
Template: `tabular_infer_template`

| Group | Parameter | Value |
| --- | --- | --- |
| Input | `Input/clearml_dataset_id` | `<Agent-reachable dev Dataset ID>` |
| Input | `Input/dataset_file` | `sample_infer.csv` |
| Model | `Model/artifact_path` | `<model artifact URL from grid train>` |
| Output | `Output/prediction_name` | `predictions.csv` |
| Output | `Output/chunk_size` | `10` |

Expected artifacts: `predictions`, `manifest`, `config`, and `model_info` when
available.

Expected metrics: none required for pure infer.

Success criteria: task completes; `predictions.csv` row count matches the infer
dataset; output schema matches V2.2 prediction schema; `manifest` records
`chunk_size=10`; ClearML Artifacts tab shows `predictions`.

## Optimization Pipeline

Task name: `v2_remote_optimization_pipeline`  
Template: `tabular_pipeline_template`

| Group | Parameter | Value |
| --- | --- | --- |
| Input | `Input/clearml_dataset_id` | `<Agent-reachable dev Dataset ID>` |
| Input | `Input/train_dataset_file` | `sample_train.csv` |
| Input | `Input/eval_dataset_file` | `sample_train.csv` |
| Input | `Input/infer_dataset_file` | `sample_infer.csv` |
| Model | `Model/name` | `ridge` |
| Model | `Model/params` | `{}` |
| Model | `Model/search_enabled` | `true` |
| Model | `Model/search_method` | `grid` |
| Model | `Model/search_space` | `{"alpha":[0.1,1.0,10.0]}` |
| Model | `Model/max_trials` | `3` |
| Model | `Model/selection_metric` | `rmse` |
| Model | `Model/feature_preset` | `basic` |

Leave ensemble parameters at defaults:
`Model/ensemble_enabled=false`, `Model/ensemble_method=mean_topk`,
`Model/ensemble_top_k=3`.

Expected artifacts:
- Parent pipeline task: no required artifacts.
- Train step: `optimization_trials`, `optimization_summary`, `best_params`,
  `model`, `model_info`, `metrics`, `manifest`, `validation_predictions`.
- Eval step: `metrics`, `manifest`, `evaluation_predictions`.
- Infer step: `predictions`, `manifest`.

Expected metrics: train and eval show `mae`, `rmse`, `r2`; infer has no required
scalar metrics.

Success criteria: pipeline completes; graph is fixed `train -> eval -> infer`;
eval and infer receive `Model/artifact_path=${train.artifacts.model.url}`;
train step shows HPO artifacts; infer step shows standardized `predictions`; no
Dataset URL reachability, package install, artifact upload, or handoff failures
appear in logs.

## Expected Artifact Summary

| Execution | Required artifacts |
| --- | --- |
| random search train | `optimization_trials`, `optimization_summary`, `best_params`, `model`, `model_info`, `metrics`, `manifest`, `validation_predictions`, `config` |
| grid search train | `optimization_trials`, `optimization_summary`, `best_params`, `model`, `model_info`, `metrics`, `manifest`, `validation_predictions`, `config` |
| optimized best model infer | `predictions`, `manifest`, `config` |
| chunked infer | `predictions`, `manifest`, `config` |
| optimization pipeline | train/eval/infer step artifacts; parent pipeline graph and logs are the primary parent-task evidence |

## Assumptions

- `Input/local_path`, `Input/feature_columns`, and `Input/id_columns` remain at
  template defaults unless the dev Dataset requires explicit overrides.
- `Run/task`, `Run/name`, and `Run/seed` remain at template defaults for these
  gate runs.
- `Output/chunk_size` exists only on `tabular_infer_template`; pipeline infer
  chunking is not exposed by the current pipeline UI surface.
- Pipeline controller and step tasks use the dev queue and require enough worker
  capacity for controller plus steps.
