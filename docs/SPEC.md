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
  integration without excessive helpers, diagnostics, tests, or docs.

Legacy repositories are reference material only. This repository does not target
legacy full parity or legacy directory/config recreation.

## Product Scope

### Supported

- local tabular scalar regression training pipeline
- local tabular batch inference task
- ClearML Dataset id / dataset file handling
- supported sklearn models: `linear`, `ridge`, `lasso`, `elasticnet`,
  `random_forest`, `extra_trees`, `gradient_boosting`
- multiple model training through `model.candidates`
- `mean_topk` / `weighted` ensemble
- leaderboard and best model selection
- validation prediction tables with `actual`, `prediction`, `residual`, and
  `abs_error`
- lightweight prediction-vs-actual and residual histogram artifacts
- current ClearML template sync and dry-run surface

### Experimental / Future

- ClearML remote execution of the stage-based training pipeline until dev-server
  evidence is recorded
- ClearML remote inference from `source_task_id` until best/ensemble evidence is
  recorded
- optimization pipeline
- `search_trials`, `retrain_best`, `evaluate_best`
- `artifact_url` inference source
- `clearml_model_id` inference source
- experimental models with optional dependencies: `lightgbm`, `xgboost`,
  `catboost`
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
- ensemble-specific templates
- optimization-specific templates
- dataset-specific templates
- direct copy of legacy `train_ensemble_full`
- excessive diagnostics, tests, helpers, and docs

## Training Pipeline

The official training pipeline is:

```text
preprocess_features
  -> train_<model>*
  -> build_ensemble
  -> evaluate_models
```

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
  -> build_ensemble
  -> evaluate_models
```

Each `train_<model>` node uses the same internal stage template with a different
step name and `Model/name`. Do not create model-specific templates.

Model selection is done with `model.candidates` locally and `Model/candidates`
in ClearML UI. Default candidates must not include experimental models.

Supported models are:

- `linear`
- `ridge`
- `lasso`
- `elasticnet`
- `random_forest`
- `extra_trees`
- `gradient_boosting`

Experimental models are:

- `lightgbm`
- `xgboost`
- `catboost`

Experimental models are executable only when their optional dependency is
installed in the local or Agent environment. They are not supported until local
and ClearML remote evidence is recorded.

Install experimental model dependencies explicitly, for example
`pip install -e "pkgs/tabular[experimental]"`. Do not add them to base runtime
requirements or default candidates.

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
`model_selector=ensemble` resolves the ensemble artifact from `build_ensemble`.
Supported model names such as `linear` or `ridge` resolve the matching
`train_<model>` artifact.

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
- ensemble-specific templates
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
| stages | `MLPlatform/Dev/Runs/Tabular/Stages` |
| tasks | `MLPlatform/Dev/Runs/Tabular/Tasks` |
| experiments | `MLPlatform/Dev/Experiments/Tabular` |

Runtime naming:

- `pipeline/tabular_train_pipeline/<run_name>`
- `stage/preprocess_features/<run_name>`
- `stage/train_<model>/<run_name>`
- `stage/build_ensemble/<run_name>`
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

Keep UI parameters grouped only under:

- `Input`
- `Run`
- `Model`
- `Output`

Do not add model-specific, ensemble-specific, optimization-specific, or
dataset-specific templates to reduce UI choices. Use `Model/candidates`,
`Model/name`, and stage overrides instead.

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
| `Model/candidates` | optional | optional | JSON array. Supported models are defaults; experimental models must be explicit. |
| `Model/model_params_by_name` | optional | optional | JSON object keyed by model name. |
| `Model/evaluation_metrics` | optional | optional | JSON array or comma-separated metric names. |
| `Model/selection_metric` | optional | optional | `rmse`, `mae`, or `r2`; used for leaderboard selection. |
| `Model/ensemble_*` | optional | optional | Controls `mean_topk` / `weighted` ensemble. |
| `Output/report_plots` | optional | optional | Set false to skip ClearML plot media reporting. |

Future inference UI parameters, if still present in code, must be documented as
future or experimental rather than primary:

- `Model/model_artifact_url`
- `Model/clearml_model_id`

## Artifact Policy

Training pipeline artifacts:

- `preprocess_bundle`
- `feature_spec.json`
- `feature_summary.json`
- model artifacts
- `model_refs.json`
- validation predictions
- `metrics_by_model.json`
- `leaderboard.csv`
- `best_model.json`
- `ensemble_info.json`
- ensemble artifact
- `evaluation_report.json`
- `evaluation_predictions.csv`
- `metrics.json`
- `manifest.json`

ClearML result display:

- scalar metrics for each `train_<model>` stage
- `metrics_by_model/rmse`, `metrics_by_model/mae`, and `metrics_by_model/r2`
  scalar series by model
- `best_model` and `ensemble` scalar summaries when available
- table views for `leaderboard.csv`, `evaluation_predictions.csv`, and
  `predictions.csv`
- lightweight `prediction_vs_actual`, `residual_histogram`, and
  `metrics_by_model_bar` plot artifacts

Inference artifacts:

- `predictions.csv`
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
