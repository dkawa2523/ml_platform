# ClearML Plots / Tables Reporting Verification

Status: local and dry-run verification current; remote evidence must be
recorded fresh after template sync.

## Scope

Current reporting is handled only in `clearml/reports.py` and `clearml/adapter.py`.
Package code under `pkgs/` remains ClearML-free and returns `RunResult`
with metrics, artifacts, tables, and plots.

## Expected ClearML UI

- `preprocess_features`
  - Scalars: feature row/count metrics from `feature_summary.json`
  - Tables: `feature_summary_table`, `data_quality_summary_table`,
    `data_quality_warnings`, `missing_rate_by_column`, `feature_type_counts`
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
  - Tables: `leaderboard_table`, `metrics_by_candidate`, `evaluation_summary`,
    `leaderboard_decision_summary_table`, `best_vs_ensemble_summary_table`,
    `evaluation_predictions`
  - Plots/images: native best prediction plots, `metrics_by_candidate_bar`, best PNGs
- `tabular_infer`
  - Tables: `schema_check_summary_table`, `predictions_table`,
    `source_summary_table`, `prediction_summary_table`, `prediction_preview_table`
  - Plots/images: native prediction distribution, `prediction_distribution_histogram`

## Local Verification

- `python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run`
- `python scripts/clearml_pipeline.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q`
- `rg -n "from clearml|import clearml|PipelineController|StorageManager" pkgs/core pkgs/tabular`

## Remote Verification

Record fresh remote evidence after syncing templates from the branch being
released:

- training Pipeline task ID and commit
- graph shape and queues
- key stage tables/plots listed above
- inference task ID using `source_type=task_id`, `model_selector=best`
- sanitized failure logs, if any
