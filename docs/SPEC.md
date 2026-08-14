# Product Specification

`ml_platform` is a ClearML-based execution platform for tabular regression.
It supports both a scalar table and sparse target-specific tables that share
coordinate roles but may observe different coordinate sets. It must be usable
from ClearML UI and maintainable by data scientists extending features, models,
ensembles, metrics, plots, and reports.

Legacy repositories are reference-only material. This repo does not preserve
legacy layout or full parity.

## Training

Official graph:

```text
preprocess_features -> train_<model>* -> build_ensemble_<method>* -> evaluate_models
```

Package stage keys stay stable as `preprocess_features`, `train_model`,
`build_ensemble`, and `evaluate_models`. ClearML Pipeline step labels add model
or ensemble method suffixes, such as `train_ridge` and
`build_ensemble_weighted`, for operator readability.

Primary task configs:

- `config/tasks/tabular_pipeline.yaml`
- `config/tasks/tabular_stage.yaml`
- `config/tasks/tabular_infer.yaml`

Compatibility-only train/eval task configs are not part of the current product
surface.
Future/P2 items are tracked in `docs/ROADMAP.md` and should not appear as
half-enabled ClearML UI surfaces.

Training uses one holdout validation split. Supported `split.method` values are
`random`, `group`, `time`, and `fixed`. `random` keeps the seeded shuffle
behavior for scalar input. For target collections it assigns normalized
coordinate tuples deterministically, so a coordinate shared by multiple
targets cannot cross the split. `group` keeps all rows for the same
`split.group_column` on one side of the split. `time` sorts by
`split.time_column` and uses the latest
timestamp boundary closest to `split.valid_size` for validation without
splitting equal timestamps across train and validation. `fixed` uses
`split.valid_filter_column == split.valid_filter_value` as validation rows.
The active group/time/fixed control column is split metadata, not a model
feature: it is excluded from automatic feature selection and rejected in an
explicit `data.feature_columns` list. Derive a separate prediction-time feature
when the underlying group or time information is intentionally needed.
K-fold CV, nested CV, HPO-driven splitting, and external validation files are
future scope. `external_valid_file`, k-fold, nested CV, and `group_kfold` are
not implemented in this release.

## Data Inputs

Scalar input uses `data.local_path` plus `data.target_column`.

A sparse target collection uses a dataset directory plus
`data.source_manifest`; `data.target_column` must then be empty. The manifest
maps stable coordinate roles and the observed value role to source column
names:

```yaml
schema_version: 1
defaults:
  columns: {x: x, y: y, z: z, time: t, value: f}
targets:
  - name: temperature
    file: temperature.csv
  - name: pressure
    file: pressure.csv
    columns: {time: timestamp, value: pressure}
```

Each source remains sparse. The loader never outer-joins targets, creates
missing grid rows, imputes observed values, or interpolates coordinates.
Coordinate cells and observed values must be present and finite, and duplicate
coordinates within one target are rejected. The internal logical form is one
row per observation with `__target__`, canonical coordinates, `__value__`, and
`__source_row__`.

## Models

Supported models:

```text
linear, ridge, lasso, elasticnet,
random_forest, extra_trees, gradient_boosting,
lightgbm, xgboost, catboost
```

`lightgbm`, `xgboost`, and `catboost` require optional dependencies. They stay
out of package required dependencies and `requirements.txt`. ClearML templates
install those GBM packages into the remote execution venv. The profile's
`clearml.execution` block supplies one repository revision, image, and Python
binary for all templates; sync resolves the revision to an immutable commit.
Local or slim-image runs may override `model.candidates` to the dependency-free
subset.

Out-of-scope models:

```text
knn, svr, mlp, gaussian_process, tabpfn
```

HPO is not part of the current model flow. `Basic/quality_mode` applies fixed,
bounded parameter presets; it does not run search. Existing search-like config
guards may reject `model.search.enabled=true` as future/experimental, but no
ClearML HPO or optimization stage is implemented.

`run.seed` / `Run/seed` is the single random-seed contract for data splitting
and model construction. Model-specific `random_state` and `random_seed` values
are normalized to that value before training.

## Ensembles

Supported methods:

```text
mean_topk, weighted, median
```

One training run may build multiple ensemble methods. Each method must produce
metrics, prediction tables, one member table containing weights, and artifacts
that can be compared in `evaluate_models`.

For target collections, each model candidate owns one shared feature
transformer and one scalar regressor per target in a single
`TargetModelBundle`. Candidate and ClearML stage counts therefore do not grow
with target count. Ensemble methods continue to combine candidate predictions
row-wise and use one global candidate weight.

## Evaluation Outputs

`evaluate_models` is the comparison dashboard. It owns:

- `leaderboard.csv`
- `best_model.joblib`
- `model_info.json`
- `best_model.json`
- `evaluation_predictions.csv`
- `manifest.json`

`best_model.json` is the canonical inference decision artifact. It carries the
recommended `Model/source_type`, `Model/source_task_id`, and
`Model/model_selector`. `leaderboard.csv` is the single detailed comparison
table. ClearML PLOTS should focus on the leaderboard metric panel and best-model
prediction diagnostics.

Target-collection metrics are written in tidy form by target plus a
`__macro__` row. MAE, RMSE, and R2 remain visible per target. Cross-target
selection must use `skill`, `relative_rmse`, or macro R2, with the first two
calculated against each target's training-mean baseline and macro-averaged with
equal target weight.
Row-count-weighted micro metrics and plots that mix target units are not
produced.

## Inference

Official inference entrypoint: `tabular_infer_template`.

Primary sources:

- `source_task_id + model_selector`
- `local_model_path`

Selectors:

- `best`
- supported model name, for example `ridge`
- `ensemble`
- `ensemble:<method>`, for example `ensemble:median`

Inference outputs:

- `predictions.csv`
- `schema_check_summary.json` and `.csv`
- `prediction_summary.csv`
- `prediction_preview.csv`
- `prediction_distribution.png`
- `manifest.json`

Scalar `predictions.csv` is intentionally slim: it contains `row_index`,
configured or learned ID columns when present, and `prediction`.
Target-collection predictions additionally contain `target`,
canonical coordinate columns, and `source_row`, because these fields identify
the predicted field observation. Other feature columns are not copied.

`schema_check_summary` compares inference input columns with `model_info` and
the serialized estimator. Missing required features and invalid/non-finite
values in learned numeric roles fail the task; extra columns, missing ID
columns, and unseen categorical values are warnings.

Inference loads one supported table and predicts it as one batch. True
streaming input belongs in a separate future design if operational demand
requires it.

`manifest.json` records the model source, selector, resolved model name,
artifact kind, ensemble method, target column, and feature preset when known.

Drift and monitoring are not implemented. Future monitoring should build from
stored inference outputs such as `schema_check_summary`, `prediction_summary`,
and the run manifest, not from a separate service in the current release.

## P2 Roadmap Boundary

The following items are intentionally not implemented in the current release and
are tracked in `docs/ROADMAP.md`:

- HPO / hyperparameter optimization behind a small Basic-level control.
- Model Registry flow from `evaluate_models` best-model decisions to approved
  model registration.
- Drift / monitoring from accumulated inference summaries.
- Task Registry and joint tensor models for aligned 1D/2D outputs or mode
  decomposition. Sparse independent target bundles do not require a registry.
- `external_valid_file`, k-fold, nested CV, and `group_kfold`.

Do not expose these as user-facing ClearML parameters or templates until their
product flow is intentionally designed.

## ClearML Templates And Projects

User-facing templates:

- `tabular_train_pipeline_template`
- `tabular_infer_template`

Internal template:

- `tabular_stage_template`

Display names:

- `template/tabular_train_pipeline`
- `template/tabular_infer`
- `internal/tabular_stage`

Project layout is profile-driven:

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

Tags:

- `domain:tabular`
- `run_type:template|pipeline|stage|task`
- `user_facing:true` or `internal:true`
- `stage:<stage_name>`
- `model:<model_name>`
- `ensemble:<method>`

## Architecture

`pkgs/core` and `pkgs/tabular` are ClearML-free. ClearML SDK usage lives under
`clearml/`. `scripts/` are the preferred local operator entrypoints and wrap
package or ClearML operations entrypoints. Remote ClearML templates still execute
`clearml/app.py` and `clearml/pipelines.py` directly. Config remains split
between task YAML and profile YAML.

The top-level `clearml/` operations directory intentionally remains in place for
this release because synced templates reference those paths. Official SDK imports
must go through the adapter import helpers so the repo directory does not shadow
the external `clearml` package. A future rename should first add replacement
entrypoints, sync and verify templates against them, then remove the old paths
after existing Pipeline drafts are recreated or archived.

Do not add model-specific, dataset-specific, optimization-specific, or
ensemble-specific templates. Add product behavior through model candidates,
ensemble methods, stage overrides, and reporting.
