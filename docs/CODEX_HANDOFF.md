# Codex Handoff

This repo has V2 product scope for tabular scalar regression. Keep the implementation simple.

## Current State

- Local train/eval/infer/pipeline and tabular 1D output run successfully.
- ClearML task entrypoint, adapter, reports, templates, and pipeline controller are implemented.
- ClearML SDK usage is contained under `clearml/`.
- `pkgs/core` and `pkgs/tabular` do not import ClearML.
- Deploy manifests provide a minimal ClearML Agent runtime.
- Tests are smoke and boundary oriented.
- Official supported regression models are `linear`, `ridge`, `random_forest`, and `gradient_boosting`.
- Experimental sklearn regressors are implemented: `lasso`, `elasticnet`, `extra_trees`, `knn`, `svr`, and `mlp`.
- `scikit-learn` is a required runtime dependency.
- Verification evidence lives under `verification/v1/`, `verification/v1_2/`, `verification/v1_3/`, `verification/v2_1/`, `verification/v2_2/`, and `verification/v2_remote/`.
- V1 single-model switching uses `Model/name` and `Model/params`.
- Comparison uses `Model/candidates` as a list of model names, model-keyed `Model/params`, and `Model/selection_metric`; it writes `leaderboard.csv` and saves only the best model artifact.
- Ensemble uses `Model/ensemble_enabled`, `Model/ensemble_method`, and `Model/ensemble_top_k` in ClearML, while local config stays nested under `model.ensemble`. Supported methods are `mean_topk` and `weighted`; both save one standard `model` artifact.
- Search uses `Model/search_enabled`, `Model/search_method`, `Model/search_space`, and `Model/max_trials`; it writes `optimization_trials.csv`, `optimization_summary.json`, and `best_params.json`, then saves the best params as the standard retrained `model` artifact.
- Inference adds `model_artifact_id` to `predictions.csv` and supports optional CSV chunked prediction with `Output/chunk_size`.

## Scope Rules

`docs/SPEC.md` is the source of truth for supported, experimental, future, and
discarded scope. Do not promote an experimental or future feature to supported
without local and ClearML remote verification evidence.

## Required Local Check

```powershell
python scripts/make_sample_data.py
python scripts/local_run.py --task config/tasks/tabular_train.yaml --profile config/profiles/local.yaml
python scripts/local_run.py --task config/tasks/tabular_eval.yaml --profile config/profiles/local.yaml
python scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml
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
```

Real sync:

```powershell
python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml
```

Pipeline Agent capacity:

- Remote pipeline execution needs at least two worker slots on the execution queue: one for the pipeline controller task and one for step tasks. Alternatively, use separate controller and step queues.

Manual UI checks:

- Clone `tabular_train_template`, set `Input/*`, `Run/*`, `Model/*`, and run.
- Clone `tabular_eval_template`, set the dataset and model artifact when needed, and run.
- Clone `tabular_infer_template`, set the dataset and model artifact when needed, and run.
- Clone `tabular_pipeline_template` and verify exactly three steps: train, eval, infer.
- Confirm train uploads the `model` artifact and eval/infer receive it as `Model/artifact_path`.

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
- Do not add all-model pipeline DAGs, stacking, train_ensemble_full, or separate runtime leaderboard tasks.
- Do not add model-specific or dataset-specific ClearML templates.
- Do not mark `gaussian_process`, LightGBM, XGBoost, CatBoost, or TabPFN as supported without a separate verification phase.
- Do not add stacking or weight optimization to ensemble without a new verification phase.
- Do not add Optuna, Ray Tune, per-trial ClearML child tasks, or an optimize template for current search.
