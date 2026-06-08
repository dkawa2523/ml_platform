# ClearML Project Layout Verification

Date: 2026-06-08

Scope: Phase 2 ClearML project / task naming and tag policy.

## Policy

Profile-managed projects:

- templates: `MLPlatform/Dev/Templates/Tabular`
- pipelines: `MLPlatform/Dev/Pipelines/Tabular`
- stages: `MLPlatform/Dev/Runs/Tabular/Stages`
- tasks: `MLPlatform/Dev/Runs/Tabular/Tasks`
- experiments: `MLPlatform/Dev/Experiments/Tabular`

ClearML display names:

- `template/tabular_train_pipeline`
- `template/tabular_infer`
- `internal/tabular_stage`
- `pipeline/tabular_train_pipeline/<run_name>`
- `stage/<stage_name>/<run_name>`
- `stage/train_<model>/<run_name>`
- `task/tabular_infer/<run_name>`

Canonical tags:

- `domain:tabular`
- `run_type:template | pipeline | stage | task`
- `user_facing:true`
- `internal:true`
- `stage:<stage_name>`
- `model:<model_name>`

## Commands

```powershell
python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
python clearml/pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest -q
git diff --check
rg -n "from clearml|import clearml|PipelineController|StorageManager" pkgs/core pkgs/tabular
```

## Results

- Template dry-run: pass.
  - `template/tabular_infer` in `MLPlatform/Dev/Templates/Tabular`
  - `internal/tabular_stage` in `MLPlatform/Dev/Templates/Tabular`
  - `template/tabular_train_pipeline` in `MLPlatform/Dev/Pipelines/Tabular`
- Pipeline dry-run: pass.
  - controller project: `MLPlatform/Dev/Pipelines/Tabular`
  - stage target project: `MLPlatform/Dev/Runs/Tabular/Stages`
  - stage base task: `MLPlatform/Dev/Templates/Tabular/internal/tabular_stage`
  - runtime name: `pipeline/tabular_train_pipeline/tabular_training_pipeline`
  - stage run names include `stage/train_linear/tabular_training_pipeline`
  - model stage tags include `model:<model_name>`
- Tests: `56 passed`.
- `git diff --check`: pass with line-ending warnings only.
- ClearML import boundary: pass, no ClearML imports under `pkgs/core` or `pkgs/tabular`.

## Notes

- This is repo-side dry-run evidence only. No ClearML remote tasks were created
  or archived in this pass.
- Old ClearML server tasks/runs may remain visible until a human archives them.
