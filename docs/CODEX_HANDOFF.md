# Codex Handoff

This repo has V2 product scope for tabular scalar regression. Keep the implementation simple.

## Current State

- Local train/eval/infer, stage-based training pipeline, deprecated
  compatibility simple full-run fallback, and tabular 1D output run
  successfully.
- Local stage-based optimization pipeline runs as
  `preprocess_features -> search_trials -> retrain_best -> evaluate_best`
  when `model.search.enabled=true` and `model.ensemble.enabled=false`.
- ClearML task entrypoint, adapter, reports, templates, and pipeline controller are implemented.
- ClearML SDK usage is contained under `clearml/`.
- `pkgs/core` and `pkgs/tabular` do not import ClearML.
- Deploy manifests provide a minimal ClearML Agent runtime.
- Tests are smoke and boundary oriented.
- Official supported regression models are `linear`, `ridge`, `random_forest`, and `gradient_boosting`.
- Experimental sklearn regressors are implemented: `lasso`, `elasticnet`, `extra_trees`, `knn`, `svr`, and `mlp`.
- `scikit-learn` is a required runtime dependency.
- Verification evidence lives under `verification/v1/`, `verification/v1_2/`,
  `verification/v1_3/`, `verification/v2_1/`, `verification/v2_2/`,
  `verification/v2_remote/`, `verification/training_pipeline/`,
  `verification/inference/`, and `verification/optimization/`. Start with
  `verification/README.md` to understand which evidence is current product
  evidence and which evidence is historical compatibility evidence.
- V1 single-model switching uses `Model/name` and `Model/params`.
- Deprecated compatibility Pipeline-tab full-run uses `Run/pipeline_mode`:
  `auto`, `single`, `compare`, `ensemble`, or `optimize`.
- Comparison uses `Model/candidates` as a list of model names, model-keyed `Model/params`, and `Model/selection_metric`; it writes `leaderboard.csv` and saves only the best model artifact.
- Ensemble uses `Model/ensemble_enabled`, `Model/ensemble_method`, and `Model/ensemble_top_k` in ClearML, while local config stays nested under `model.ensemble`. Supported methods are `mean_topk` and `weighted`; both save one standard `model` artifact.
- Search uses `Model/search_enabled`, `Model/search_method`, `Model/search_space`, and `Model/max_trials`; train tasks still support train-time search, and stage-based pipelines use these parameters to switch to the optimization graph.
- Inference resolves `task_id`, `artifact_url`, `clearml_model_id`, or
  `local_path` sources, adds `model_artifact_id` to `predictions.csv`, and
  supports optional CSV chunked prediction with `Output/chunk_size`.

## Scope Rules

`docs/SPEC.md` is the source of truth for supported, experimental, future, and
discarded scope. Do not promote an experimental or future ClearML feature to
supported without local and ClearML remote verification evidence.

The official training pipeline definition is:

```text
preprocess_features -> train_<model>* -> build_ensemble optional -> evaluate_models
```

`config/tasks/tabular_pipeline.yaml` and `pkgs/tabular.pipeline.run_pipeline()`
implement this graph locally. ClearML Pipeline-tab drafts implement the same
graph through the internal `tabular_stage_template`; these ClearML pipeline
drafts remain experimental until remote evidence is recorded. The old
`tabular_pipeline_template` remains a deprecated compatibility full-run
entrypoint for `train -> eval -> infer`.

Inference is a separate `tabular_infer_template` task. Do not fold inference
into the training pipeline redesign.

## Required Local Check

```powershell
python scripts/make_sample_data.py
python scripts/local_run.py --task config/tasks/tabular_train.yaml --profile config/profiles/local.yaml
python scripts/local_run.py --task config/tasks/tabular_eval.yaml --profile config/profiles/local.yaml
python scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
# Local stage-based training pipeline. Inference is intentionally separate.
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml
# Local stage-based optimization pipeline. Quote JSON-like overrides in PowerShell.
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set model.ensemble.enabled=false --set 'model.candidates=[]' --set model.name=ridge --set 'model.params={}' --set model.search.enabled=true --set model.search.method=grid --set model.search.max_trials=2 --set 'model.search.search_space={"alpha":[0.1,1.0]}'
python scripts/local_run.py --task config/tasks/tabular_1d_output.yaml --profile config/profiles/local.yaml
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
- `artifact_output_uri` is only the destination for artifacts produced by train/eval/infer. It does not change where an existing ClearML Dataset is stored or whether the Dataset artifact URL is reachable.

Dry-run:

```powershell
python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
python clearml/pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
python clearml/pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run --set model.ensemble.enabled=false --set 'model.candidates=[]' --set model.name=ridge --set 'model.params={}' --set model.search.enabled=true --set model.search.method=grid --set model.search.max_trials=2 --set 'model.search.search_space={"alpha":[0.1,1.0]}'
```

Real sync:

```powershell
python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml
```

PipelineController Agent capacity:

- Remote training pipeline execution needs enough worker slots on the execution
  queue for the controller and stage tasks. Alternatively, use separate
  controller and step queues.

Manual UI checks:

- Clone `tabular_infer_template`, set the inference dataset, then choose a
  model source:
  `Model/source_type=task_id`, `Model/source_task_id=<pipeline or stage task id>`,
  and `Model/model_selector=best` or `ensemble`.
- For local-path style checks, use `Model/source_type=local_path` and
  `Model/local_model_path=<training pipeline run dir or model file>`.
- Open `tabular_train_pipeline_template` from the Pipeline tab and verify:
  preprocess_features -> train_linear/ridge/random_forest/gradient_boosting ->
  evaluate_models.
- Open `tabular_train_full_ensemble_pipeline_template` from the Pipeline tab and
  verify: preprocess_features -> train_<model>* -> build_ensemble ->
  evaluate_models.
- Open `tabular_pipeline_template` only if intentionally checking deprecated
  compatibility behavior.
- Confirm stage artifacts: preprocess bundle, feature spec, per-model model
  artifacts, leaderboard, best model, optional ensemble artifact.
- For optimization checks, set `Model/search_enabled=true` and
  `Model/ensemble_enabled=false`; confirm the graph is
  preprocess_features -> search_trials -> retrain_best -> evaluate_best and
  artifacts include `optimization_trials`, `optimization_summary`,
  `best_params`, retrained `model`, and `best_model`.

Useful logs on failure:

- pipeline controller task console
- each step task console
- task parameters
- train task Artifacts tab
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
- Do not add new stage nodes to the deprecated `tabular_pipeline_template`; use
  `tabular_stage_template` through the user-facing training pipeline drafts.
- Do not add model-specific or dataset-specific ClearML templates.
- Do not mark `gaussian_process`, LightGBM, XGBoost, CatBoost, or TabPFN as supported without a separate verification phase.
- Do not add stacking or weight optimization to ensemble without a new verification phase.
- Do not add Optuna, Ray Tune, per-trial ClearML child tasks, or an optimize template for current search.
