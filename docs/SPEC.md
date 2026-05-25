# Specification

## Purpose

`ml_platform` manages small tabular regression runs locally and through ClearML while keeping reusable ML logic ClearML-free.

The V1 product surface supports:

- local train, eval, infer, and train -> eval -> infer pipeline
- local tabular 1D output task
- ClearML template tasks for train, eval, infer, and pipeline controller
- minimal ClearML Agent deploy manifests
- smoke and boundary tests
- official tabular scalar regression models: `linear`, `ridge`, `random_forest`, and `gradient_boosting`
- V1.1 single-model extensions: `lasso`, `elasticnet`, `extra_trees`, `knn`, `svr`, and `mlp`
- V1.2 `mean_topk` and `weighted` ensembles on top of comparison mode
- V1.3 standardized batch inference output for model, best-model, and ensemble artifacts

The four official models are verified for local train/eval/infer/pipeline,
ClearML task train/eval/infer, and ClearML train -> eval -> infer pipeline
execution. `scikit-learn` is a required V1 runtime dependency because it
provides `random_forest` and `gradient_boosting`. Train supports a small
`model.candidates` comparison mode that writes `leaderboard.csv`, records a
comparison summary in `metrics.json`, and saves only the best model artifact.
Broader ensemble workflows such as train_ensemble_full, stacking,
LightGBM/XGBoost/CatBoost, advanced plots, diagnostics, all-model pipeline DAGs,
and separate runtime leaderboard tasks are future scope. V1.1 excludes
`gaussian_process` because it needs a separate stability and runtime gate.
V1.2 includes `mean_topk` and deterministic validation-metric `weighted`
ensemble. Stacking remains future scope.
V1.3 inference remains batch table inference only. It does not add online
serving, optimization, streaming readers, or a new template.

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
Model/ensemble_enabled
Model/ensemble_method
Model/ensemble_top_k
Model/artifact_path
Model/feature_preset

Output/prediction_name
```

Queue selection is profile and Agent configuration, not a UI parameter.

Templates are task-type based, not model-specific. Keep the four templates:
train, eval, infer, and pipeline. Use `Model/name` and `Model/params` for single
model execution. Use `Model/candidates` as a JSON list of model names and
`Model/selection_metric` for comparison mode. In comparison mode, `Model/params`
may be a JSON object keyed by model name.

Example:

```json
{
  "Model/candidates": "[\"linear\", \"ridge\", \"random_forest\"]",
  "Model/params": "{\"ridge\":{\"alpha\":1.0},\"random_forest\":{\"n_estimators\":50,\"random_state\":42,\"n_jobs\":1}}"
}
```

The same parameter surface is used for V1.1 sklearn models. Do not add
model-specific templates or ClearML adapter branches for `lasso`, `elasticnet`,
`extra_trees`, `knn`, `svr`, or `mlp`.

Use the flat `Model/ensemble_*` parameters only with comparison mode. Local
config remains nested under `model.ensemble`. Supported methods are `mean_topk`
and `weighted`. The V1.2 supported ClearML shape is:

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
prediction_run_id
```

These appended column names are reserved in inference input tables. The ClearML
artifact key is `predictions`; the physical file name is controlled by
`output.prediction_name` or `Output/prediction_name`.

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
