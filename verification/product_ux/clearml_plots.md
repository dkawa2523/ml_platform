# ClearML Plots / Tables Reporting Verification

Status: repo-side verified; remote UI verification pending.

## Scope

Current reporting is handled only in `clearml/reports.py` and `clearml/adapter.py`.
Package code under `pkgs/` remains ClearML-free and returns `RunResult`
with metrics, artifacts, tables, and plots.

## Expected ClearML UI

- `preprocess_features`
  - Scalars: feature row/count metrics from `feature_summary.json`
  - Tables: `feature_summary_table`, `missing_rate_by_column`, `feature_type_counts`
  - Plots/images: `missing_rate_by_column_bar`
- `train_<model>`
  - Scalars: `rmse`, `mae`, `r2`
  - Tables: `metrics_table`, `validation_predictions`, optional `feature_importance`
  - Plots: native prediction-vs-actual/residual histogram, validation PNGs, optional feature importance
- `build_ensemble`
  - Scalars: ensemble metrics per method
  - Tables: `ensemble_metrics_table`, `ensemble_predictions_<method>`, members, weights
  - Plots/images: ensemble prediction plots, `ensemble_metrics_bar`, weight bars
- `evaluate_models`
  - Scalars: candidate metrics, ensemble metrics, best model metrics
  - Tables: `leaderboard_table`, `metrics_by_candidate`, `evaluation_summary`, `evaluation_predictions`
  - Plots/images: native best prediction plots, `metrics_by_candidate_bar`, best PNGs
- `tabular_infer`
  - Tables: `predictions_table`, `prediction_summary_table`, `prediction_preview_table`
  - Plots/images: native prediction distribution, `prediction_distribution_histogram`

## Local Verification

- `python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run`
- `python clearml/pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q`
- `rg -n "from clearml|import clearml|PipelineController|StorageManager" pkgs/core pkgs/tabular`

## Remote Verification

Pending. Run `template/tabular_train_pipeline` and `template/tabular_infer` on the
dev ClearML server, then confirm each stage task shows its own Scalars, Tables,
and Plots/Images. If PNG images appear outside the Plotly-style PLOTS panel, use
the native CSV-derived scatter/histogram plots as the PLOTS gate evidence.
