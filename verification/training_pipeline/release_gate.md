# Primary Training / Inference Release Gate

Date: 2026-06-08
Branch: `main`
Local HEAD: `5f501ae` plus uncommitted release-candidate changes
Profile: `config/profiles/clearml-dev.yaml`

## Decision

Result: not ready for release promotion.

Local execution, tests, ClearML template dry-run, and ClearML graph dry-run pass
for the primary scope. ClearML remote execution is still pending because the
dev profile clones GitHub `main`; running the Agent before commit/push would
validate the old remote checkout. Do not use old full-template, optimization,
or `train -> eval -> infer` compatibility evidence as the current product
release gate.

## Required Gates

| gate | status | evidence |
| --- | --- | --- |
| Training pipeline local | pass | `outputs\tabular_training_pipeline_20260608T035008Z` and `verification/training_pipeline/local_training_pipeline.md` |
| ClearML graph dry-run | pass | `verification/training_pipeline/clearml_training_pipeline.md` |
| Inference local | pass | best: `outputs\tabular_infer_20260608T035008Z`; ensemble: `outputs\tabular_infer_20260608T035042Z`; see `verification/inference/infer_task_reference.md` |
| Template sync dry-run | pass | Default sync targets are `tabular_train_pipeline_template`, `tabular_infer_template`, and `tabular_stage_template`. |
| Tests | pass | `56 passed` |
| ClearML dependency boundary | pass | `rg "from clearml|import clearml|PipelineController|StorageManager" pkgs/core pkgs/tabular` returned no matches. |
| ClearML remote training pipeline | pending | Run `tabular_train_pipeline_template` from the dev Pipeline tab. |
| ClearML remote inference task-id best | pending | Run `tabular_infer_template` with `source_type=task_id`, `model_selector=best`. |
| ClearML remote inference task-id ensemble | pending | Run `tabular_infer_template` with `source_type=task_id`, `model_selector=ensemble`. |

## Artifact Checklist

Primary training artifacts:

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

- best-model `predictions.csv`: pass
- ensemble `predictions.csv`: pass

## Current Product Graphs

Training:

```text
preprocess_features
  -> train_linear
  -> train_ridge
  -> train_random_forest
  -> train_gradient_boosting
  -> build_ensemble
  -> evaluate_models
```

Inference:

```text
source_task_id + model_selector
or local_model_path
-> inference dataset
-> feature align
-> predict
-> predictions.csv
```

## Commands

```powershell
.\.venv\Scripts\python.exe scripts\make_sample_data.py
.\.venv\Scripts\python.exe scripts\local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
.\.venv\Scripts\python.exe clearml\pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
git diff --check
```

## Scope Classification

Primary:

- `tabular_train_pipeline_template`
- `tabular_infer_template`
- internal `tabular_stage_template`
- local training pipeline for official models
- local inference from best / ensemble / local model references

Future / experimental:

- optimization pipeline
- `artifact_url` inference source
- `clearml_model_id` inference source
- full template configs
- external model full pipeline
- additional sklearn models beyond the official four

Historical compatibility:

- `tabular_pipeline_template`
- `Run/pipeline_mode`
- fixed `train -> eval -> infer` release gates

## Required Fixes Before Release

- Sync the three primary ClearML templates on the dev server.
- Run remote dev verification for:
  - `tabular_train_pipeline_template`
  - `tabular_infer_template` with `source_type=task_id`, `model_selector=best`
  - `tabular_infer_template` with `source_type=task_id`, `model_selector=ensemble`
- Record task IDs, graph shape, artifacts, metrics, and sanitized failure logs.

## Commit Scope

Commit candidates:

- `pkgs/tabular` implementation files
- ClearML adapter/template/pipeline files under `clearml`
- primary task configs under `config/tasks`
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
