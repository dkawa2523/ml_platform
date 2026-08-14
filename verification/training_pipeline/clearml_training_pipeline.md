# ClearML Training Pipeline Verification

Date: 2026-08-14

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
.\.venv\Scripts\python.exe scripts\clearml_pipeline.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
```

## Dry-Run Result

Result: pass

- default sync targets:
  - `tabular_infer_template`
  - `tabular_stage_template`
  - `tabular_train_pipeline_template`
- dry-run tags:
  - user entries: `domain:tabular`, `run_type:template`, `user_facing:true`
  - internal stage: `domain:tabular`, `run_type:template`, `internal:true`
- primary Pipeline-tab draft: `template/tabular_train_pipeline`
- dev profile Pipeline defaults use `Input/clearml_dataset_id=b7afaea9d7aa42f084fb4fc06b0d4d41`,
  `Input/dataset_file=sample_train.csv`, and blank `Input/local_path`
- Basic Pipeline defaults use `Basic/model_suite=default`,
  `Basic/quality_mode=standard`, and `Basic/use_ensemble=true`
- Split defaults use `Split/method=random` and `Split/valid_size=0.2`; group,
  time, and fixed split columns are blank until selected by the user
- graph from `config/tasks/tabular_pipeline.yaml`:
  - `preprocess_features`
  - `train_linear`
  - `train_ridge`
  - `train_lasso`
  - `train_elasticnet`
  - `train_random_forest`
  - `train_extra_trees`
  - `train_gradient_boosting`
  - `train_lightgbm`
  - `train_xgboost`
  - `train_catboost`
  - `build_ensemble_mean_topk`
  - `build_ensemble_weighted`
  - `build_ensemble_median`
  - `evaluate_models`
- all graph nodes use `internal/tabular_stage`
- `train_<model>` steps receive preprocess artifact refs
- each `build_ensemble_<method>` receives JSON `Input/model_refs` and one ensemble method
- `evaluate_models` receives JSON `Input/model_refs` and `Input/ensemble_refs`
- Pipeline UI params do not expose `Model/search_*`, `Run/pipeline_mode`, or
  `Model/ensemble_method`
- `Basic/use_ensemble` is the single public ensemble switch

## Expected Stage Artifacts

- `preprocess_features`: `preprocess_bundle`, `feature_spec`, `data_quality_summary`, `data_quality_summary_table`, `data_quality_warnings`, `processed_train`, `processed_valid`
- `train_<model>`: `model`, `model_info`, `validation_predictions`, `metrics`, lightweight validation plots
- `build_ensemble_<method>`: `model_<method>`, `model_info_<method>`, `ensemble_info_<method>`, `ensemble_predictions_<method>`, `metrics_<method>`, lightweight ensemble plots
- `evaluate_models`: `leaderboard`, `best_model`, `best_model_json`, `ensemble_refs`, `ensemble_info_by_method`, `evaluation_report`, `metrics`, `manifest`

## Remote Verification

Result: pass

- synced Pipeline template: `808d1808618c419ea302eb1320a96143`
- completed Pipeline: `3290c45a3f7041b5a91f23027ba87266`
- completed evaluate stage: `aa8c9d0bc3c1448ebd3419ab9810a6bd`
- graph: preprocess 1, fast-suite train 7, evaluate 1; all 9 stages completed
- controller, stage templates, and all stage runs used commit
  `e06b0fdd83ab1a8e691014acf551919bb574002f`, `python3.11`, and
  `ml-platform-clearml-agent:dev`
- Pipeline template exposed 33 `Args/*` inputs and no duplicate top-level
  `Basic/*`, `Input/*`, `Model/*`, or other runtime inputs
- the clean execution image build context contained no repository source; a
  clean Agent task reported zero Git editable requirements
