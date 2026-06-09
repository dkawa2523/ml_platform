# Results And Plots Verification

Date: 2026-06-08

Scope: Phase 4 product UX cleanup for training results, metrics, tables, and
minimal plots.

## Expected Result Surface

Training pipeline artifacts and tables:

- `feature_summary.json`
- `model_refs.json`
- `metrics_by_model.json`
- `metrics_by_candidate.json`
- `leaderboard.csv`
- `best_model.json`
- `ensemble_refs.json`
- `ensemble_info_by_method.json`
- `evaluation_report.json`
- `evaluation_predictions.csv`
- `metrics.json`
- `manifest.json`

Inference remains separate and keeps `predictions.csv` as the prediction output.

ClearML display:

- scalar metrics from each stage result
- `metrics_by_model/rmse`, `metrics_by_model/mae`, and `metrics_by_model/r2`
  series by model or ensemble method
- `metrics_by_candidate/rmse`, `metrics_by_candidate/mae`, and
  `metrics_by_candidate/r2` series by candidate
- `best_model` scalar summary
- `ensemble` scalar summary for each ensemble method
- table reports for `leaderboard`, train-stage `validation_predictions`,
  `evaluation_predictions`, per-method `ensemble_predictions_<method>`, and
  `predictions`
- native ClearML plot reports for prediction-vs-actual and residual histogram
  from prediction tables when `Output/report_plots=true`
- plot artifacts/media for `metrics_by_candidate_bar`, compatibility
  `metrics_by_model_bar`, `prediction_vs_actual`, and `residual_histogram`

## Commands

```powershell
.\.venv\Scripts\python.exe scripts\make_sample_data.py
.\.venv\Scripts\python.exe scripts\local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
.\.venv\Scripts\python.exe clearml\pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
git diff --check
rg -n "from clearml|import clearml|PipelineController|StorageManager" pkgs/core pkgs/tabular
```

## Result

- Sample data generation: pass.
- Local training pipeline: pass.
- Local artifacts include `feature_summary`, `model_refs`, `metrics_by_model`,
  `metrics_by_candidate`, `leaderboard`, `best_model_json`, `ensemble_refs`,
  `ensemble_info_by_method`, `evaluation_report`, `evaluation_predictions`,
  `metrics`, and `manifest`.
- Local plots include `metrics_by_candidate_bar`, compatibility
  `metrics_by_model_bar`, `prediction_vs_actual`, and `residual_histogram`.
- Tests: `52 passed`.
- Exact `validation_predictions` tables are reported on individual train stages;
  aggregate parent keys such as `validation_predictions_linear` remain uploaded
  artifacts/tables only, avoiding noisy ClearML table spam.
- Template sync dry-run: pass.
- ClearML pipeline dry-run: pass.
- `git diff --check`: pass with line-ending warnings only.
- ClearML import boundary: no matches under `pkgs/core` or `pkgs/tabular`.
- Remote ClearML UI execution: not run in this phase.
