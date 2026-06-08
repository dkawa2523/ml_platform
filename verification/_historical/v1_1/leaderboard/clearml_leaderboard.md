# V1.1 ClearML Leaderboard Compatibility

Run date: 2026-05-25 00:39:39 +09:00
Git commit: 0756d3b

## Scope

This records ClearML compatibility for V1.1 leaderboard mode after the local implementation change.

No model-specific template, dataset-specific template, ensemble template, or leaderboard-specific template was added.

## Template Dry-Run

Command:

```powershell
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config\profiles\clearml-dev.yaml --dry-run
```

Result: pass.

The dry-run still reported exactly four templates:

| Template | Entry point | Relevant parameters |
| --- | --- | --- |
| `tabular_train_template` | `clearml/app.py` | `Model/name`, `Model/params`, `Model/candidates`, `Model/selection_metric` |
| `tabular_eval_template` | `clearml/app.py` | `Model/artifact_path` |
| `tabular_infer_template` | `clearml/app.py` | `Model/artifact_path`, `Output/prediction_name` |
| `tabular_pipeline_template` | `clearml/pipelines.py` | `Model/name`, `Model/params`, `Model/candidates`, `Model/selection_metric` |

## ClearML Artifact Path

`leaderboard.csv` is returned from package code as:

```text
RunResult.tables["leaderboard"]
```

`clearml/reports.py` uploads every `RunResult.tables` entry with:

```text
adapter.upload_artifact(name, path)
```

Therefore the leaderboard is reported as a ClearML artifact named `leaderboard`, using the same generic table artifact path already used by validation/evaluation/prediction tables.

## UI Parameter Shape

Comparison mode uses the existing `Model` group:

| Parameter | Product meaning |
| --- | --- |
| `Model/candidates` | JSON list of model names, for example `["linear", "ridge", "random_forest"]` |
| `Model/params` | JSON object keyed by model name in comparison mode |
| `Model/selection_metric` | `rmse`, `mae`, or `r2`; default is `rmse` |

Example:

```json
{
  "Model/candidates": "[\"linear\", \"ridge\", \"random_forest\"]",
  "Model/params": "{\"ridge\":{\"alpha\":1.0},\"random_forest\":{\"n_estimators\":50,\"random_state\":42,\"n_jobs\":1}}",
  "Model/selection_metric": "rmse"
}
```

## Real Server Status

This change was verified by local execution, tests, template dry-run, and code-path review. A new ClearML dev server clone-run was not executed in this turn.

Previous V1 ClearML verification already confirmed the generic `leaderboard` artifact upload path for comparison mode. The V1.1 change keeps that reporting path and only changes the supported candidate input shape to list-of-model-names with model-keyed params.

## Next ClearML Check

Before declaring remote V1.1 leaderboard fully measured, run one dev `tabular_train_template` clone with:

- Agent-reachable `Input/clearml_dataset_id`
- `Input/dataset_file=sample_train.csv`
- `Model/candidates=["linear","ridge","random_forest","gradient_boosting","lasso","elasticnet","extra_trees","knn","svr","mlp"]`
- `Model/params` keyed by model name
- `Model/selection_metric=rmse`

Expected ClearML artifacts:

- `leaderboard`
- `model`
- `model_info`
- `metrics`
- `manifest`
- `validation_predictions`

## Decision

ClearML template and report compatibility is ready. Real dev server rerun is the remaining operational verification step for the new list-of-model-names UI input shape.
