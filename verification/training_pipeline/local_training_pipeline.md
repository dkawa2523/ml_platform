# Local Training Pipeline Verification

Date: 2026-06-16

Scope: current local training pipeline. Inference remains a separate task, and
optimization is future scope rather than part of the primary training pipeline.

## Commands

```powershell
.\.venv\Scripts\python.exe scripts\make_sample_data.py
.\.venv\Scripts\python.exe scripts\local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set "model.candidates=[linear,ridge,lasso,elasticnet,random_forest,extra_trees,gradient_boosting]"
```

Run directory:

```text
outputs\latest_training_pipeline
```

## Stage Summary

```text
preprocess_features
  -> train_linear
  -> train_ridge
  -> train_lasso
  -> train_elasticnet
  -> train_random_forest
  -> train_extra_trees
  -> train_gradient_boosting
  -> build_ensemble_<method>*
  -> evaluate_models
```

The latest local run reported `pipeline_kind=training`, `selection_metric=rmse`,
and the dependency-free candidate subset: `linear`, `ridge`, `lasso`,
`elasticnet`, `random_forest`, `extra_trees`, and `gradient_boosting`. The
ClearML template default remains all 10 supported models, including optional
GBM candidates when their packages are installed.

## Artifact Checklist

This dated run predates the lean artifact cleanup. Its transformed feature
matrices were present at the time, but current runs no longer emit
`train_features.csv` or `valid_features.csv`; the files were unused downstream
and could grow prohibitively large for high-cardinality data.

| artifact | result |
| --- | --- |
| `preprocess_features/preprocess_bundle.joblib` | present |
| `preprocess_features/feature_spec.json` | present |
| `preprocess_features/data_quality_summary.json` | present |
| `preprocess_features/data_quality_summary_table.csv` | present |
| `preprocess_features/data_quality_warnings.csv` | present |
| `preprocess_features/processed_train.csv` | present |
| `preprocess_features/processed_valid.csv` | present |
| `train_linear/model.joblib` | present |
| `train_ridge/model.joblib` | present |
| `train_lasso/model.joblib` | present |
| `train_elasticnet/model.joblib` | present |
| `train_random_forest/model.joblib` | present |
| `train_extra_trees/model.joblib` | present |
| `train_gradient_boosting/model.joblib` | present |
| per-model `validation_predictions.csv` | present |
| per-model `validation_prediction_vs_actual.png` | present |
| per-model `validation_residual_histogram.png` | present |
| `evaluate_models/model_refs.json` | present |
| `evaluate_models/metrics_by_model.json` | present |
| `build_ensemble/ensemble_refs.json` | present |
| `build_ensemble/ensemble_info_by_method.json` | present |
| per-method ensemble model artifacts | present |
| per-method ensemble info / metrics | present |
| per-method `ensemble_predictions_<method>.csv` | present |
| per-method ensemble prediction plots | present |
| `evaluate_models/leaderboard.csv` | present |
| `evaluate_models/best_model.json` | present |
| `evaluate_models/best_model.joblib` | present |
| `evaluate_models/metrics_by_candidate.json` | present |
| `evaluate_models/evaluation_predictions.csv` | present |
| `evaluate_models/evaluation_report.json` | present |
| root `metrics.json` | present |
| root `manifest.json` | present |

## Result

Pass. The local training pipeline runs the intended training stages and does not
produce inference outputs. Validation prediction tables include `actual`,
`prediction`, `residual`, and `abs_error`. `feature_spec.json` and
`data_quality_summary.json` include holdout split metadata. `tabular_infer_template`
remains the separate inference path.

`model.search.enabled=true` is rejected by the primary local training pipeline.
Optimization remains P2 roadmap scope.
