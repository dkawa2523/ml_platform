# Productization Phases

Each phase must end with local smoke runs and tests passing. Keep the product small and operational.

## Phase 0: Repo Acceptance

Goal: make `ml_platform/` the product repo and keep legacy repos reference-only.

Done:

- repo initialized under `ml_platform/`
- local train/eval/infer/pipeline accepted
- tests pass
- ignored data, outputs, virtualenvs, and reference dirs stay out of git

## Phase 1: Local MVP

Goal: ClearML-free local tabular regression workflows.

Done:

- sample data generation
- local train/eval/infer
- local train -> eval -> infer pipeline
- model, metrics, predictions, config, and manifest outputs
- `latest_train` model lookup

## Phase 2: ClearML Task MVP

Goal: ClearML UI clone-run for train/eval/infer.

Done:

- ClearML SDK boundary under `clearml/`
- four template definitions
- UI parameters grouped as Input, Run, Model, Output
- local tests pass without ClearML installed

Verified for V1:

- real ClearML template sync
- train/eval/infer clone-run
- dataset ID resolution
- artifact upload visibility

## Phase 3: ClearML Pipeline MVP

Goal: fixed ClearML pipeline: train -> eval -> infer.

Done:

- PipelineController code in `clearml/pipelines.py`
- three fixed steps
- train model artifact passed to eval/infer as `Model/artifact_path`
- local pipeline remains in `pkgs/tabular/pipeline.py`

Verified for V1:

- pipeline template clone-run
- model artifact handoff on the dev server
- Agent queue behavior

## Phase 4: Deploy / Agent Runtime

Goal: minimal Kubernetes runtime for ClearML Agent.

Done:

- Agent Dockerfile
- base Deployment, ConfigMap, PVC, Secret example
- dev and prod overlays
- deploy README with operator checklist

Needs environment validation:

- real image registry and tag
- namespace and storage class
- ClearML credentials Secret
- Agent visible in ClearML Workers / Queues

## Phase 5: Selective Legacy Feature Reimplementation

Goal: reimplement only useful legacy features in the current boundaries.

Done:

- regression metrics support `mae`, `rmse`, `r2`, and optional `mse`
- metric selection via `metrics.names`

Deferred:

- richer preprocessing
- schema artifacts
- ClearML dataset registration
- table/plot reporting improvements

## Phase 6: Minimal Product Hardening

Goal: prepare for v1 handoff without adding heavy process.

Tasks:

- keep README, handoff, and spec current
- keep CI local-only
- remove stale docs and unsupported config keys
- keep requirements focused on V1 runtime needs
- keep tests small and useful

## Phase 7: Future Expansion

Goal: add new analysis content without breaking scalar regression or adding unused abstractions.

Done:

- first local `tabular_1d_output` task
- runner registration consolidated through the lazy registry
- ClearML template count unchanged

Deferred:

- tabular 2D output
- distribution modes
- optimization
- new domain packages until there is a clear second domain

## V1 Scope

Goal: verify multiple tabular scalar regression models across local and ClearML execution.

Verified:

- official models: `linear`, `ridge`, `random_forest`, `gradient_boosting`
- `scikit-learn` as a runtime dependency
- local train/eval/infer/pipeline verification for all official models
- ClearML task and pipeline verification for all official models
- train `model.candidates` comparison mode with `leaderboard.csv`
- four task-type ClearML templates only; no model-specific templates

Deferred:

- all-model pipeline DAGs
- runtime leaderboard tasks
- ensemble, stacking, and weighted ensemble
- LightGBM, XGBoost, CatBoost, and TabPFN
- train_ensemble_full
- advanced plots and diagnostics

## V1.1 Scope

Goal: add lightweight sklearn single-model regressors without changing template or config shape.

Implemented:

- `lasso`
- `elasticnet`
- `extra_trees`
- `knn`
- `svr`
- `mlp`
- model switching remains `Model/name` plus `Model/params`
- ClearML templates remain the same four task-type templates

Deferred:

- `gaussian_process`
- LightGBM, XGBoost, CatBoost, and TabPFN
- ensemble, stacking, weighted ensemble, and train_ensemble_full
- model-specific task configs or templates

## V1.2 Scope

Goal: add the first ensemble mode without adding ensemble-specific templates.

Implemented:

- `mean_topk` ensemble over comparison-mode leaderboard results
- `weighted` ensemble with deterministic validation-metric weights
- flat ClearML `Model/ensemble_*` parameters plus nested local `model.ensemble`
- ensemble artifact saved as the standard `model.joblib`
- selected top-k base models saved under `base_models/`
- eval, infer, and pipeline continue to consume the `model` artifact

Deferred:

- stacking
- weight optimization
- train_ensemble_full
- ensemble-specific templates or pipeline DAGs
