# Specification

## Purpose

`ml_platform` manages small tabular regression runs locally and through ClearML while keeping reusable ML logic ClearML-free.

The current product surface supports:

- local train, eval, infer, and train -> eval -> infer pipeline
- local tabular 1D output task
- ClearML template tasks for train, eval, infer, and pipeline controller
- minimal ClearML Agent deploy manifests
- smoke and boundary tests

## Boundaries

```text
scripts/local_run.py -> pkgs
clearml/app.py      -> clearml/adapter.py -> pkgs
clearml/pipelines.py -> ClearML PipelineController

pkgs/core    -> pandas, pyyaml, stdlib
pkgs/tabular -> pkgs/core, pandas, numpy, optional sklearn models
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
Model/artifact_path
Model/feature_preset

Output/prediction_name
```

Queue selection is profile and Agent configuration, not a UI parameter.

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
    predictions.csv

  latest_train/
    model.joblib
    model_info.json

  latest/
    latest completed task copy
```

`latest_train` is the default model lookup for eval and infer. It is a copied directory rather than a symlink for Windows, ClearML Agent, and mounted volume compatibility.

## Extension Points

- Add models in `pkgs/tabular/src/ml_platform_tabular/models.py`.
- Add feature presets in `pkgs/tabular/src/ml_platform_tabular/features.py`.
- Add metrics in `pkgs/tabular/src/ml_platform_tabular/metrics.py`.
- Add small tabular analysis tasks in `pkgs/tabular/src/ml_platform_tabular/`.
- Change ClearML parameter mapping in `clearml/adapter.py`.
- Change ClearML reports in `clearml/reports.py`.
- Change template sync in `clearml/templates.py`.
- Change Agent runtime in `deploy/`.

Add an abstraction only after at least two concrete implementations need it.
