# V1.2 Mean Top-K ClearML Compatibility

Run date: 2026-05-25 07:50:25 +09:00  
Git commit: 0756d3b

## Scope

This records ClearML compatibility for V1.2 `mean_topk` ensemble mode. A real
dev server clone-run was not executed in this implementation turn.

## Template Dry-Run

Command:

```powershell
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config\profiles\clearml-dev.yaml --dry-run
```

Result: pass.

The dry-run reported exactly four templates:

- `tabular_train_template`
- `tabular_eval_template`
- `tabular_infer_template`
- `tabular_pipeline_template`

The train template and pipeline controller expose the ensemble controls as flat
Model parameters:

- `Model/ensemble_enabled`
- `Model/ensemble_method`
- `Model/ensemble_top_k`

No ensemble-specific, model-specific, or dataset-specific template was added.

## Reporting Path

No `clearml/reports.py` change was required. The train result exposes ensemble
outputs through existing `RunResult` maps:

- `artifacts["model"]`: ensemble `model.joblib`
- `artifacts["model_info"]`: ensemble metadata
- selected base model artifacts: `base_model_<rank>_<model>`
- `tables["leaderboard"]`: `leaderboard.csv`
- `tables["ensemble_predictions"]`: `ensemble_predictions.csv`

The generic ClearML reporter uploads all artifacts and tables.

## Expected Dev Server Check

Clone `tabular_train_template` on the dev project and set:

```json
{
  "Model/candidates": "[\"linear\", \"ridge\", \"random_forest\", \"gradient_boosting\", \"lasso\", \"elasticnet\", \"extra_trees\", \"knn\", \"svr\", \"mlp\"]",
  "Model/params": "{\"ridge\":{\"alpha\":1.0},\"random_forest\":{\"n_estimators\":50,\"random_state\":42,\"n_jobs\":1},\"gradient_boosting\":{\"n_estimators\":50,\"random_state\":42},\"lasso\":{\"alpha\":0.01,\"max_iter\":5000},\"elasticnet\":{\"alpha\":0.01,\"l1_ratio\":0.5,\"max_iter\":5000,\"random_state\":42},\"extra_trees\":{\"n_estimators\":50,\"random_state\":42,\"n_jobs\":1},\"knn\":{\"n_neighbors\":5,\"weights\":\"distance\"},\"svr\":{\"kernel\":\"rbf\",\"C\":1.0,\"epsilon\":0.1,\"gamma\":\"scale\"},\"mlp\":{\"hidden_layer_sizes\":[32],\"solver\":\"lbfgs\",\"max_iter\":500,\"random_state\":42}}",
  "Model/selection_metric": "rmse",
  "Model/ensemble_enabled": true,
  "Model/ensemble_method": "mean_topk",
  "Model/ensemble_top_k": 3
}
```

Expected ClearML artifacts:

- `model`
- `model_info`
- `metrics`
- `manifest`
- `leaderboard`
- `ensemble_predictions`
- selected `base_model_*` artifacts

Eval and infer should use the produced `model` artifact exactly as they do for
single-model runs.

Expected `leaderboard` table:

- candidate model rows ranked by `Model/selection_metric`
- one `mean_topk` row with artifact name `model`

## Decision

ClearML template compatibility is ready for V1.2 `mean_topk`. Real dev server
task and pipeline verification should be run as the next operational gate.
