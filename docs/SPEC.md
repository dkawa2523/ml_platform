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

Compatibility or future utilities may remain in `config/tasks`, but they are
not product entrypoints and must not be synced as user-facing ClearML templates.

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
- `recommendation.json`
- `decision_summary.md` / `decision_summary.json`
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
- `prediction_summary.csv`
- `prediction_preview.csv`
- `source_summary.csv`
- `prediction_distribution_histogram.png`
- `manifest.json`

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
`clearml/`. `scripts/` are wrappers. Config remains split between task YAML and
profile YAML.

Do not add model-specific, dataset-specific, optimization-specific, or
ensemble-specific templates. Add product behavior through model candidates,
ensemble methods, stage overrides, and reporting.
