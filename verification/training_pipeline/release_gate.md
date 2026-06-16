# Primary Training / Inference Release Gate

Date: 2026-06-16
Profile: `config/profiles/clearml-dev.yaml`

## Decision

Local execution, tests, template sync dry-run, and Pipeline graph dry-run pass
for the current product scope. Remote ClearML verification is still a release
promotion step and should be recorded with fresh task IDs after syncing templates
from the branch being released.

## Current Product Scope

Training:

```text
preprocess_features -> train_<model>* -> build_ensemble_<method>* -> evaluate_models
```

Inference:

```text
tabular_infer_template -> predictions.csv
```

User-facing templates:

- `template/tabular_train_pipeline`
- `template/tabular_infer`

Internal template:

- `internal/tabular_stage`

P2 items such as HPO, Model Registry, drift monitoring, Task Registry,
external validation files, k-fold, nested CV, and `group_kfold` are not release
scope. See `docs/ROADMAP.md`.

## Required Gates

| gate | status | evidence |
| --- | --- | --- |
| Training pipeline local | pass | `scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml` |
| Inference local | pass | `scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml` |
| Template sync dry-run | pass | `scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run` |
| ClearML graph dry-run | pass | `scripts/clearml_pipeline.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run` |
| Tests | pass | `89 passed` |
| ClearML dependency boundary | pass | no ClearML SDK imports under `pkgs/core` or `pkgs/tabular` |
| Remote training pipeline | pending | run `template/tabular_train_pipeline` after template sync |
| Remote inference task-id best | pending | run `template/tabular_infer` with `source_type=task_id`, `model_selector=best` |

## Commands

```powershell
.\.venv\Scripts\python.exe scripts\make_sample_data.py
.\.venv\Scripts\python.exe scripts\local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set "model.candidates=[linear,ridge,lasso,elasticnet,random_forest,extra_trees,gradient_boosting]"
.\.venv\Scripts\python.exe scripts\local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
.\.venv\Scripts\python.exe scripts\clearml_pipeline.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
git diff --check
rg -n "from clearml|import clearml|PipelineController|StorageManager" pkgs/core pkgs/tabular
```

## Remote Evidence To Record

After syncing templates on the target ClearML server, record:

- training Pipeline task ID and git commit
- graph shape and queues
- `evaluate_models/decision_summary.md`
- inference task ID using `source_type=task_id`, `model_selector=best`
- key artifacts, tables, plots, and any sanitized failure logs
