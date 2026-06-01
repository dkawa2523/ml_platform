# Specification

## Purpose

`ml_platform` manages small tabular regression runs locally and through ClearML while keeping reusable ML logic ClearML-free.

## Product Scope

This section is the canonical current product scope. Historical phase notes live
in `docs/PRODUCTIZATION_PHASES.md`.

### Supported

Supported means the behavior is implemented, exposed through the intended local
or ClearML interface, and has local plus ClearML remote verification evidence.

- tabular scalar regression local train, eval, infer, and train -> eval -> infer pipeline
- ClearML UI train, eval, infer, and pipeline execution
- four ClearML launch targets: train, eval, infer, and Pipeline-tab pipeline
- official models: `linear`, `ridge`, `random_forest`, and `gradient_boosting`
- comparison mode with `model.candidates` / `Model/candidates`
- `leaderboard.csv` and best model selection
- `mean_topk` and `weighted` ensemble saved as the standard model artifact
- train-time `grid` and `random` hyperparameter search
- standardized batch inference output for model, best-model, ensemble, and optimized artifacts
- optional CSV chunked prediction/write via `output.chunk_size` / `Output/chunk_size`
- metrics, artifacts, predictions, ClearML Dataset id/file handling, and minimal Agent deploy manifests

### Experimental

Experimental means the behavior is implemented but remote verification is
limited, dependency/runtime behavior has caveats, or the API/config may still
change before promotion to supported.

- additional sklearn regressors: `lasso`, `elasticnet`, `extra_trees`, `knn`, `svr`, and `mlp`
- local `tabular_1d_output` utility
- model-specific runtime caveats such as convergence warnings or data-size sensitivity

Experimental features must use the existing task/profile config shape and the
same ClearML launch targets. Do not mark them supported until local and ClearML
remote evidence is documented.

### Future

- LightGBM, XGBoost, and CatBoost
- Optuna, Ray Tune, Bayesian search, and advanced optimization
- stacking and weight optimization
- per-trial ClearML child tasks
- advanced plots and reporting
- online serving APIs
- 1D / 2D productization
- distribution mode decomposition
- richer preprocessing and schema validation

### Discarded

- legacy full parity as a goal
- excessive contract docs and checklist pages
- broad diagnostics helpers
- old adapter splits
- live cleanup operations
- model-specific ClearML templates
- dataset-specific ClearML templates
- legacy repo directory, config, helper, test, or docs recreation

The four official models are verified for local train/eval/infer/pipeline,
ClearML task train/eval/infer, and ClearML train -> eval -> infer pipeline
execution. `scikit-learn` is a required runtime dependency because it provides
`random_forest` and `gradient_boosting`. Train supports a small
`model.candidates` comparison mode that writes `leaderboard.csv`, records a
comparison summary in `metrics.json`, and saves only the best model artifact.
This repo does not target full legacy parity: train_ensemble_full, all-model
pipeline DAGs, separate runtime leaderboard tasks, broad diagnostics, and
template proliferation are not product scope. `mean_topk` and deterministic
validation-metric `weighted` ensemble are supported; stacking remains future
scope. Train-time hyperparameter search is limited to `grid` and `random`; it
does not add
Optuna, Ray Tune, ClearML child tasks, or an optimize template.
Inference remains batch table inference only. It includes CSV chunked
prediction/write support, but not streaming readers, online serving, parquet as
a required format, or a new template.

## Boundaries

```text
scripts/local_run.py -> pkgs
clearml/app.py      -> clearml/adapter.py -> pkgs
clearml/pipelines.py -> ClearML PipelineController

pkgs/core    -> pandas, pyyaml, stdlib
pkgs/tabular -> pkgs/core, pandas, numpy, scikit-learn
```

Forbidden dependencies:

```text
pkgs -> clearml
pkgs -> deploy
pkgs -> scripts
```

## Config

Config uses two axes:

```text
config/tasks    what to run
config/profiles where to run
```

Task config values override profile values. CLI overrides are applied last.

Important task sections:

- `task`
- `run`
- `data`
- `split`
- `metrics`
- `features`
- `model`
- `output`

`metrics.names` is task config only. It is not a ClearML UI parameter.

## ClearML UI Parameters

The ClearML UI parameter surface is intentionally small and grouped only as:

```text
Input
Run
Model
Output
```

Current parameters:

```text
Input/local_path
Input/clearml_dataset_id
Input/dataset_file
Input/target_column
Input/feature_columns
Input/id_columns

Run/task
Run/name
Run/seed

Model/name
Model/params
Model/candidates
Model/selection_metric
Model/search_enabled
Model/search_method
Model/search_space
Model/max_trials
Model/ensemble_enabled
Model/ensemble_method
Model/ensemble_top_k
Model/artifact_path
Model/feature_preset

Output/prediction_name
Output/chunk_size
```

Queue selection is profile and Agent configuration, not a UI parameter.

ClearML launch targets are task-type based, not model-specific. Keep three
clone-run task templates for train, eval, and infer plus one Pipeline-tab draft
for the fixed train -> eval -> infer pipeline. Use `Model/name` and
`Model/params` for single model execution. Use `Model/candidates` as a JSON list
of model names and `Model/selection_metric` for comparison mode. In comparison
mode, `Model/params` may be a JSON object keyed by model name.

Example:

```json
{
  "Model/candidates": "[\"linear\", \"ridge\", \"random_forest\"]",
  "Model/params": "{\"ridge\":{\"alpha\":1.0},\"random_forest\":{\"n_estimators\":50,\"random_state\":42,\"n_jobs\":1}}"
}
```

The same parameter surface is used for experimental sklearn models. Do not add
model-specific templates or ClearML adapter branches for `lasso`, `elasticnet`,
`extra_trees`, `knn`, `svr`, or `mlp`.

Use the flat `Model/ensemble_*` parameters only with comparison mode. Local
config remains nested under `model.ensemble`. Supported methods are `mean_topk`
and `weighted`. The supported ClearML shape is:

```json
{
  "Model/ensemble_enabled": true,
  "Model/ensemble_method": "mean_topk",
  "Model/ensemble_top_k": 3
}
```

When enabled, train saves `model.joblib` as an ensemble artifact and stores the
selected top-k base models under `base_models/`. `weighted` derives normalized
weights from `Model/selection_metric`; it does not run optimization.

Use `Model/search_*` parameters only for train-time hyperparameter search.
Supported methods are `grid` and `random`. Search writes
`optimization_trials.csv`, `optimization_summary.json`, and `best_params.json`,
then saves the best params as the standard retrained `model.joblib` artifact.
`Model/search_space` is a JSON object string: direct parameter names for
single-model search, or a model-keyed object when `Model/candidates` is used.

## Artifacts

Typical local outputs:

```text
outputs/
  <run_name>_<timestamp>/
    config.yaml
    metrics.json
    manifest.json
    model.joblib
    model_info.json
    leaderboard.csv
    optimization_trials.csv
    optimization_summary.json
    best_params.json
    ensemble_predictions.csv
    predictions.csv

  latest_train/
    model.joblib
    model_info.json

  latest/
    latest completed task copy
```

`latest_train` is the default model lookup for eval and infer. It is a copied directory rather than a symlink for Windows, ClearML Agent, and mounted volume compatibility.

Inference `predictions.csv` preserves the input columns and appends:

```text
prediction
model_name
artifact_kind
model_artifact_id
prediction_run_id
```

These appended column names are reserved in inference input tables. The ClearML
artifact key is `predictions`; the physical file name is controlled by
`output.prediction_name` or `Output/prediction_name`. `Output/chunk_size` is an
optional CSV inference control that chunks prediction and writing after the input
table has been loaded.

## Extension Points

- Add models in `pkgs/tabular/src/ml_platform_tabular/models.py`.
- Add feature presets in `pkgs/tabular/src/ml_platform_tabular/features.py`.
- Add metrics in `pkgs/tabular/src/ml_platform_tabular/metrics.py`.
- Use train `model.candidates` for small model comparison; do not add a template per model.
- Add small tabular analysis tasks in `pkgs/tabular/src/ml_platform_tabular/`.
- Change ClearML parameter mapping in `clearml/adapter.py`.
- Change ClearML reports in `clearml/reports.py`.
- Change template sync in `clearml/templates.py`.
- Change Agent runtime in `deploy/`.

Add an abstraction only after at least two concrete implementations need it.
