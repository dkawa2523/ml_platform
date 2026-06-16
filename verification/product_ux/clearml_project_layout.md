# ClearML Project Layout Verification

Date: 2026-06-16

Scope: Phase 1 ClearML project / task naming and tag policy.

## Policy

Profile-managed projects:

- templates: `MLPlatform/Dev/Templates/Tabular`
- pipelines: `MLPlatform/Dev/Pipelines/Tabular`
- preprocess: `MLPlatform/Dev/Runs/Tabular/Preprocess`
- train: `MLPlatform/Dev/Runs/Tabular/Train`
- ensemble: `MLPlatform/Dev/Runs/Tabular/Ensemble`
- evaluate: `MLPlatform/Dev/Runs/Tabular/Evaluate`
- infer: `MLPlatform/Dev/Runs/Tabular/Infer`
- experiments: `MLPlatform/Dev/Experiments/Tabular`

ClearML display names:

- `template/tabular_train_pipeline`
- `template/tabular_infer`
- `internal/tabular_stage`
- `pipeline/tabular_train_pipeline/<run_name>`
- `stage/preprocess_features/<run_name>`
- `stage/train_<model>/<run_name>`
- `stage/build_ensemble_<method>/<run_name>`
- `stage/evaluate_models/<run_name>`
- `task/tabular_infer/<run_name>`

Canonical tags:

- `domain:tabular`
- `run_type:template | pipeline | stage | task`
- `user_facing:true`
- `internal:true`
- `stage:<stage_name>`
- `model:<model_name>`
- `ensemble:<method>`

## Commands

```powershell
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
.\.venv\Scripts\python.exe scripts\clearml_pipeline.py --task config\tasks\tabular_pipeline.yaml --profile config\profiles\clearml-dev.yaml --dry-run
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
  - preprocess target project: `MLPlatform/Dev/Runs/Tabular/Preprocess`
  - train target project: `MLPlatform/Dev/Runs/Tabular/Train`
  - ensemble target project: `MLPlatform/Dev/Runs/Tabular/Ensemble`
  - evaluate target project: `MLPlatform/Dev/Runs/Tabular/Evaluate`
  - stage base task: `MLPlatform/Dev/Templates/Tabular/internal/tabular_stage`
  - runtime name: `pipeline/tabular_train_pipeline/tabular_training_pipeline`
  - stage run names include `stage/train_linear/tabular_training_pipeline`
  - model stage tags include `model:<model_name>`
  - ensemble stage tags include `ensemble:<method>`
- Tests: `89 passed`.
- `git diff --check`: pass with line-ending warnings only.
- ClearML import boundary: pass, no ClearML imports under `pkgs/core` or `pkgs/tabular`.

## Notes

- This is repo-side dry-run evidence only. No ClearML remote tasks were created
  or archived in this pass.
- Old ClearML server tasks/runs may remain visible until a human archives them.
