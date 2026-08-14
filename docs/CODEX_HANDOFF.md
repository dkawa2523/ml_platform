# Codex Handoff

Use this file as the short operational handoff. The product spec lives in
`docs/SPEC.md`; ClearML screen behavior lives in `docs/CLEARML_UI_SPEC.md`;
future/P2 scope lives in `docs/ROADMAP.md`.

## Current Product

Training graph:

```text
preprocess_features -> train_<model>* -> build_ensemble_<method>* -> evaluate_models
```

Package stage keys stay stable as `preprocess_features`, `train_model`,
`build_ensemble`, and `evaluate_models`. The `<model>` and `<method>` suffixes
are ClearML step labels/task names only.

Inference is separate through `tabular_infer_template` with either:

- `source_task_id + model_selector`
- `local_model_path`

Primary configs:

- `config/tasks/tabular_pipeline.yaml`
- `config/tasks/tabular_stage.yaml`
- `config/tasks/tabular_infer.yaml`

Supported models are `linear`, `ridge`, `lasso`, `elasticnet`,
`random_forest`, `extra_trees`, `gradient_boosting`, `lightgbm`, `xgboost`, and
`catboost`. GBM models are supported optional-dependency models: local/package
required dependencies stay light, while synced ClearML templates add GBM
packages to the remote execution venv for 10-model runs.

Supported ensemble methods are `mean_topk`, `weighted`, and `median`.

## Boundaries

- `pkgs/core` and `pkgs/tabular` remain ClearML-free.
- ClearML SDK usage stays under `clearml/`.
- `scripts/` stay wrapper-only.
- Local operator commands should prefer `scripts/` wrappers. Remote ClearML
  templates still point at `clearml/app.py` and `clearml/pipelines.py`.
- Do not add model-specific, ensemble-specific, or dataset-specific templates.
- Do not copy legacy repo code or directory layouts.
- Do not implement HPO, Model Registry, drift/monitoring, Task Registry,
  external validation files, k-fold, nested CV, or group-k-fold in this release.
  Keep them in `docs/ROADMAP.md` until explicitly promoted.

## Local Checks

Use dependency-free candidates unless GBM extras are installed locally:

```powershell
uv run python scripts/make_sample_data.py
uv run python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set "model.candidates=[linear,ridge,lasso,elasticnet,random_forest,extra_trees,gradient_boosting]"
uv run python scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
uv run python -m pytest -q
```

## ClearML Checks

Dry-run:

```powershell
uv run python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
uv run python scripts/clearml_pipeline.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
```

Real sync:

```powershell
uv run python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml
```

Template sync intentionally recreates the Pipeline draft. ClearML stores the
graph separately from task parameters, so updating an existing draft can leave
New Run inputs current while the graph stays old. Do not rely on old run clones
when validating template changes.

Before remote execution, verify `clearml.execution` (`repository`, `revision`,
`working_dir`, `image`, and `python_binary`), `controller_queue`, `stage_queue`,
and optional `artifact_output_uri`. Sync resolves `revision` to one commit used
by all templates. Run the PipelineController on `controller_queue`; stages
run on `stage_queue`. Remote runs should use `Input/clearml_dataset_id`,
`Input/dataset_file`, and `Input/target_column`; `Input/local_path` works only
when the Agent can see that path.

Current display names:

- `template/tabular_train_pipeline`
- `template/tabular_infer`
- `internal/tabular_stage`

Old ClearML tasks may remain on the server until manually archived.

## Import Safety Notes

The repository keeps a top-level `clearml/` operations directory because synced
templates execute `clearml/app.py` and `clearml/pipelines.py` directly. Official
SDK imports must continue to go through `adapter.import_clearml_sdk()` so the
local operations directory does not shadow the external `clearml` package.

Do not rename `clearml/` in a small maintenance change. A safe future migration
should add new script/module entrypoints first, sync templates to the new
entrypoints, verify remote Pipeline and inference runs, then remove the old
entrypoints after existing ClearML drafts are archived or recreated.

## Release Focus

Current release evidence should show:

- stage graph with 10 model candidates and three ensemble methods on the
  configured execution image
- leaderboard tables and plots in `evaluate_models`
- prediction summary and distribution plots in `tabular_infer`
- no ClearML imports under `pkgs`

Historical verification can be consulted for context, but it is not the current
readiness gate.
