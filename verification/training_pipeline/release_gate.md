# Stage-Based Training Pipeline Release Gate

Date: 2026-06-04
Branch: `main`
Local HEAD: `fc219af`
Profile: `config/profiles/clearml-dev.yaml`

## Decision

Result: not ready for release promotion.

Local execution, tests, ClearML template dry-run, and ClearML graph dry-run all
passed. ClearML remote execution is blocked because the working tree contains
the current implementation and `config/profiles/clearml-dev.yaml` runs Agents
from GitHub `main`. Launching remote tasks before commit/push would validate the
old remote checkout, not this release candidate.

## Required Gates

| gate | status | evidence |
| --- | --- | --- |
| Training pipeline local | pass | `outputs/tabular_training_pipeline_20260604T001907Z` contains `preprocess_features`, per-model `train_*`, `build_ensemble`, and `evaluate_models`. |
| ClearML graph dry-run | pass | `tabular_train_pipeline.yaml` dry-run shows `preprocess_features -> train_linear/ridge/random_forest/gradient_boosting -> evaluate_models`. |
| Full ensemble graph dry-run | pass | `tabular_train_full_ensemble_pipeline.yaml` dry-run shows `preprocess_features -> train_<model>* -> build_ensemble -> evaluate_models`. |
| Inference local | pass | `outputs/tabular_infer_20260604T001914Z/predictions.csv` exists and uses the best model from the training pipeline. |
| Optimization local | pass | `outputs/tabular_training_pipeline_20260604T001936Z` contains `search_trials`, `retrain_best`, and `evaluate_best`. |
| Optimization graph dry-run | pass | Override dry-run shows `preprocess_features -> search_trials -> retrain_best -> evaluate_best`. |
| Tests | pass | `57 passed`. |
| ClearML dependency boundary | pass | `rg "from clearml|import clearml|PipelineController|StorageManager" pkgs/core pkgs/tabular` returned no matches. |
| Docs cleanup | pass | Current docs call `train -> eval -> infer` historical/compatibility, not the official training pipeline. |
| ClearML remote | blocked | Current changes are uncommitted/unpushed while Agent profile clones GitHub `main`. |

## Commands

```powershell
.\.venv\Scripts\python.exe scripts\make_sample_data.py
.\.venv\Scripts\python.exe scripts\local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
.\.venv\Scripts\python.exe clearml\pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
.\.venv\Scripts\python.exe clearml\pipelines.py --task config/tasks/tabular_train_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
.\.venv\Scripts\python.exe clearml\pipelines.py --task config/tasks/tabular_train_full_ensemble_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
.\.venv\Scripts\python.exe scripts\local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set model.ensemble.enabled=false --set 'model.candidates=[]' --set model.name=ridge --set 'model.params={}' --set model.search.enabled=true --set model.search.method=grid --set model.search.max_trials=2 --set 'model.search.search_space={"alpha":[0.1,1.0]}'
.\.venv\Scripts\python.exe clearml\pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run --set model.ensemble.enabled=false --set 'model.candidates=[]' --set model.name=ridge --set 'model.params={}' --set model.search.enabled=true --set model.search.method=grid --set model.search.max_trials=2 --set 'model.search.search_space={"alpha":[0.1,1.0]}'
git diff --check
```

## Artifact Checklist

Training pipeline artifacts:

- `preprocess_features/preprocess_bundle.joblib`: pass
- `preprocess_features/feature_spec.json`: pass
- `train_linear/model.joblib`: pass
- `train_ridge/model.joblib`: pass
- `train_random_forest/model.joblib`: pass
- `train_gradient_boosting/model.joblib`: pass
- `build_ensemble/model.joblib`: pass
- `build_ensemble/ensemble_info.json`: pass
- `evaluate_models/leaderboard.csv`: pass
- `evaluate_models/best_model.json`: pass
- `evaluate_models/evaluation_report.json`: pass

Inference artifacts:

- `predictions.csv`: pass
- `manifest.json`: pass

Optimization artifacts:

- `search_trials/optimization_trials.csv`: pass
- `search_trials/best_params.json`: pass
- `retrain_best/model.joblib`: pass
- `evaluate_best/evaluation_report.json`: pass

## Scope Classification

Supported:

- Local stage-based training pipeline for official models.
- Local `tabular_infer_template` execution from local/best model references.
- Local stage-based grid/random optimization.
- ClearML task/template mapping and graph dry-run behavior.

Experimental:

- ClearML stage-based training pipeline remote execution.
- ClearML full ensemble pipeline remote execution.
- ClearML inference `source_type=task_id` for best/ensemble selectors.
- Additional sklearn models in full templates.

Future:

- Optuna, Ray Tune, Bayesian optimization.
- Per-trial ClearML child tasks.
- LightGBM, XGBoost, CatBoost.
- Stacking, advanced plots, online serving, large dataset inference.

## Required Fixes Before Release

- Commit and push the current implementation to the branch used by
  `config/profiles/clearml-dev.yaml`.
- Sync ClearML templates on the dev server.
- Run remote dev verification for:
  - `tabular_train_pipeline_template`
  - `tabular_train_full_ensemble_pipeline_template`
  - `tabular_infer_template` with `source_type=task_id`, `model_selector=best`
  - `tabular_infer_template` with `source_type=task_id`, `model_selector=ensemble`
- Record task IDs, graph shape, artifacts, metrics, and sanitized failure logs.

## Commit Scope

Commit candidates:

- implementation files under `pkgs/tabular`
- ClearML adapter/template/pipeline files under `clearml`
- task configs under `config/tasks`
- focused tests
- docs and verification markdown

Commit exclusions:

- `outputs/`
- raw ClearML logs
- screenshots unless sanitized and intentionally requested
- secrets, private Dataset IDs, private artifact URLs

Recommended tag:

- Do not create a release tag from this gate.
- After remote pass, use a release candidate tag such as `v2.4.0-rc1`; promote
  to a final tag only after the remote evidence is recorded.
