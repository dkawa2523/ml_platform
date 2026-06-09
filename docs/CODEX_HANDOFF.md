# Codex Handoff

This repo has V2 product scope for tabular scalar regression. Keep the implementation simple.

## Current State

- Local train/eval/infer tasks still exist for compatibility, but the primary
  product entrypoints are the training pipeline and inference task.
- Optimization remains future / experimental and is not a primary ClearML UI
  entrypoint.
- ClearML task entrypoint, adapter, reports, templates, and pipeline controller are implemented.
- ClearML SDK usage is contained under `clearml/`.
- `pkgs/core` and `pkgs/tabular` do not import ClearML.
- Deploy manifests provide a minimal ClearML Agent runtime.
- Tests are smoke and boundary oriented.
- Dependency-free supported regression models are `linear`, `ridge`, `lasso`,
  `elasticnet`, `random_forest`, `extra_trees`, and `gradient_boosting`.
- Supported optional-dependency regressors are `lightgbm`, `xgboost`, and
  `catboost`. They are not default candidates; install `pkgs/tabular[gbm]`
  or provide a ClearML Agent image with those packages before selecting them.
- `scikit-learn` is a required runtime dependency.
- Current verification evidence lives under `verification/training_pipeline/`
  and `verification/inference/`. Historical and future-reference evidence lives
  under `verification/_historical/`. Start with `verification/README.md`.
- Compatibility single-model tasks use `Model/name` and `Model/params`.
- Deprecated compatibility full-run evidence exists under verification history,
  but `Run/pipeline_mode` is not an official training pipeline mode.
- Comparison uses `Model/candidates` as a list of model names,
  `Model/model_params_by_name` as model-keyed JSON parameters,
  `Model/evaluation_metrics`, and `Model/selection_metric`; it writes
  `leaderboard.csv` and saves only the best model artifact.
- Ensemble uses `Model/ensemble_enabled`, `Model/ensemble_methods`, and `Model/ensemble_top_k` in the user-facing ClearML pipeline UI, while local config stays nested under `model.ensemble`. Supported methods are `mean_topk`, `weighted`, and `median`; `Model/ensemble_method` remains an internal/compatibility alias when `ensemble_methods` is absent.
- Primary inference uses `source_task_id + model_selector` or
  `local_model_path`. `artifact_url` and `clearml_model_id` remain
  future/experimental sources.

## Scope Rules

`docs/SPEC.md` is the source of truth for supported, experimental, future, and
discarded scope. Do not promote an experimental or future ClearML feature to
supported without local and ClearML remote verification evidence.

The official training pipeline definition is:

```text
preprocess_features -> train_<model>* -> build_ensemble_<method>* -> evaluate_models
```

`config/tasks/tabular_pipeline.yaml` and `pkgs/tabular.pipeline.run_pipeline()`
implement this graph locally. `tabular_train_pipeline_template` implements the
same graph through the internal `tabular_stage_template`. Each ClearML
`build_ensemble_<method>` node still runs the internal `build_ensemble` stage
with one method. The old
`tabular_pipeline_template` is deprecated and sync-excluded.

Inference is a separate `tabular_infer_template` task. Do not fold inference
into the training pipeline redesign.

## Required Local Check

```powershell
python scripts/make_sample_data.py
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml
python scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

## ClearML Dev Server Check

Before real sync:

- replace `repository` in `config/profiles/clearml-dev.yaml`
- confirm `branch` and `working_dir`
- confirm `queue`
- set `artifact_output_uri` if the server has no default artifact storage
- configure ClearML credentials outside the repo

Input data rules:

- Local runs use `data.local_path` or `Input/local_path`; `clearml_dataset_id` is not required.
- ClearML Agent runs should use `Input/clearml_dataset_id`. If the Dataset contains multiple files, set `Input/dataset_file`.
- `Input/local_path` is valid on an Agent only when the path exists inside the Agent container or mounted PVC. A host machine path is not assumed to exist inside the Agent.
- ClearML Dataset artifact URLs must be reachable from the Agent. Avoid host-only `localhost` URLs or host filesystem paths for Agent runs.
- In Docker or Kubernetes, use a Fileserver service DNS name, a cluster-internal URL, or an external URL that the Agent can reach.
- `artifact_output_uri` is only the destination for artifacts produced by the
  current task or pipeline run. It does not change where an existing ClearML
  Dataset is stored or whether the Dataset artifact URL is reachable.

Dry-run:

```powershell
python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
python clearml/pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
```

Real sync:

```powershell
python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml
```

ClearML project layout is profile-managed. The dev profile routes templates to
`MLPlatform/Dev/Templates/Tabular`, Pipeline-tab drafts/controllers to
`MLPlatform/Dev/Pipelines/Tabular`, preprocess stages to
`MLPlatform/Dev/Runs/Tabular/Preprocess`, train stages to
`MLPlatform/Dev/Runs/Tabular/Train`, ensemble stages to
`MLPlatform/Dev/Runs/Tabular/Ensemble`, evaluate stages to
`MLPlatform/Dev/Runs/Tabular/Evaluate`, standalone inference tasks to
`MLPlatform/Dev/Runs/Tabular/Infer`, and compatibility experiments to
`MLPlatform/Dev/Experiments/Tabular`. Legacy `stages` / `tasks` profile keys are
fallbacks only.

Current ClearML display names are:

- `template/tabular_train_pipeline`
- `template/tabular_infer`
- `internal/tabular_stage`

Old template/run names can remain visible on the ClearML server until a human
archives them. Do not delete or archive server tasks from repo automation.

PipelineController Agent capacity:

- Remote training pipeline execution needs enough worker slots on the execution
  queue for the controller and stage tasks. Alternatively, use separate
  controller and step queues.

Manual UI checks:

- Clone `template/tabular_infer`, set the inference dataset, then choose a
  model source:
  `Model/source_type=task_id`, `Model/source_task_id=<pipeline or stage task id>`,
  and `Model/model_selector=best` or `ensemble`.
- For local-path style checks, use `Model/source_type=local_path` and
  `Model/local_model_path=<training pipeline run dir or model file>`.
- Open `template/tabular_train_pipeline` from the Pipeline tab and verify:
  preprocess_features -> train_linear/ridge/lasso/elasticnet/random_forest/
  extra_trees/gradient_boosting -> build_ensemble_mean_topk/
  build_ensemble_weighted/build_ensemble_median -> evaluate_models.
- Required remote training inputs are `Input/clearml_dataset_id`,
  `Input/dataset_file`, and `Input/target_column`; local development can use
  `Input/local_path` plus `Input/target_column`.
- Use `Model/candidates=["linear","ridge","random_forest"]` style JSON and
  `Model/model_params_by_name={"ridge":{"alpha":1.0}}` for model-specific
  parameters. `Output/report_plots=false` suppresses ClearML plot media only.
- Do not use `tabular_train_full_*` or `tabular_pipeline_template` as primary
  UI entrypoints.
- Confirm stage artifacts: preprocess bundle, feature spec, per-model model
  artifacts, leaderboard, best model, optional ensemble artifact.
Useful logs on failure:

- pipeline controller task console
- each step task console
- task parameters
- stage task Artifacts tab
- Agent log for queue, git clone, package install, and entrypoint
- Dataset artifact URL plus `Input/clearml_dataset_id`, `Input/dataset_file`, `Input/local_path`, and `artifact_output_uri`

## Deploy Check

See `deploy/README.md`. At minimum verify:

- image repository and tag
- `clearml-credentials` Secret
- queue alignment across profile, deploy, and ClearML UI
- PVC size and storage class
- Agent visibility in ClearML Workers / Queues

## Do Not Do

- Do not add ClearML imports to `pkgs`.
- Do not add real ClearML server tests to pytest or CI.
- Do not expand UI parameters without a current product need.
- Do not copy legacy repo files or directory structures.
- Do not add broad diagnostics, contract docs, checklist docs, old adapter splits, live cleanup, or abstract base classes.
- Do not recreate legacy `train_ensemble_full`, stacking, or separate runtime
  leaderboard tasks.
- Do not add new stage nodes to deprecated templates; use
  `tabular_stage_template` through `tabular_train_pipeline_template`.
- Do not add model-specific or dataset-specific ClearML templates.
- Do not add `gaussian_process` or `tabpfn` to the supported model set without
  a separate verification phase.
- Do not reintroduce `knn`, `svr`, or `mlp` into the current product model set.
- Do not add stacking or weight optimization to ensemble without a new verification phase.
- Do not add Optuna, Ray Tune, per-trial ClearML child tasks, or an optimize template.
