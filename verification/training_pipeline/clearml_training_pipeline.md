# ClearML Training Pipeline Verification

Date: 2026-06-08

## Scope

Phase C normalizes the primary ClearML training pipeline graph:

```text
preprocess_features
  -> train_<model>*
  -> build_ensemble_<method>*
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
- dry-run tags:
  - user entries: `product:tabular`, `entrypoint:user`
  - internal stage: `product:tabular`, `entrypoint:internal`
- primary Pipeline-tab draft: `tabular_train_pipeline_template`
- dev profile Pipeline defaults use `Input/clearml_dataset_id=b7afaea9d7aa42f084fb4fc06b0d4d41`,
  `Input/dataset_file=sample_train.csv`, and blank `Input/local_path`
- graph from `config/tasks/tabular_pipeline.yaml`:
  - `preprocess_features`
  - `train_linear`
  - `train_ridge`
  - `train_lasso`
  - `train_elasticnet`
  - `train_random_forest`
  - `train_extra_trees`
  - `train_gradient_boosting`
  - `build_ensemble_mean_topk`
  - `build_ensemble_weighted`
  - `build_ensemble_median`
  - `evaluate_models`
- all graph nodes use `tabular_stage_template`
- `train_<model>` steps receive preprocess artifact refs
- each `build_ensemble_<method>` receives JSON `Input/model_refs` and one ensemble method
- `evaluate_models` receives JSON `Input/model_refs` and `Input/ensemble_refs`
- Pipeline UI params do not expose `Model/search_*` or `Run/pipeline_mode`

## Expected Stage Artifacts

- `preprocess_features`: `preprocess_bundle`, `feature_spec`, `processed_train`, `processed_valid`, `train_features`, `valid_features`
- `train_<model>`: `model`, `model_info`, `validation_predictions`, `metrics`, lightweight validation plots
- `build_ensemble_<method>`: `model_<method>`, `model_info_<method>`, `ensemble_info_<method>`, `ensemble_predictions_<method>`, `metrics_<method>`, lightweight ensemble plots
- `evaluate_models`: `leaderboard`, `best_model`, `best_model_json`, `ensemble_refs`, `ensemble_info_by_method`, `evaluation_report`, `metrics`, `manifest`

## Remote Verification

Result: not run

Remote dev server execution still needs to be performed from the ClearML
Pipeline tab:

- `tabular_train_pipeline_template`
- candidates: `linear`, `ridge`, `lasso`, `elasticnet`, `random_forest`,
  `extra_trees`, `gradient_boosting`
- ensemble methods: `mean_topk`, `weighted`, `median`

Do not promote the ClearML stage-based training pipeline to supported scope
until that remote evidence is recorded.
