# Results And Plots Verification

Date: 2026-06-08

Scope: Phase 4 product UX cleanup for training results, metrics, tables, and
minimal plots.

## Expected Result Surface

Training pipeline artifacts and tables:

- `feature_summary.json`
- `model_refs.json`
- `metrics_by_model.json`
- `leaderboard.csv`
- `best_model.json`
- `ensemble_info.json`
- `evaluation_report.json`
- `evaluation_predictions.csv`
- `metrics.json`
- `manifest.json`

Inference remains separate and keeps `predictions.csv` as the prediction output.

ClearML display:

- scalar metrics from each stage result
- `metrics_by_model/rmse`, `metrics_by_model/mae`, and `metrics_by_model/r2`
  series by model
- `best_model` scalar summary
- `ensemble` scalar summary when an ensemble is present
- table reports for `leaderboard`, `evaluation_predictions`, and `predictions`
- media reports for `metrics_by_model_bar`, `prediction_vs_actual`, and
  `residual_histogram` when `Output/report_plots=true`

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
  `leaderboard`, `best_model_json`, `ensemble_info`, `evaluation_report`,
  `evaluation_predictions`, `metrics`, and `manifest`.
- Local plots include `metrics_by_model_bar`, `prediction_vs_actual`, and
  `residual_histogram`.
- Tests: `59 passed`.
- Template sync dry-run: pass.
- ClearML pipeline dry-run: pass.
- `git diff --check`: pass with line-ending warnings only.
- ClearML import boundary: no matches under `pkgs/core` or `pkgs/tabular`.
- Remote ClearML UI execution: not run in this phase.
