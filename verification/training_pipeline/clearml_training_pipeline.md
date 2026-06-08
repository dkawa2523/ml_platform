# ClearML Training Pipeline Verification

Date: 2026-06-08

## Scope

Phase C normalizes the primary ClearML training pipeline graph:

```text
preprocess_features
  -> train_<model>*
  -> build_ensemble
  -> evaluate_models
```

Inference is intentionally excluded and remains `tabular_infer_template`.
Optimization is intentionally excluded from the primary graph.

## Dry-Run Commands

```powershell
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
.\.venv\Scripts\python.exe clearml\pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
```

## Dry-Run Result

Result: pass

- default sync targets:
  - `tabular_infer_template`
  - `tabular_stage_template`
  - `tabular_train_pipeline_template`
- primary Pipeline-tab draft: `tabular_train_pipeline_template`
- graph from `config/tasks/tabular_pipeline.yaml`:
  - `preprocess_features`
  - `train_linear`
  - `train_ridge`
  - `train_random_forest`
  - `train_gradient_boosting`
  - `build_ensemble`
  - `evaluate_models`
- all graph nodes use `tabular_stage_template`
- `train_<model>` steps receive preprocess artifact refs
- `build_ensemble` receives JSON `Input/model_refs`
- `evaluate_models` receives JSON `Input/model_refs` and `Input/ensemble_ref`
- Pipeline UI params do not expose `Model/search_*`

## Expected Stage Artifacts

- `preprocess_features`: `preprocess_bundle`, `feature_spec`, `processed_train`, `processed_valid`, `train_features`, `valid_features`
- `train_<model>`: `model`, `model_info`, `validation_predictions`, `metrics`
- `build_ensemble`: `model`, `model_info`, `ensemble_info`, `ensemble_predictions`, `metrics`
- `evaluate_models`: `leaderboard`, `best_model`, `best_model_json`, `evaluation_report`, `metrics`, `manifest`

## Remote Verification

Result: not run

Remote dev server execution still needs to be performed from the ClearML
Pipeline tab:

- `tabular_train_pipeline_template`
- candidates: `linear`, `ridge`, `random_forest`, `gradient_boosting`
- ensemble enabled

Do not promote the ClearML stage-based training pipeline to supported scope
until that remote evidence is recorded.
