# V2.0 ClearML Pipeline Verification

Date: 2026-05-26 JST

## Dry-Run Commands

```powershell
.\.venv\Scripts\python.exe scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
.\.venv\Scripts\python.exe clearml/pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
```

## Template Dry-Run Result

Status: pass.

The template set remains fixed to four task-type templates:

- `tabular_train_template`
- `tabular_eval_template`
- `tabular_infer_template`
- `tabular_pipeline_template`

The pipeline template still uses `clearml/pipelines.py` as entrypoint. No model-specific, dataset-specific, leaderboard-specific, or ensemble-specific template is introduced.

## Pipeline Dry-Run Result

Status: pass.

The planned DAG remains fixed:

```text
train -> eval -> infer
```

The eval and infer steps receive the train step model artifact through:

```text
Model/artifact_path=${train.artifacts.model.url}
```

Comparison and ensemble parameters are passed only to the train step when supplied from the pipeline UI:

- `Model/name`
- `Model/params`
- `Model/candidates`
- `Model/selection_metric`
- `Model/ensemble_enabled`
- `Model/ensemble_method`
- `Model/ensemble_top_k`
- `Model/feature_preset`

## Remote Execution Plan

Remote ClearML execution should verify these three pipeline runs on the dev queue:

| Mode | Expected train artifacts | Expected eval/infer artifacts |
| --- | --- | --- |
| Single model | `model`, `model_info`, `metrics`, `validation_predictions` | `evaluation_predictions`, `predictions` |
| Comparison / best model | `leaderboard`, `model`, `model_info`, `metrics`, `validation_predictions` | `evaluation_predictions`, `predictions` |
| Weighted ensemble | `leaderboard`, `ensemble_predictions`, `base_model_*`, `model`, `model_info`, `metrics` | `evaluation_predictions`, `predictions` |

The parent PipelineController task is not expected to aggregate step artifacts in V2.0. Operators should inspect the pipeline graph and step task artifacts.

## Operational Conditions

- Use dev project and dev queue only.
- The queue needs enough worker capacity for controller plus step execution.
- The ClearML Dataset artifact URL must be reachable from the Agent.
- Do not delete, archive, reset, or cleanup ClearML tasks as part of verification.

V2.0 ClearML dry-run status: ready for dev remote execution.
