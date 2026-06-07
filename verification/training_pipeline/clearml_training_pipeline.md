# ClearML Training Pipeline Verification

Date: 2026-06-04

## Scope

Phase C implements the ClearML stage-based training pipeline graph:

```text
preprocess_features
  -> train_<model>*
  -> build_ensemble optional
  -> evaluate_models
```

Inference is intentionally excluded and remains `tabular_infer_template`.

## Dry-Run Commands

```powershell
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
.\.venv\Scripts\python.exe clearml\pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
```

## Dry-Run Result

Result: pass

- task templates: `tabular_infer_template`, `tabular_stage_template`
- Pipeline-tab drafts:
  - `tabular_train_pipeline_template`
  - `tabular_train_full_pipeline_template`
  - `tabular_train_full_ensemble_pipeline_template`
- default local alias graph from `config/tasks/tabular_pipeline.yaml`:
  - `preprocess_features`
  - `train_linear`
  - `train_ridge`
  - `train_random_forest`
  - `train_gradient_boosting`
  - `build_ensemble`
  - `evaluate_models`
- all graph nodes use `tabular_stage_template`
- model refs use JSON placeholders such as `${train_linear.artifacts.model.url}`
- ensemble refs use `${build_ensemble.artifacts.model.url}`

## Expected Stage Artifacts

- `preprocess_features`: `preprocess_bundle`, `feature_spec`, `processed_train`, `processed_valid`, `train_features`, `valid_features`
- `train_<model>`: `model`, `model_info`, `validation_predictions`, `metrics`
- `build_ensemble`: `model`, `model_info`, `ensemble_info`, `ensemble_predictions`, `metrics`
- `evaluate_models`: `leaderboard`, `best_model`, `best_model_json`, `evaluation_report`, `metrics`, `manifest`

## Remote Verification

Result: not run

Remote dev server execution still needs to be performed from the ClearML Pipeline tab for at least:

- `tabular_train_pipeline_template`
- `tabular_train_full_ensemble_pipeline_template`

Do not promote ClearML stage-based training pipelines to supported scope until that remote evidence is recorded.
