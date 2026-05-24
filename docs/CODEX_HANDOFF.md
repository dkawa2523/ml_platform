# Codex Handoff

This repo is ready for small product hardening and ClearML environment validation. Keep the implementation simple.

## Current State

- Local train/eval/infer/pipeline and tabular 1D output run successfully.
- ClearML task entrypoint, adapter, reports, templates, and pipeline controller are implemented.
- ClearML SDK usage is contained under `clearml/`.
- `pkgs/core` and `pkgs/tabular` do not import ClearML.
- Deploy manifests provide a minimal ClearML Agent runtime.
- Tests are smoke and boundary oriented.

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

Dry-run:

```powershell
python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
python clearml/pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
```

Real sync:

```powershell
python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml
```

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
- Do not add broad diagnostics, contract docs, or abstract base classes.
