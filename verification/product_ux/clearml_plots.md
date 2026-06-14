# ClearML Plots / Tables Reporting Verification

Status: remote training and inference verified.

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

Latest training template New Run:

- Pipeline task: `cf12d910fcbf44d8a94b5b1a6cfef4ff`
- Run name: `gate_latest_20260614_214421`
- Commit: `647bcdfb53283b0fd37ab81535117661c5edfe7a`
- Result: completed
- Graph: 10 `train_<model>` tasks plus `build_ensemble_mean_topk`,
  `build_ensemble_weighted`, `build_ensemble_median`, and `evaluate_models`.
- GBM packages in task venv: `lightgbm==4.6.0`, `xgboost==3.2.0`,
  `catboost==1.2.10`.

Stage evidence:

- `stage/preprocess_features`: `feature_summary_table`,
  `missing_rate_by_column`, `feature_type_counts`.
- `stage/train_lightgbm` and `stage/train_xgboost`: metrics scalars,
  validation prediction/residual plots, feature importance table.
- `stage/build_ensemble_mean_topk`: ensemble metrics scalars,
  ensemble member/weight/prediction tables, prediction/residual plots.
- `stage/evaluate_models`: `leaderboard/table`, `leaderboard/top_k_scores`,
  `leaderboard/metric_panel`, `leaderboard/pareto_rmse_r2`,
  top-k prediction/residual plots, best-entry prediction/residual plots,
  candidate and ensemble scalar metrics.

Latest inference template New Run:

- Inference task: `f47d25d6862f4949ba56825c0ae3b002`
- Run name: `infer_gate_latest_20260614_215444`
- Source task: `cf12d910fcbf44d8a94b5b1a6cfef4ff`
- Selector: `best`
- Commit: `2d5e2f6b4950253c299500a3f667e78ecda85520`
- Result: completed
- PLOTS/TABLES: `prediction_distribution_histogram`, `prediction_preview_table`,
  `prediction_summary_table`, `predictions_table`, `source_summary_table`.
- Artifacts: `predictions`, `prediction_summary`, `prediction_preview`,
  `prediction_distribution_histogram`, `source_summary`, `feature_spec`,
  `preprocess_bundle`, `model_info`, `manifest`, `config`.
