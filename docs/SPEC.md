# Specification

## Product Goal

`ml_platform` is a ClearML-based machine learning execution platform. The
current primary product domain is tabular scalar regression.

The product must support two workflows:

- ClearML UI users select a dataset, set parameters, run a task or pipeline,
  and inspect metrics, leaderboard, artifacts, predictions, and pipeline graph
  without reading code.
- Data scientists and architects can improve preprocessing, feature
  engineering, models, ensemble logic, evaluation, inference, and ClearML
  integration without being blocked by unnecessary prohibitions, helpers,
  diagnostics, tests, or docs.

Legacy repositories are reference material only. This repository does not target
legacy full parity or legacy directory/config recreation.

## Product Scope

### Supported

- local tabular scalar regression training pipeline
- local tabular batch inference task
- ClearML Dataset id / dataset file handling
- dependency-free supported models: `linear`, `ridge`, `lasso`, `elasticnet`,
  `random_forest`, `extra_trees`, `gradient_boosting`
- optional-dependency supported models: `lightgbm`, `xgboost`, `catboost`
- user-facing preprocessing and feature parameters in the training Pipeline UI
- multiple model training through `model.candidates`
- one training pipeline can run and compare multiple ensemble methods such as
  `mean_topk`, `weighted`, and `median`
- leaderboard and best model selection
- validation prediction tables with `actual`, `prediction`, `residual`, and
  `abs_error`
- lightweight prediction-vs-actual and residual histogram artifacts
- current ClearML template sync and dry-run surface

Supported currently means local execution plus repository-side dry-run evidence.
ClearML remote execution is promoted only after dev-server evidence is recorded
in `verification/training_pipeline/release_gate.md`.

### Experimental / Future

- ClearML remote execution of the stage-based training pipeline until dev-server
  evidence is recorded
- ClearML remote inference from `source_task_id` until best/ensemble evidence is
  recorded
- optimization pipeline
- `search_trials`, `retrain_best`, `evaluate_best`
- `artifact_url` inference source
- `clearml_model_id` inference source
- external model full pipeline
- Optuna / Ray Tune
- per-trial ClearML child tasks
- online serving
- tabular 1D/2D productization
- distribution mode decomposition
- advanced plots and reports

### Out Of Scope

- calling `train -> eval -> infer` the training pipeline
- optimization as the primary product flow
- full pipeline templates as primary templates
- full ensemble pipeline templates as primary templates
- `knn`, `svr`, and `mlp`
- `gaussian_process`
- `tabpfn`
- stacking
- model-specific templates
- one-template-per-ensemble-method variants
- optimization-specific templates
- dataset-specific templates
- direct copy of legacy `train_ensemble_full`
- excessive diagnostics, tests, helpers, and docs

## Training Pipeline

The official training pipeline is:

```text
preprocess_features
  -> train_<model>*
  -> build_ensemble_<method>*
  -> evaluate_models
```

Each ClearML ensemble step uses the same internal `build_ensemble` stage runner
and one ensemble method. Do not create ensemble-specific templates.

The intended ClearML graph for the default tabular regression product is:

```text
preprocess_features
  -> train_linear
  -> train_ridge
  -> train_lasso
  -> train_elasticnet
  -> train_random_forest
  -> train_extra_trees
  -> train_gradient_boosting
  -> build_ensemble_mean_topk
  -> build_ensemble_weighted
  -> build_ensemble_median
  -> evaluate_models
```

Each `train_<model>` node uses the same internal stage template with a different
step name and `Model/name`. Do not create model-specific templates.

Model selection is done with `model.candidates` locally and `Model/candidates`
in ClearML UI. Portable default candidates may stay dependency-free so the
pipeline runs on a minimal Agent image.

`Model/model_params_by_name` should be prefilled with editable keys for all
supported models, including optional-dependency GBM models. This lets ClearML
New Run users see the available model settings without making optional GBM
models part of the default runnable candidates.

Dependency-free supported models are:

- `linear`
- `ridge`
- `lasso`
- `elasticnet`
- `random_forest`
- `extra_trees`
- `gradient_boosting`

Optional-dependency supported models are:

- `lightgbm`
- `xgboost`
- `catboost`

Optional-dependency models are product-supported, but executable only when their
dependency is installed in the local or Agent environment. If a dependency is
missing, the selected optional model should fail with a clear installation error
without breaking dependency-free model runs.

Install optional model dependencies explicitly, for example
`pip install -e "pkgs/tabular[gbm]"`. Do not add them to base runtime
requirements.

Out-of-scope models are `knn`, `svr`, `mlp`, `gaussian_process`, and `tabpfn`.

Primary stages:

- `preprocess_features`
- `train_model`
- `build_ensemble`
- `evaluate_models`

Future stages:

- `search_trials`
- `retrain_best`
- `evaluate_best`

## Inference

Inference is separate from the training pipeline. The official inference
entrypoint is `tabular_infer_template`.

Primary inference sources:

- `source_task_id + model_selector`
- `local_model_path`

Future inference sources:

- `artifact_url`
- `clearml_model_id`

Inference flow:

```text
source_task_id + model_selector
or local_model_path
-> inference dataset
-> feature align
-> predict
-> predictions.csv
```

`model_selector=best` resolves the selected best model from `evaluate_models`.
`model_selector=ensemble` resolves the best ensemble artifact from a
`build_ensemble_<method>` task that runs the internal `build_ensemble` stage.
Supported model names such as `linear` or `ridge` resolve the matching
`train_<model>` artifact.

`source_task_id` may point to a training pipeline controller task or directly to
an `evaluate_models`, `build_ensemble_<method>`, or `train_<model>` stage task. The
selector decides which artifact is used.

Feature alignment uses explicit `data.feature_columns` first, then model
metadata from the referenced artifact, then `feature_spec.json` /
`preprocess_bundle` metadata when available. Model artifacts remain
self-contained for prediction.

Do not add an inference pipeline unless a future product decision explicitly
requires it.

## Template Policy

User-facing templates:

- `tabular_train_pipeline_template`
- `tabular_infer_template`

Internal template:

- `tabular_stage_template`

Default sync target:

- `tabular_train_pipeline_template`
- `tabular_infer_template`
- `tabular_stage_template`

Deprecated, deleted, or sync-excluded:

- `tabular_train_full_pipeline_template`
- `tabular_train_full_ensemble_pipeline_template`
- legacy `tabular_pipeline_template`
- optimize-specific templates
- model-specific templates
- one-template-per-ensemble-method variants
- dataset-specific templates

`tabular_stage_template` is for PipelineController steps. It is not the normal
template that ClearML UI users clone directly.

ClearML display names:

- `template/tabular_train_pipeline`
- `template/tabular_infer`
- `internal/tabular_stage`

Profile-managed ClearML projects:

| purpose | dev default |
| --- | --- |
| templates | `MLPlatform/Dev/Templates/Tabular` |
| pipelines | `MLPlatform/Dev/Pipelines/Tabular` |
| preprocess | `MLPlatform/Dev/Runs/Tabular/Preprocess` |
| train | `MLPlatform/Dev/Runs/Tabular/Train` |
| ensemble | `MLPlatform/Dev/Runs/Tabular/Ensemble` |
| evaluate | `MLPlatform/Dev/Runs/Tabular/Evaluate` |
| infer | `MLPlatform/Dev/Runs/Tabular/Infer` |
| experiments | `MLPlatform/Dev/Experiments/Tabular` |

Runtime naming:

- `pipeline/tabular_train_pipeline/<run_name>`
- `stage/preprocess_features/<run_name>`
- `stage/train_<model>/<run_name>`
- `stage/build_ensemble_<method>/<run_name>`
- `stage/evaluate_models/<run_name>`
- `task/tabular_infer/<run_name>`

Canonical ClearML tags:

- `domain:tabular`
- `run_type:template`, `run_type:pipeline`, `run_type:stage`, or `run_type:task`
- `user_facing:true` or `internal:true`
- `stage:<stage_name>` for stage tasks
- `model:<model_name>` for model training stages

## Config Policy

Config uses two axes:

```text
config/tasks
config/profiles
```

Primary task configs:

- `config/tasks/tabular_pipeline.yaml`
- `config/tasks/tabular_infer.yaml`
- `config/tasks/tabular_stage.yaml`

Deprecated or future configs must not be presented as the normal product entry.

## ClearML UI Policy

ClearML screen-level behavior is specified in `docs/CLEARML_UI_SPEC.md`.
Keep this section as product policy and avoid duplicating long operation notes.

Keep UI parameters compact by default. The current implementation may still use
`Input`, `Run`, `Model`, and `Output`, but the product policy allows semantic
groups when they make ClearML New Run forms easier to understand:

- `Input`
- `Split`
- `Features`
- `Models`
- `Ensemble`
- `Evaluation`
- `Output`
- `Run`

Avoid template sprawl. Do not add model-specific or dataset-specific templates,
and do not create one template per ensemble method. Use candidates, ensemble
parameters, and stage overrides instead.

Primary inference UI parameters:

- `Model/source_type`
- `Model/source_task_id`
- `Model/model_selector`
- `Model/local_model_path`

Primary training UI parameters:

| parameter | local | ClearML remote | note |
| --- | --- | --- | --- |
| `Input/local_path` | required | avoid | Use only when the Agent can see the same path. |
| `Input/clearml_dataset_id` | optional | required | Preferred remote Dataset source. |
| `Input/dataset_file` | optional | required when Dataset has multiple files | Example: `sample_train.csv`. |
| `Input/target_column` | required | required | Scalar regression target. |
| `Input/feature_columns` | optional | optional | Empty auto-selects non-target, non-id columns. |
| `Input/id_columns` | optional | optional | Excluded from features. |
| `Split/valid_size` | optional | optional | Validation split fraction. |
| `Features/preset` | optional | optional | Feature transformer preset, for example `basic` or `numeric_only`. |
| `Features/numeric_impute_strategy` | optional | optional | `median`, `mean`, or `zero`. |
| `Features/categorical_impute_strategy` | optional | optional | `missing_token` or `mode`. |
| `Features/categorical_encoder` | optional | optional | `onehot` or `drop`. |
| `Features/scaling` | optional | optional | `standard` or `none`. |
| `Features/drop_columns` | optional | optional | JSON array or comma list of selected columns to remove before fitting features. |
| `Features/passthrough_columns` | optional | optional | Numeric raw feature columns appended without impute/encoding/scaling. |
| `Model/candidates` | optional | optional | JSON array. Portable defaults may be dependency-free; optional supported models must be explicit when the Agent has dependencies. |
| `Model/model_params_by_name` | optional | optional | JSON object keyed by model name. New Run defaults should include dependency-free and optional GBM model keys for editing. |
| `Model/ensemble_enabled` | optional | optional | Enables ensemble building. |
| `Model/ensemble_methods` | optional | optional | JSON array or comma list, for example `["mean_topk","weighted","median"]`. |
| `Model/ensemble_top_k` | optional | optional | Number of ranked base models for top-k ensemble methods. |
| `Model/evaluation_metrics` | optional | optional | JSON array or comma-separated metric names. |
| `Model/selection_metric` | optional | optional | `rmse`, `mae`, or `r2`; used for leaderboard selection. |
| `Output/report_plots` | optional | optional | Set false to skip ClearML plot media reporting. |

ClearML UI parameter groups may stay compact or become semantic when that makes
the UI easier to use. The current training template uses `Input`, `Split`,
`Features`, `Run`, `Model`, and `Output`. Future UI refinements may split model,
ensemble, and evaluation controls into separate semantic groups when that improves
operator clarity.

Future feature inputs are `datetime_columns`, `text_columns`, and custom
transformers. Keep them documented as future until implemented.

`Model/ensemble_method` remains accepted as a compatibility/internal stage
alias when `Model/ensemble_methods` is absent, but it is not part of the
user-facing training Pipeline New Run parameter set.

Future inference UI parameters, if still present in code, must be documented as
future rather than primary:

- `Model/model_artifact_url`
- `Model/clearml_model_id`

## Artifact Policy

Training pipeline artifacts:

- `preprocess_bundle`
- `feature_spec.json`
- `feature_summary.json`
- `feature_summary_table.csv`
- `missing_rate_by_column.csv`
- `feature_type_counts.csv`
- model artifacts
- model feature importance table/plot when the estimator exposes importances or coefficients
- `model_refs.json`
- validation predictions
- `metrics_by_model.json`
- `metrics_by_candidate.json`
- `leaderboard.csv`
- `best_model.json`
- `ensemble_refs.json`
- `ensemble_info_by_method.json`
- `ensemble_members_<method>.csv`
- `ensemble_weights_<method>.csv`
- ensemble artifacts
- `evaluation_report.json`
- `evaluation_summary.csv`
- `evaluation_predictions.csv`
- `metrics.json`
- `manifest.json`

ClearML result display:

- artifacts: model files, `feature_summary`, `leaderboard`, `best_model_json`,
  `ensemble_info`, `evaluation_report`, `manifest`
- tables: feature summary/missingness, leaderboard, evaluation summary,
  evaluation predictions, feature importance, ensemble members/weights, and
  inference predictions
- scalars: feature counts, per-model `rmse`, `mae`, `r2`; ensemble and
  best-model summaries
- plots: feature missingness, feature importance where available,
  prediction-vs-actual and residual histogram from prediction tables, prediction
  distribution for inference, plus metrics-by-candidate/model artifacts

Inference artifacts:

- `predictions.csv`
- `prediction_summary.csv`
- `prediction_distribution_histogram.png`
- `manifest.json`

Artifacts should make the ClearML UI readable without requiring users to inspect
source code.

## Architecture Boundaries

```text
scripts/local_run.py      -> pkgs
clearml/app.py           -> clearml/adapter.py -> pkgs
clearml/pipelines.py     -> ClearML PipelineController
pkgs/core                -> common ClearML-free utilities
pkgs/tabular             -> ClearML-free tabular ML logic
```

Forbidden dependencies:

```text
pkgs/core    -> clearml
pkgs/tabular -> clearml
pkgs         -> deploy
pkgs         -> scripts
```

`scripts/` are wrappers only. Business logic belongs in `pkgs` or `clearml/`
according to the boundary above.

## Extension Points

- Add models in `pkgs/tabular/src/ml_platform_tabular/models.py`.
- Add feature logic in `pkgs/tabular/src/ml_platform_tabular/features.py`.
- Add metrics in `pkgs/tabular/src/ml_platform_tabular/metrics.py`.
- Add ensemble behavior in `pkgs/tabular/src/ml_platform_tabular/ensemble.py`.
- Change ClearML parameter mapping in `clearml/adapter.py`.
- Change ClearML reporting in `clearml/reports.py`.
- Change template sync in `clearml/templates.py`.

Add abstractions only when they reduce real duplication inside the current
product scope.


## ClearML UI Product Contract

ClearML UI behavior is specified in `docs/CLEARML_UI_SPEC.md`.

The product is not complete if a run only succeeds technically but does not expose enough information for users to understand:

- which dataset was used
- which features were used
- which models were trained
- which model won
- whether ensemble improved metrics
- where predictions are stored
- which artifacts should be reused for inference

## Result Visibility

Each product pipeline must provide user-visible artifacts and metrics.

Training pipeline must expose:

- feature summary
- model metrics
- leaderboard
- best model metadata
- ensemble metadata when enabled
- evaluation report
- prediction-vs-actual plot
- residual histogram
- manifest

Inference must expose:

- prediction table
- model source metadata
- manifest
