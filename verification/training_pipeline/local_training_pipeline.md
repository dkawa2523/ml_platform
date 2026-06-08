# Local Training Pipeline Verification

Date: 2026-06-08

Scope: Phase B local training pipeline only. Inference and optimization are
intentionally not part of the primary training pipeline.

## Commands

```powershell
.\.venv\Scripts\python.exe scripts\make_sample_data.py
.\.venv\Scripts\python.exe scripts\local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml
```

Run directory:

```text
outputs\tabular_training_pipeline_20260608T023305Z
```

## Stage Summary

```text
preprocess_features
  -> train_linear
  -> train_ridge
  -> train_random_forest
  -> train_gradient_boosting
  -> train_multiple_models
  -> build_ensemble
  -> evaluate_models
```

The run reported `pipeline_kind=training`, `selection_metric=rmse`, and four
candidate models: `linear`, `ridge`, `random_forest`, and
`gradient_boosting`.

## Artifact Checklist

| artifact | result |
| --- | --- |
| `preprocess_features/preprocess_bundle.joblib` | present |
| `preprocess_features/feature_spec.json` | present |
| `preprocess_features/train_features.csv` | present |
| `preprocess_features/valid_features.csv` | present |
| `preprocess_features/processed_train.csv` | present |
| `preprocess_features/processed_valid.csv` | present |
| `train_linear/model.joblib` | present |
| `train_ridge/model.joblib` | present |
| `train_random_forest/model.joblib` | present |
| `train_gradient_boosting/model.joblib` | present |
| per-model `validation_predictions.csv` | present |
| `train_multiple_models/model_refs.json` | present |
| `train_multiple_models/metrics_by_model.json` | present |
| `build_ensemble/model.joblib` | present |
| `build_ensemble/ensemble_info.json` | present |
| `build_ensemble/ensemble_predictions.csv` | present |
| `evaluate_models/leaderboard.csv` | present |
| `evaluate_models/best_model.json` | present |
| `evaluate_models/best_model.joblib` | present |
| `evaluate_models/evaluation_report.json` | present |
| root `metrics.json` | present |
| root `manifest.json` | present |

## Result

Pass. The local training pipeline runs the intended training stages and does not
produce inference outputs. `tabular_infer_template` remains the separate
inference path.

`model.search.enabled=true` is rejected by the primary local training pipeline
in Phase B. Optimization remains future / experimental.
