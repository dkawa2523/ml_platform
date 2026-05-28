# V2.1 ClearML Optimization Verification

Date: 2026-05-26 JST

## Dry-Run Commands

```powershell
.\.venv\Scripts\python.exe scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
.\.venv\Scripts\python.exe clearml/pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
```

## Dry-Run Result

Status: pass.

The template set remains fixed to four task-type templates:

- `tabular_train_template`
- `tabular_eval_template`
- `tabular_infer_template`
- `tabular_pipeline_template`

The train and pipeline template parameter surfaces include the new V2.1 Model parameters:

- `Model/search_enabled`
- `Model/search_method`
- `Model/search_space`
- `Model/max_trials`

No optimize-specific, model-specific, dataset-specific, or per-trial template is introduced.

## Pipeline Plan

The ClearML pipeline remains the fixed graph:

```text
train -> eval -> infer
```

`Model/search_*` parameters are passed only to the train step. Eval and infer continue to consume:

```text
Model/artifact_path=${train.artifacts.model.url}
```

## Remote Execution Plan

Run on the dev server and dev queue only:

1. Clone `tabular_train_template`.
2. Set `Model/search_enabled=true`, `Model/search_method=grid` or `random`, `Model/search_space`, and `Model/max_trials`.
3. Confirm artifacts `optimization_trials`, `optimization_summary`, `best_params`, `model`, `model_info`, `metrics`, and `manifest`.
4. Clone `tabular_pipeline_template` with the same search parameters.
5. Confirm train step search artifacts and eval/infer step outputs.

V2.1 ClearML dry-run status: ready for dev remote execution.
