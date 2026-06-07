# Productization Phases

Each phase must end with local smoke runs and tests passing. Keep the product small and operational.
This file is phase history. Current supported, experimental, future, and
discarded scope is defined in `docs/SPEC.md`.
Historical verification records are evidence for past flows, not the current
product specification.
Use `verification/README.md` to decide whether a record is current product
evidence, experimental evidence, or historical compatibility evidence.

## Phase 0: Repo Acceptance

Goal: make `ml_platform/` the product repo and keep legacy repos reference-only.

Done:

- repo initialized under `ml_platform/`
- local train/eval/infer and simple full-run compatibility flow accepted
- tests pass
- ignored data, outputs, virtualenvs, and reference dirs stay out of git

## Phase 1: Local MVP

Goal: ClearML-free local tabular regression workflows.

Done:

- sample data generation
- local train/eval/infer
- local simple full-run compatibility flow: train -> eval -> infer
- model, metrics, predictions, config, and manifest outputs
- `latest_train` model lookup

## Phase 2: ClearML Task MVP

Goal: ClearML UI clone-run for train/eval/infer.

Done:

- ClearML SDK boundary under `clearml/`
- three task template definitions plus one Pipeline-tab draft
- UI parameters grouped as Input, Run, Model, Output
- local tests pass without ClearML installed

Verified for V1:

- real ClearML template sync
- train/eval/infer clone-run
- dataset ID resolution
- artifact upload visibility

## Phase 3: ClearML Simple Full-Run MVP

Goal: fixed ClearML compatibility flow: train -> eval -> infer.

Done:

- PipelineController code in `clearml/pipelines.py`
- three fixed steps
- train model artifact passed to eval/infer as `Model/artifact_path`
- local simple full-run orchestration remains in `pkgs/tabular/pipeline.py`

Verified for V1:

- compatibility Pipeline-tab draft run
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
- local train/eval/infer and simple full-run verification for all official models
- ClearML task and compatibility full-run verification for all official models
- train `model.candidates` comparison mode with `leaderboard.csv`
- three task templates plus one Pipeline-tab draft only; no model-specific templates

Deferred:

- legacy all-model pipeline recreation
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
- ClearML launch targets remain the same three task templates plus one Pipeline-tab draft

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
- eval, infer, and compatibility full-run continue to consume the `model` artifact

Deferred:

- stacking
- weight optimization
- train_ensemble_full
- ensemble-specific templates or pipeline DAGs

## V2.1 Scope

Goal: add minimal train-time hyperparameter search without adding heavy optimization frameworks.

Implemented:

- `grid` and `random` search inside `tabular_train`
- nested local `model.search` config
- flat ClearML `Model/search_*` parameters
- `optimization_trials.csv`
- `optimization_summary.json`
- `best_params.json`
- best params saved as the standard retrained `model.joblib`
- compatibility full-run continues to pass the train `model` artifact to eval/infer

Deferred:

- Optuna, Ray Tune, and Bayesian optimization
- per-trial ClearML child tasks
- optimize-specific templates
- per-trial model artifacts

## V2.2 Scope

Goal: make batch inference artifacts easier to use in operations without adding serving APIs.

Implemented:

- `model_artifact_id` in `predictions.csv`
- `prediction_schema_version`, model, input, and chunk metadata in manifest
- optional CSV chunked prediction via `output.chunk_size` / `Output/chunk_size`
- same infer path for single, best, ensemble, and optimized model artifacts

Deferred:

- online serving APIs
- streaming input readers
- parquet as a required output format
- inference-specific templates

## V2.3 Scope

Goal: make the compatibility Pipeline-tab full-run flow explicit without adding
templates or recreating legacy task trees.

Implemented:

- `run.pipeline_mode` / `Run/pipeline_mode`
- modes: `auto`, `single`, `compare`, `ensemble`, `optimize`
- Pipeline-tab input controls for train/eval/infer dataset files
- pipeline-level `Input/target_column` and `Input/id_columns`
- pipeline-level `Output/prediction_name` and `Output/chunk_size`
- compatibility ClearML graph remains train -> eval -> infer
- eval and infer continue to consume the train step's standard `model` artifact

Deferred:

- separate leaderboard, ensemble, or optimization pipeline nodes
- train_ensemble_full
- per-model or per-trial child tasks
- Optuna, Ray Tune, and stacking

## Phase A: Pipeline Vocabulary Cleanup

Goal: stop calling the compatibility `train -> eval -> infer` flow the official
training pipeline.

Implemented:

- official training pipeline definition documented as
  `preprocess_features -> train_<model>* -> build_ensemble optional -> evaluate_models`
- inference documented as a separate `tabular_infer_template` task
- `tabular_pipeline_template` and `config/tasks/tabular_pipeline.yaml`
  documented as deprecated compatibility full-run entrypoints
- historical verification documented as evidence, not current specification

Deferred:

- local stage-based training pipeline
- ClearML stage graph using `tabular_stage_template`
- inference model reference resolution from training pipeline artifacts

## Phase B: Local Training Pipeline

Goal: implement the correct training pipeline locally without ClearML.

Implemented:

- `config/tasks/tabular_pipeline.yaml` now describes the local training pipeline
- local graph:
  `preprocess_features -> train_<model>* -> build_ensemble optional -> evaluate_models`
- stage directories for preprocessing, per-model training, ensemble, and
  evaluation
- artifacts for `preprocess_bundle`, `feature_spec.json`, per-model artifacts,
  `leaderboard.csv`, `best_model.json`, `best_model.joblib`,
  `evaluation_report.json`, `metrics.json`, and `manifest.json`
- inference intentionally removed from local training pipeline execution

Deferred:

- stage-based optimization
- inference model reference resolution from training pipeline artifacts

## Phase C: ClearML Stage-Based Training Pipeline

Goal: make the correct training pipeline visible in the ClearML Pipeline tab.

Implemented:

- internal `tabular_stage_template`
- user-facing Pipeline-tab drafts:
  `tabular_train_pipeline_template`, `tabular_train_full_pipeline_template`,
  and `tabular_train_full_ensemble_pipeline_template`
- ClearML graph:
  `preprocess_features -> train_<model>* -> build_ensemble optional -> evaluate_models`
- JSON stage refs for preprocess, per-model model artifacts, optional ensemble,
  and evaluation
- `tabular_train_template`, `tabular_eval_template`, and
  `tabular_pipeline_template` isolated as deprecated compatibility targets

Deferred:

- remote promotion of ClearML stage-based training pipelines to supported
- inference model reference resolution from training pipeline artifacts

## Phase D: Inference Model Reference

Goal: complete inference as a separate `tabular_infer_template` task, not a
training pipeline stage.

Implemented:

- `Model/source_type` support for `task_id`, `artifact_url`,
  `clearml_model_id`, and `local_path`
- `Model/model_selector` support for `best`, `ensemble`, and model names
- Pipeline controller task id and direct stage task id resolution
- local inference from `latest_training_pipeline` best/ensemble artifacts

Deferred:

- inference pipeline
- online serving
- richer metadata recovery from ClearML Model registry

## Phase E: Stage-Based Optimization Pipeline

Goal: treat optimization as a pipeline shape instead of hiding it inside train.

Implemented:

- local optimization graph:
  `preprocess_features -> search_trials -> retrain_best -> evaluate_best`
- ClearML dry-run graph for the same stage shape through `tabular_stage_template`
- `grid` and `random` search only
- artifacts: `optimization_trials.csv`, `optimization_summary.json`,
  `best_params.json`, retrained `model.joblib`, `best_model.joblib`,
  `evaluation_report.json`, `metrics.json`, and `manifest.json`
- no optimize-specific template and no per-trial child tasks

Deferred:

- ClearML remote verification and promotion decision
- Optuna, Ray Tune, Bayesian search, and per-trial ClearML child tasks
- combining search with ensemble
