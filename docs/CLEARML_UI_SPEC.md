# ClearML UI Specification

This is the screen-level guide for the current tabular regression product.
Product scope lives in `docs/SPEC.md`.

## Entry Points

- Pipeline tab: `template/tabular_train_pipeline`
- Task template: `template/tabular_infer`
- Internal stage template: `internal/tabular_stage`

Users should start from the Pipeline tab for training and from
`template/tabular_infer` for inference. `internal/tabular_stage` is for
PipelineController steps.

Run the training PipelineController on the profile `controller_queue`; stage
steps are queued to `stage_queue`. In dev this means controller queue
`controller` and stage queue `default`.

## Projects

| object | dev project |
| --- | --- |
| templates | `MLPlatform/Dev/Templates/Tabular` |
| pipeline controllers | `MLPlatform/Dev/Pipelines/Tabular` |
| preprocess stages | `MLPlatform/Dev/Runs/Tabular/Preprocess` |
| train stages | `MLPlatform/Dev/Runs/Tabular/Train` |
| ensemble stages | `MLPlatform/Dev/Runs/Tabular/Ensemble` |
| evaluate stages | `MLPlatform/Dev/Runs/Tabular/Evaluate` |
| inference tasks | `MLPlatform/Dev/Runs/Tabular/Infer` |
| experiments | `MLPlatform/Dev/Experiments/Tabular` |

Project names come from profile config.

## Names And Tags

Runtime names:

- `pipeline/tabular_train_pipeline/<run_name>`
- `stage/preprocess_features/<run_name>`
- `stage/train_<model>/<run_name>`
- `stage/build_ensemble_<method>/<run_name>`
- `stage/evaluate_models/<run_name>`
- `task/tabular_infer/<run_name>`

Required tags:

- `domain:tabular`
- `run_type:template|pipeline|stage|task`
- `user_facing:true` or `internal:true`
- `stage:<stage_name>`
- `model:<model_name>` for train stages
- `ensemble:<method>` for ensemble stages

## Training New Run Parameters

Remote runs should use `Input/clearml_dataset_id`, `Input/dataset_file`, and
`Input/target_column`. `Input/local_path` is for local or mounted-path runs.

Important user-facing parameters:

- `Input/feature_columns`
- `Input/id_columns`
- `Split/valid_size`
- `Features/preset`
- `Features/numeric_impute_strategy`
- `Features/categorical_impute_strategy`
- `Features/categorical_encoder`
- `Features/scaling`
- `Features/drop_columns`
- `Features/passthrough_columns`
- `Model/candidates`
- `Model/model_params_by_name`
- `Model/ensemble_enabled`
- `Model/ensemble_methods`
- `Model/ensemble_top_k`
- `Model/evaluation_metrics`
- `Model/selection_metric`
- `Output/report_plots`

Default `Model/candidates` should show all supported models:

```json
["linear", "ridge", "lasso", "elasticnet", "random_forest", "extra_trees", "gradient_boosting", "lightgbm", "xgboost", "catboost"]
```

The selected profile sets `clearml.execution.image`. Synced templates also add
GBM packages to the remote execution venv so the 10-model default can run on
the standard Agent image. Slim/custom runs may remove `lightgbm`, `xgboost`,
and `catboost` from `Model/candidates`.

## Expected Training UI

Pipeline graph:

```text
preprocess_features
  -> train_<model>*
  -> build_ensemble_<method>*
  -> evaluate_models
```

Expected stage UI:

| stage | Scalars | Tables | Plots |
| --- | --- | --- | --- |
| `preprocess_features` | feature counts | feature summary, missing rate, type counts | missing-rate bar |
| `train_<model>` | rmse, mae, r2 | metrics, validation predictions, feature importance when available | prediction-vs-actual, residual histogram, residual-vs-predicted, feature importance |
| `build_ensemble_<method>` | ensemble metrics | metrics, predictions, members, weights | method prediction/residual plots, weights, metrics bar |
| `evaluate_models` | candidate, ensemble, best metrics | leaderboard, top-k, decision summary, evaluation predictions, candidate predictions | `leaderboard/table`, top-k scores, metric panel, Pareto, top-k prediction/residual plots |

Compatibility alias artifacts may exist, but the UI should prefer canonical
tables and plots. Full `candidate_predictions.csv` is evidence; the primary
PLOTS view should stay top-k and leaderboard-focused.

## Inference UI

Recommended task parameters:

- `Model/source_type=task_id`
- `Model/source_task_id=<pipeline or stage task id>`
- `Model/model_selector=best`

Supported selectors include `best`, supported model names, `ensemble`, and
`ensemble:<method>`.

Expected inference outputs:

- `predictions.csv`
- `prediction_summary.csv`
- `prediction_preview.csv`
- `source_summary.csv`
- prediction distribution plot
- `manifest.json`

Inference tasks should not show candidate comparison plots.

## Operational Notes

- Old ClearML tasks are not deleted by repo code; archive them manually.
- Template sync rebuilds the Pipeline draft because ClearML stores the step
  graph separately from task parameters. If New Run does not show 10 supported
  models and three ensemble methods, open the latest synced
  `template/tabular_train_pipeline`, not an old run clone.
- If `preprocess_features` remains queued, verify the pipeline controller was
  started on the controller queue, not on the stage queue.
- If a GBM step fails with a missing dependency, re-sync the latest templates
  so the remote package list is updated, or remove GBM names for slim/custom
  runs.
