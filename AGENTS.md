# Codex / Agent Development Charter

This repository is the product repository for `ml_platform`: a ClearML-based
machine learning execution platform. The current product domain is tabular
scalar regression, and the repository should stay open to future extensions such
as richer tabular outputs, distribution mode decomposition, optimization, and
additional analysis workflows.

The goal is not to freeze the product behind prohibitions. The goal is to make
it safe to extend. Add useful capabilities when they improve ClearML UX, DS
productivity, or architecture clarity, while preserving the boundaries below.

Legacy repositories are reference material only. Learn from them, but do not
reshape this repository to match them.

---

## 1. Product Mission

The product must serve two audiences.

### ClearML UI Users

Users who do not read code should be able to:

- select a ClearML Dataset
- configure understandable parameters
- run task or pipeline templates
- review metrics, artifacts, leaderboard, predictions, and pipeline graph
- understand results from ClearML UI

### Developers / Data Scientists / Architects

Developers should be able to:

- add or improve preprocessing, features, models, ensembles, metrics, reports,
  inference, and future optimization
- identify the right extension point without reading unrelated layers
- evolve ClearML UI behavior without leaking ClearML SDK dependencies into
  package code
- keep the platform maintainable by avoiding excessive helpers, diagnostics,
  tests, and docs

---

## 2. Safe Extension Principles

Prefer:

- clear product behavior over hidden workflow behavior
- explicit artifacts and manifests
- readable ClearML UI parameters
- local reproducibility before remote verification
- small functions that remove real duplication
- focused tests that protect product behavior and boundaries
- short docs that reflect the current product

Avoid:

- copying legacy repository structure
- creating broad frameworks before the product needs them
- adding helper, diagnostics, contract, or test sprawl
- making scripts contain business logic
- making ClearML-specific behavior a dependency of `pkgs`
- multiplying templates when parameters or stages can express the difference

---

## 3. Repository Boundaries

### `pkgs/core`

Shared ClearML-free utilities: config loading, IO, result objects, artifact
helpers, registry utilities, and manifest helpers.

Keep out: ClearML SDK imports, PipelineController, Dataset, Logger, tabular
training logic, and model-specific business logic.

### `pkgs/tabular`

ClearML-free tabular ML logic: data loading, preprocessing, feature engineering,
model building, training, ensemble building, evaluation, inference, metrics, and
artifact creation.

Keep out: ClearML imports, PipelineController, Task, Dataset, Logger,
StorageManager, and ClearML UI parameter handling.

### `clearml/`

ClearML integration boundary: Task initialization, Dataset resolution, parameter
mapping, artifact reporting, PipelineController, template sync, and ClearML
task / pipeline entrypoints.

Keep out: model implementation, preprocessing implementation, feature
engineering implementation, training logic, evaluation logic, inference logic,
and ensemble math.

### `scripts/`

Wrappers only: local entrypoints, template sync entrypoints, artifact inspection,
and sample data generation. Business logic belongs in `pkgs` or `clearml/`.

### `config/`

Use the two primary axes:

```text
config/tasks
config/profiles
```

Task configs describe what to run. Profile configs describe where to run.
Avoid model-specific or dataset-specific task configs as primary product
entrypoints.

### `deploy/`

Deployment support only: Agent runtime assumptions, container/storage manifests,
and minimal deployment notes. No training or inference logic.

---

## 4. Product Flow Rules

The training pipeline is not:

```text
train -> eval -> infer
```

The official tabular scalar regression training pipeline is:

```text
preprocess_features
  -> train_<model>*
  -> build_ensemble_<method>*   # or one build_ensembles stage
  -> evaluate_models
```

The implementation may use a single `build_ensembles` stage when that keeps the
graph clearer. What matters is that multiple model and ensemble results are
visible and comparable through leaderboard, metrics, artifacts, and manifests.

Inference remains a separate task flow:

```text
source_task_id + model_selector
or local_model_path
-> inference dataset
-> feature align
-> predict
-> predictions.csv
```

Do not mix inference into the training pipeline unless `docs/SPEC.md` explicitly
introduces an inference pipeline.

Optimization is extensible future product scope. Add it only when SPEC promotes
the workflow and verification evidence is planned.

---

## 5. Template Policy

Current user-facing templates:

- `tabular_train_pipeline_template`
- `tabular_infer_template`

Current internal template:

- `tabular_stage_template`

Default sync should expose only the current product templates unless SPEC
promotes another entrypoint.

Allowed extension: add models, ensemble methods, metrics, plots, and UI
parameters through config, stage parameters, and package extension points.

Avoid template sprawl:

- do not create model-specific templates
- do not create dataset-specific templates
- do not create one template per ensemble method
- do not revive legacy `tabular_pipeline_template` as a current entrypoint

`tabular_stage_template` is for PipelineController steps. Users should not clone
it directly for normal product runs.

---

## 6. Current Scope

Primary product scope:

- `tabular_train_pipeline_template`
- `tabular_infer_template`
- `tabular_stage_template`
- `preprocess_features`
- `train_model` / `train_<model>*`
- `build_ensemble_<method>*` or `build_ensembles`
- `evaluate_models`
- `leaderboard.csv`
- `best_model.json`
- ensemble artifacts and `ensemble_info.json`
- `evaluation_report.json`
- `evaluation_predictions.csv`
- `predictions.csv`

Supported tabular regression models:

- `linear`
- `ridge`
- `lasso`
- `elasticnet`
- `random_forest`
- `extra_trees`
- `gradient_boosting`
- `lightgbm`
- `xgboost`
- `catboost`

`linear`, `ridge`, `lasso`, `elasticnet`, `random_forest`, `extra_trees`, and
`gradient_boosting` must run with the normal runtime dependencies.
`lightgbm`, `xgboost`, and `catboost` are supported optional-dependency models:
they must not become required runtime dependencies. If the dependency is missing
and the user selects that model, raise a clear error. Missing optional
dependencies must never break dependency-free model runs.

Portable default candidates may remain dependency-free models only. ClearML
users select additional supported optional models through `Model/candidates`
when their Agent image includes the dependency.

Out of scope for now:

- `knn`
- `svr`
- `mlp`
- `gaussian_process`
- `tabpfn`

Future scope:

- optimization pipeline
- `search_trials`, `retrain_best`, `evaluate_best`
- `artifact_url` / `clearml_model_id` as primary inference sources
- stacking
- Optuna / Ray Tune
- per-trial ClearML child tasks
- online serving
- tabular 1D/2D productization
- distribution mode decomposition

---

## 7. Ensemble Policy

Ensemble is an extensible product area. Do not limit the product to one method.
Support multiple methods when that improves comparison and UI value.

Current or near-term methods:

- `mean_topk`
- `weighted`
- `median`

Future method:

- `stacking`

A training run may specify multiple ensemble methods, for example:

```yaml
ensemble:
  methods:
    - mean_topk
    - weighted
    - median
```

Each ensemble result should be visible in leaderboard, metrics, artifacts, and
evaluation reports.

---

## 8. ClearML UI Policy

ClearML UI users must be able to understand what happened without reading code.

Parameter groups are not fixed to four categories. Use the smallest set that is
clear. These semantic groups are allowed when they improve UI readability:

- `Input`
- `Split`
- `Features`
- `Models`
- `Ensemble`
- `Evaluation`
- `Output`
- `Run`

Do not add groups just to mirror internal code. Add them when they make
preprocessing, model selection, ensemble configuration, or evaluation easier for
ClearML UI users.

The training Pipeline UI should make product-level preprocessing and feature
choices visible. Do not hide these behind developer-only config if users need to
run the product from ClearML:

- `Split/valid_size`
- `Features/preset`
- `Features/params`
- `Input/feature_columns`
- `Input/id_columns`
- `Models/candidates`
- `Models/model_params_by_name`
- `Ensemble/methods`
- `Evaluation/metrics`
- `Evaluation/selection_metric`

A training pipeline run should make these visible:

- pipeline controller task
- preprocess stage
- `train_<model>` stages
- ensemble stage or `build_ensemble_<method>` stages
- evaluate stage
- scalar metrics
- leaderboard table/artifact
- evaluation artifacts
- prediction-vs-actual plot
- residual histogram
- final manifest

If a run succeeds technically but users cannot understand the results in ClearML
UI, the product behavior is incomplete.

---

## 9. Reference Repositories

Legacy repositories may exist under `_reference_repos/` or `reference_repos/`.

- Read them to understand features and product intent.
- Do not import from them.
- Do not bulk copy source, docs, tests, helpers, or directory layout.
- Reimplement only the small behavior needed inside current repository
  boundaries.

---

## 10. Required Checks

Run the narrow checks that match the change. For product-flow changes, prefer:

```powershell
python scripts/make_sample_data.py
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml
python scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

Boundary checks:

```powershell
rg -n "from clearml|import clearml|PipelineController|StorageManager" pkgs/core pkgs/tabular
rg -n "reference_repos|Plartform_pipe|table_analysis" pkgs clearml scripts config tests
```

---

## 11. Change Style

- Prefer product-facing improvements over defensive bureaucracy.
- Reuse existing functions before adding new helpers.
- Keep docs short and current.
- Keep `docs/SPEC.md` as the product specification and
  `docs/CLEARML_UI_SPEC.md` as the ClearML screen-level operation contract.
- Keep tests focused on smoke behavior, result visibility, and boundaries.
- Do not add real ClearML server calls to normal pytest or CI.
- Keep optional dependencies optional.
