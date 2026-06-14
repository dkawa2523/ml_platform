# Codex Handoff

Use this file as the short operational handoff. The product contract lives in
`docs/SPEC.md`; ClearML screen behavior lives in `docs/CLEARML_UI_SPEC.md`.

## Current Product

Training graph:

```text
preprocess_features -> train_<model>* -> build_ensemble_<method>* -> evaluate_models
```

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
- Do not add model-specific, ensemble-specific, or dataset-specific templates.
- Do not copy legacy repo code or directory layouts.

## Local Checks

Use dependency-free candidates unless GBM extras are installed locally:

```powershell
python scripts/make_sample_data.py
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set "model.candidates=[linear,ridge,lasso,elasticnet,random_forest,extra_trees,gradient_boosting]"
python scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

## ClearML Checks

Dry-run:

```powershell
python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
python clearml/pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
```

Real sync:

```powershell
python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml
```

Before remote execution, verify the profile `repository`, `branch`,
`working_dir`, `controller_queue`, `stage_queue`, and optional
`artifact_output_uri`. Run the PipelineController on `controller_queue`; stages
run on `stage_queue`. Remote runs should use `Input/clearml_dataset_id`,
`Input/dataset_file`, and `Input/target_column`; `Input/local_path` works only
when the Agent can see that path.

Current display names:

- `template/tabular_train_pipeline`
- `template/tabular_infer`
- `internal/tabular_stage`

Old ClearML tasks may remain on the server until manually archived.

## Release Focus

Current release evidence should show:

- stage graph with 10 model candidates and three ensemble methods on the
  configured execution image
- leaderboard tables and plots in `evaluate_models`
- prediction summary and distribution plots in `tabular_infer`
- no ClearML imports under `pkgs`

Historical verification can be consulted for context, but it is not the current
readiness gate.
