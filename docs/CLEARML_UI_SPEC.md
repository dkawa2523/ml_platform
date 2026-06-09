# ClearML UI Spec

This document is the ClearML screen-level operation contract for the current
tabular product. Product scope lives in `docs/SPEC.md`; development rules live
in `AGENTS.md`.

## ClearML UI Goals

ClearML UI users should be able to:

- start the training pipeline without reading source code
- see which dataset, features, models, and ensemble settings were used
- inspect stage metrics, leaderboard, plots, artifacts, and manifests
- run inference from a trained best or ensemble artifact
- distinguish user-facing templates from internal stage tasks

## Project Layout

Profiles route ClearML objects by purpose.

| Purpose | Dev default |
| --- | --- |
| Templates | `MLPlatform/Dev/Templates/Tabular` |
| Pipeline controllers | `MLPlatform/Dev/Pipelines/Tabular` |
| Preprocess stage runs | `MLPlatform/Dev/Runs/Tabular/Preprocess` |
| Train stage runs | `MLPlatform/Dev/Runs/Tabular/Train` |
| Ensemble stage runs | `MLPlatform/Dev/Runs/Tabular/Ensemble` |
| Evaluate stage runs | `MLPlatform/Dev/Runs/Tabular/Evaluate` |
| Inference tasks | `MLPlatform/Dev/Runs/Tabular/Infer` |
| Experiments | `MLPlatform/Dev/Experiments/Tabular` |

Production profiles use the same structure under `MLPlatform/Prod/...`.
Project names come from profile config; do not hard-code them in package logic.

Old ClearML tasks may remain visible until a human archives them on the server.
Repo sync should create or update only the current canonical entries.

## Templates

User-facing entrypoints:

- Pipeline tab: `template/tabular_train_pipeline`
- Task template: `template/tabular_infer`

Internal entrypoint:

- `internal/tabular_stage`

Do not clone `internal/tabular_stage` directly for normal product runs. It is
used by PipelineController steps.

## Task Naming

Runtime names should follow:

- `pipeline/tabular_train_pipeline/<run_name>`
- `stage/preprocess_features/<run_name>`
- `stage/train_<model>/<run_name>`
- `stage/build_ensemble_<method>/<run_name>`
- `stage/evaluate_models/<run_name>`
- `task/tabular_infer/<run_name>`

## Tags

Use tags to filter and explain tasks:

- `domain:tabular`
- `run_type:template`, `run_type:pipeline`, `run_type:stage`, `run_type:task`
- `user_facing:true` or `internal:true`
- `stage:<stage_name>` for stage runs
- `model:<model_name>` for model training stages
- `ensemble:<method>` for ensemble method stages

## Training Pipeline Parameters

ClearML remote runs should use Dataset inputs, not repo-local paths.

| Parameter | Required | Notes |
| --- | --- | --- |
| `Input/clearml_dataset_id` | remote | ClearML Dataset id. |
| `Input/dataset_file` | remote | File inside the Dataset, for example `sample_train.csv`. |
| `Input/target_column` | local + remote | Scalar regression target. |
| `Input/local_path` | local only | Valid remotely only if the Agent can access the same path. |
| `Input/feature_columns` | optional | Defaults to `[]`. Empty means auto-select non-target, non-id columns. |
| `Input/id_columns` | optional | Excluded from features and preserved in outputs when applicable. |
| `Split/valid_size` | optional | Validation split fraction. |
| `Features/preset` | optional | Feature transformer preset, for example `basic` or `numeric_only`. |
| `Features/numeric_impute_strategy` | optional | `median`, `mean`, or `zero`. |
| `Features/categorical_impute_strategy` | optional | `missing_token` or `mode`. |
| `Features/categorical_encoder` | optional | `onehot` or `drop`. |
| `Features/scaling` | optional | `standard` or `none`. |
| `Features/drop_columns` | optional | JSON array or comma list of selected columns to remove before fitting features. |
| `Features/passthrough_columns` | optional | Numeric raw feature columns appended without impute/encoding/scaling. |
| `Run/name` | optional | Human-readable run suffix. |
| `Run/seed` | optional | Reproducibility seed. |
| `Model/candidates` | optional | JSON array of model names. New Run defaults should show all supported models. |
| `Model/model_params_by_name` | optional | JSON object keyed by model name. New Run defaults should include dependency-free and optional GBM model keys for editing. |
| `Model/ensemble_enabled` | optional | Enables ensemble building. |
| `Model/ensemble_methods` | optional | JSON array or comma list, for example `["mean_topk","weighted","median"]`. |
| `Model/ensemble_top_k` | optional | Number of ranked base models for top-k methods. |
| `Model/evaluation_metrics` | optional | JSON array or comma-separated metric names. |
| `Model/selection_metric` | optional | `rmse`, `mae`, or `r2`. |
| `Output/report_plots` | optional | False keeps artifacts, tables, and scalars but skips ClearML plot media reporting. |

Classification:

- Required local: `Input/local_path`, `Input/target_column`
- Required remote: `Input/clearml_dataset_id`, `Input/dataset_file`, `Input/target_column`
- Optional: feature/id columns, split settings, concrete feature settings, run name/seed, candidates, model params, ensemble settings, metrics, selection metric, plot reporting
- Supported optional dependency models: `lightgbm`, `xgboost`, `catboost` in `Model/candidates` when optional dependencies are installed
- Future / hidden from primary UI: optimization/search settings, artifact name overrides, and `pipeline_mode`

`Model/ensemble_method` is accepted by internal stage tasks and compatibility
paths when `Model/ensemble_methods` is absent, but normal users should set the
list-valued `Model/ensemble_methods` field.

Feature and preprocessing settings are product inputs. They should be visible in
Pipeline UI when users need to run the product from ClearML, even if the current
implementation still carries compatibility aliases under `Model/*`.

UI groups are not limited to four sections. The current training template uses
`Input`, `Split`, `Features`, `Run`, `Model`, and `Output`; future refinements
may split model, ensemble, and evaluation controls when that makes the New Run
form easier to scan.

Future-only feature inputs are `datetime_columns`, `text_columns`, and custom
transformers.

Do not expose `pipeline_mode`, search settings, or optimization settings as
primary training inputs.

## Model Candidates

ClearML New Run default candidates should show all supported models:

```json
["linear", "ridge", "lasso", "elasticnet", "random_forest", "extra_trees", "gradient_boosting", "lightgbm", "xgboost", "catboost"]
```

`gradient_boosting` is the sklearn GBDT-style model name. `lightgbm`,
`xgboost`, and `catboost` are supported optional-dependency models. Remove
those optional names before running if the Agent environment does not include
the extra, for example `pip install -e "pkgs/tabular[gbm]"`.

The New Run form should still prefill `Model/model_params_by_name` with
`lightgbm`, `xgboost`, and `catboost` parameter keys. Those entries are settings
for supported optional-dependency models.

Out-of-scope models such as `knn`, `svr`, `mlp`, `gaussian_process`, and
`tabpfn` should not be used as current product candidates.

## Result Visibility

The Pipeline tab graph should show:

```text
preprocess_features
  -> train_<model>*
  -> build_ensemble_<method>*
  -> evaluate_models
```

Expected ClearML screens:

| Screen | Expected content |
| --- | --- |
| Configuration / Hyperparameters | Dataset id/file, split, target column, feature settings, candidates, ensemble methods, evaluation metric. |
| Scalars | feature counts under `features/*`; `metrics_by_candidate/rmse`, `metrics_by_candidate/mae`, `metrics_by_candidate/r2`; compatibility `metrics_by_model/*`; `ensemble/*`; `best_model/*`. |
| Plots | feature missingness, feature importance where available, prediction-vs-actual with `R2` and `y=x`, residual histogram with axis labels, residual-vs-predicted, candidate comparison plots from `candidate_predictions`, per-method ensemble plots, prediction distribution for inference. |
| Artifacts | model artifacts, per-method ensemble artifacts, `feature_summary`, `feature_missingness`, `leaderboard`, `metrics_by_candidate`, `metrics_by_model`, `best_model_json`, `evaluation_report`, `evaluation_predictions`, `manifest`. |
| Debug Samples / Tables | `feature_summary`, `feature_missingness`, `leaderboard`, `evaluation_summary`, train-stage `validation_predictions`, `feature_importance_<model>`, aggregate `evaluation_predictions`, per-method `ensemble_predictions_<method>`, `ensemble_members_<method>`, `ensemble_weights_<method>`, inference-only `predictions` and `prediction_summary`. |
| Console | dataset resolution, stage selection, artifact resolution, missing dependency errors. |
| Graph | stage order and parent/child handoff. |

If a run succeeds but users cannot understand these outputs in UI, product UX is
not complete.

Each `train_<model>` stage shows only that model's plots. Cross-model and
cross-ensemble comparison belongs in `evaluate_models`, where
`candidate_prediction_vs_actual`, `candidate_residual_histogram`, and
`candidate_residual_vs_predicted` should include base models and ensemble
methods in the same view.

## Inference Parameters

Recommended ClearML inference:

```text
Model/source_type=task_id
Model/source_task_id=<training pipeline controller or stage task id>
Model/model_selector=best
```

Use `Model/model_selector=ensemble` for the best ensemble artifact. With
multiple ensemble methods, use `ensemble:<method>`, for example
`ensemble:median`, without creating a new inference template.

Local inference can use:

```text
Model/source_type=local_path
Model/local_model_path=<local training pipeline run dir or model file>
```

`artifact_url` and `clearml_model_id` are future / experimental sources and
should not be presented as the primary workflow.

## Inference Result Visibility

Inference tasks should expose:

- `predictions.csv`
- `prediction_summary.csv`
- `prediction_distribution_histogram.png`
- `manifest.json`
- model source metadata
- source task id and model selector
- preserved id columns when configured

## Multi-User Operation

- Keep user-facing templates and internal stage templates in separate projects.
- Use tags before searching by task name alone.
- Prefer `Input/clearml_dataset_id` and `Input/dataset_file` for Agent runs.
- Treat `Input/local_path` as local/dev unless the path is mounted in the Agent.
- Do not archive old ClearML tasks automatically from repo scripts.

## What Not To Do

- Do not create model-specific, dataset-specific, or one-template-per-ensemble-method variants.
- Do not make `train -> eval -> infer` the training pipeline.
- Do not present optimization as the current primary UI flow.
- Do not expose optional model dependencies as required runtime packages.
- Do not add a diagnostics framework when a simple table, scalar, or plot is
  enough.

## Failure Triage

Check in this order:

1. Console log for dataset, dependency, or artifact resolution errors.
2. Configuration values for Dataset id, dataset file, target, candidates, and selector.
3. Failed stage task artifacts and `manifest.json`.
4. Pipeline graph parent/child handoff.
5. Agent queue capacity and Dataset artifact URL reachability.
