# Product Specification

`ml_platform` is a ClearML-based execution platform for tabular scalar
regression. It must be usable from ClearML UI and maintainable by data
scientists extending features, models, ensembles, metrics, plots, and reports.

Legacy repositories are reference-only material. This repo does not preserve
legacy layout or full parity.

## Training

Official graph:

```text
preprocess_features -> train_<model>* -> build_ensemble_<method>* -> evaluate_models
```

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
behavior. `group` keeps all rows for the same `split.group_column` on one side
of the split. `time` sorts by `split.time_column` and uses the latest
`split.valid_size` rows for validation. `fixed` uses
`split.valid_filter_column == split.valid_filter_value` as validation rows.
K-fold CV, nested CV, HPO-driven splitting, and external validation files are
future scope. `external_valid_file`, k-fold, nested CV, and `group_kfold` are
not implemented in this release.

## Models

Supported models:

```text
linear, ridge, lasso, elasticnet,
random_forest, extra_trees, gradient_boosting,
lightgbm, xgboost, catboost
```

`lightgbm`, `xgboost`, and `catboost` require optional dependencies. They stay
out of package required dependencies and `requirements.txt`. ClearML templates
install those GBM packages into the remote execution venv, and profiles still
reference `clearml.execution.image` so workers use the intended base image.
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

## Ensembles

Supported methods:

```text
mean_topk, weighted, median
```

One training run may build multiple ensemble methods. Each method must produce
metrics, prediction tables, member/weight tables when applicable, and artifacts
that can be compared in `evaluate_models`.

## Evaluation Outputs

`evaluate_models` is the comparison dashboard. It owns:

- `leaderboard.csv`
- `leaderboard_topk.csv`
- `leaderboard_decision_summary.csv`
- `best_vs_ensemble_summary.csv`
- `metrics_by_candidate.json` and `.csv`
- `best_model.json`
- `evaluation_report.json`
- `evaluation_predictions.csv`
- `candidate_predictions.csv`
- `decision_summary.md` / `decision_summary.json` as the canonical inference
  decision note
- `recommendation.json` as a compatibility machine-readable recommendation
- `manifest.json`

ClearML PLOTS should focus on readable leaderboard views: table, top-k score
bar, metric panel, Pareto scatter, top-k prediction-vs-actual, top-k residual
histogram, and top-k residual-vs-predicted. Full candidate predictions stay as
table/artifact evidence, not a noisy all-series plot.

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
- `source_summary.csv`
- `prediction_distribution_histogram.png`
- `manifest.json`

`predictions.csv` is intentionally slim: it contains `row_index`, configured
or learned ID columns when present, `prediction`, and lightweight model metadata.
It does not copy all input feature columns.

`schema_check_summary` compares inference input columns with the training
feature spec or model info. Missing required features fail the task; extra
columns, missing ID columns, and unseen categorical values are warnings.

`source_summary.csv` records the model source, selector, resolved model name,
artifact kind, ensemble method, target column, and feature preset when known.

Drift and monitoring are not implemented. Future monitoring should build from
stored inference outputs such as `schema_check_summary`, `prediction_summary`,
and `source_summary`, not from a separate service in the current release.

## P2 Roadmap Boundary

The following items are intentionally not implemented in the current release and
are tracked in `docs/ROADMAP.md`:

- HPO / hyperparameter optimization behind a small Basic-level control.
- Model Registry flow from `evaluate_models` recommendations to approved model
  registration.
- Drift / monitoring from accumulated inference summaries.
- Task Registry for non-scalar outputs such as 1D/2D output or mode
  decomposition.
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
