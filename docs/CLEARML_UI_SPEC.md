# ClearML UI Specification

This is the screen-level guide for the current tabular regression product.
Product scope lives in `docs/SPEC.md`; future/P2 scope lives in
`docs/ROADMAP.md`.

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

These are ClearML task names and step labels. Package stage keys remain
`train_model` and `build_ensemble`; the model/method suffixes are display names
used by PipelineController.

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

Basic parameters are the recommended first-run surface:

- `Basic/model_suite`
- `Basic/quality_mode`
- `Basic/use_ensemble`
- `Basic/notes`

`Basic/model_suite` values:

| value | model candidates |
| --- | --- |
| `default` | all supported models |
| `fast` | dependency-free models only |
| `interpretable` | `linear`, `ridge`, `lasso`, `elasticnet` |
| `tree` | `random_forest`, `extra_trees`, `gradient_boosting` |
| `gbm` | `lightgbm`, `xgboost`, `catboost` |
| `custom` | use `Model/candidates` directly |

`Basic/quality_mode` applies small, fixed parameter presets. It does not run HPO
or search:

| value | parameter behavior |
| --- | --- |
| `fast` | smaller tree/GBM estimator counts for quick checks |
| `standard` | current default-sized parameters |
| `quality` | modestly larger tree/GBM estimator counts, still bounded |

If `Model/model_params_by_name` or `Model/params` is explicitly edited, that
detailed value takes precedence. With `Basic/model_suite=custom`, candidates and
params stay driven by the detailed `Model/*` fields.

HPO/search settings are not part of the user-facing Pipeline New Run surface.
Future optimization should remain behind a small Basic-level control rather
than exposing raw search spaces to first-run users.

`Basic/use_ensemble` controls whether `build_ensemble_<method>` steps are added.
The detailed `Model/ensemble_enabled` parameter is blank by default; if a user
explicitly sets it to `true` or `false`, it takes precedence over
`Basic/use_ensemble`.

Detailed user-facing parameters remain available:

- `Input/feature_columns`
- `Input/id_columns`
- `Split/method`
- `Split/valid_size`
- `Split/group_column`
- `Split/time_column`
- `Split/valid_filter_column`
- `Split/valid_filter_value`
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
- `Output/upload_plots`

`Split/method` values are `random`, `group`, `time`, and `fixed`. `random` uses
the existing seeded holdout behavior. `group` requires `Split/group_column` and
keeps a group out of both train and validation at the same time. `time` requires
`Split/time_column` and uses the latest rows as validation. `fixed` requires
`Split/valid_filter_column` and `Split/valid_filter_value`; matching rows become
validation rows. `external_valid_file`, k-fold, nested CV, and `group_kfold` are
not implemented and are not part of this UI.

Default `Basic/model_suite=default` and default `Model/candidates` should show
all supported models:

```json
["linear", "ridge", "lasso", "elasticnet", "random_forest", "extra_trees", "gradient_boosting", "lightgbm", "xgboost", "catboost"]
```

The selected profile sets `clearml.execution.image`. Synced templates also add
GBM packages to the remote execution venv so the 10-model default can run on
the standard Agent image. `Basic/model_suite=gbm` can fail in local or slim
custom environments unless LightGBM, XGBoost, and CatBoost are installed.
Slim/custom runs may choose `Basic/model_suite=fast` or remove GBM names from
`Model/candidates`.

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
| `preprocess_features` | feature counts | feature summary, data quality summary/warnings, missing rate, type counts | missing-rate bar |
| `train_<model>` | rmse, mae, r2 | metrics, validation predictions, feature importance when available | prediction-vs-actual, residual histogram, residual-vs-predicted, feature importance |
| `build_ensemble_<method>` | ensemble metrics | metrics, predictions, members, weights | method prediction/residual plots, weights, metrics bar |
| `evaluate_models` | best metrics | leaderboard, best model, evaluation predictions | leaderboard metric panel, best prediction diagnostics |

Compatibility alias artifacts may exist in old runs, but the current UI should
prefer the minimal outputs from new runs.

In `evaluate_models`, the first artifact to open is `best_model.json`. It is the
canonical inference decision artifact and lists the recommended inference
settings:

- `Model/source_type=task_id`
- `Model/source_task_id=<training_or_evaluate_task_id>`
- `Model/model_selector=best`

Use `leaderboard.csv` when you need to compare all candidates.

## Inference UI

Recommended task parameters:

- `Model/source_type=task_id`
- `Model/source_task_id=<pipeline or stage task id>`
- `Model/model_selector=best`

Supported selectors include `best`, supported model names, `ensemble`, and
`ensemble:<method>`.

Expected inference outputs:

- `predictions.csv`
- `schema_check_summary.csv` / `schema_check_summary.json`
- `prediction_summary.csv`
- `prediction_preview.csv`
- `source_summary.csv`
- prediction distribution plot
- `manifest.json`

`schema_check_summary` should be visible as a ClearML table. It shows whether
the input schema is `ok`, `warning`, or `error`; missing required features fail
the run, while extra columns and unseen categories are warnings. `predictions.csv`
should stay slim: `row_index`, ID columns when available, `prediction`, and
lightweight model metadata only.

Inference tasks should not show candidate comparison plots.

Drift/monitoring and Model Registry promotion are not current ClearML UI
surfaces. Future monitoring should compare accumulated inference summaries;
future registration should start from the `evaluate_models` best-model decision.

## P2 Items Not Shown In Current UI

- HPO / hyperparameter optimization.
- Model Registry approval or promotion.
- Drift / monitoring dashboards.
- Task Registry for 1D/2D output or mode decomposition tasks.
- `external_valid_file`, k-fold, nested CV, and `group_kfold`.

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
