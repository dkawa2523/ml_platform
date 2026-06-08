# Codex / Agent Instructions

This repository is the product repository for `ml_platform`.

`ml_platform` is a ClearML-based machine learning execution platform. It supports local execution and ClearML-managed task / pipeline execution. The first production domain is tabular scalar regression, but the architecture must remain extensible to future domains such as tabular 1D/2D outputs, distribution mode decomposition, optimization, and other analysis workflows.

Legacy repositories are reference material only. Do not reshape this repository to match them.

---

## 1. Product Mission

The product must support two user types.

### ClearML UI users

Users who do not read code should be able to:

- select a ClearML Dataset
- configure parameters in ClearML UI
- run task or pipeline templates
- review metrics, artifacts, leaderboard, predictions, and pipeline graph
- understand results without opening source code

### Developers / data scientists / architects

Developers should be able to:

- understand the code structure quickly
- add or improve preprocessing
- add or improve feature engineering
- add or improve models
- add or improve ensemble logic
- add or improve evaluation
- add or improve inference
- add or improve optimization
- modify ClearML integration without breaking package logic
- maintain the platform without excessive contracts, helpers, tests, or docs

---

## 2. Product Principles

Prefer:

- simple product behavior
- clear directory responsibility
- small reusable functions
- explicit artifacts
- clear ClearML UI parameters
- local reproducibility
- minimal but useful tests
- short and current docs

Avoid:

- copying legacy repository structure
- excessive abstraction
- excessive helper layers
- excessive diagnostics
- excessive contract documents
- excessive tests
- model-specific ClearML templates
- dataset-specific ClearML templates
- hidden workflow behavior
- putting ClearML dependencies into package code

---

## 3. Repository Boundaries

### `pkgs/core`

Shared utilities only.

Allowed:

- config loading
- artifact helpers
- IO helpers
- result objects
- simple registry utilities
- common manifest helpers

Forbidden:

- ClearML SDK imports
- ClearML PipelineController
- ClearML Dataset
- ClearML Logger
- tabular-specific training logic
- model-specific business logic

### `pkgs/tabular`

ClearML-independent tabular ML logic.

Allowed:

- data loading
- preprocessing
- feature engineering
- model building
- model training
- ensemble building
- evaluation
- inference
- optimization utilities if not ClearML-specific
- artifact creation through core utilities

Forbidden:

- ClearML imports
- PipelineController
- ClearML Task
- ClearML Dataset
- ClearML Logger
- ClearML StorageManager
- ClearML-specific UI parameter handling as business logic

### `clearml/`

ClearML integration boundary.

Allowed:

- ClearML Task initialization
- ClearML Dataset resolution
- ClearML parameter mapping
- ClearML artifact reporting
- ClearML PipelineController
- ClearML template sync
- ClearML task / pipeline entrypoints

Forbidden:

- tabular model implementation
- preprocessing implementation
- feature engineering implementation
- training implementation
- evaluation implementation
- inference implementation
- ensemble business logic
- optimization business logic

### `scripts/`

Wrappers only.

Allowed:

- local command entrypoints
- template sync entrypoint
- artifact inspection wrappers
- sample data generation

Forbidden:

- training logic
- preprocessing logic
- model logic
- ensemble logic
- evaluation logic
- inference logic
- optimization logic
- ClearML pipeline business logic

### `config/`

Configuration uses two primary axes:

```text
config/tasks
config/profiles
```

Allowed:

- task configs that describe what to run
- profile configs that describe where to run
- small comments that clarify product scope

Forbidden:

- template proliferation through config files
- model-specific task configs as primary product entrypoints
- dataset-specific task configs as primary product entrypoints

### `deploy/`

Deployment support only.

Allowed:

- ClearML Agent runtime assumptions
- container and storage manifests
- minimal deployment notes

Forbidden:

- training logic
- inference logic
- hidden product workflow logic

---

## 4. Product Flow Rules

The training pipeline is **not**:

```text
train -> eval -> infer
```

The official tabular scalar regression training pipeline is:

```text
preprocess_features -> train_<model>* -> build_ensemble -> evaluate_models
```

Inference is a separate task flow:

```text
source_task_id + model_selector
or local_model_path
-> inference dataset
-> feature align
-> predict
-> predictions.csv
```

Do not mix inference into the training pipeline unless a future product decision
explicitly introduces an inference pipeline.

Optimization is future / experimental. Do not present
`search_trials -> retrain_best -> evaluate_best`, `model.search`, or
optimization-specific UI as the primary product flow unless the product scope in
`docs/SPEC.md` is updated with verification evidence.

---

## 5. Template Policy

Official user-facing templates:

- `tabular_train_pipeline_template`
- `tabular_infer_template`

Official internal template:

- `tabular_stage_template`

Only these templates should be synced by default.

Forbidden as primary product templates:

- model-specific templates
- ensemble-specific templates
- optimization-specific templates
- dataset-specific templates
- legacy `tabular_pipeline_template`
- `tabular_train_full_pipeline_template`
- `tabular_train_full_ensemble_pipeline_template`

`tabular_stage_template` is for PipelineController steps. Users should not clone
it directly as the normal product entrypoint.

---

## 6. Current Scope

Primary product scope:

- `tabular_train_pipeline_template`
- `tabular_infer_template`
- `tabular_stage_template`
- `preprocess_features`
- `train_model`
- `train_multiple_models`
- `build_ensemble`
- `evaluate_models`
- `leaderboard.csv`
- `best_model.json`
- ensemble artifact
- `evaluation_report.json`
- `predictions.csv`

Future / experimental scope:

- optimization pipeline
- `search_trials`
- `retrain_best`
- `evaluate_best`
- `artifact_url` inference source
- `clearml_model_id` inference source
- external model full pipeline
- Optuna / Ray Tune
- per-trial ClearML child tasks
- online serving
- tabular 1D/2D productization
- distribution mode decomposition

Do not promote future or experimental features into the primary ClearML UI flow
without explicit verification evidence and a product-scope update.

---

## 7. Reference Repositories

Legacy repositories may exist as sibling read-only material, usually under
`_reference_repos/` or `reference_repos/`.

- Read them only to understand features and product intent.
- Do not import from them.
- Do not bulk copy source, docs, tests, helpers, or directory layout.
- Reimplement only the small behavior needed inside the current repository
  boundaries.

---

## 8. Required Checks

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

## 9. Change Style

- Prefer small, product-facing fixes.
- Reuse existing functions before adding new helpers.
- Keep docs short and current.
- Keep tests focused on smoke behavior and boundaries.
- Do not add real ClearML server calls to normal pytest or CI.
- Keep optional dependencies optional.
