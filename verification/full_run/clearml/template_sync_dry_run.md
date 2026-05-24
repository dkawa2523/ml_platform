# ClearML Template Sync Dry-Run

## Run Metadata

- Date: 2026-05-24
- Profile: `config/profiles/clearml-dev.yaml`
- Command: `python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run`
- Status: succeeded
- Secrets: not printed or stored

## Templates

| Template | Type | Project | Entry point | Args |
| --- | --- | --- | --- | --- |
| `tabular_train_template` | training | `MLPlatform/Dev/Templates` | `clearml/app.py` | `--task config/tasks/tabular_train.yaml --profile config/profiles/clearml-dev.yaml` |
| `tabular_eval_template` | testing | `MLPlatform/Dev/Templates` | `clearml/app.py` | `--task config/tasks/tabular_eval.yaml --profile config/profiles/clearml-dev.yaml` |
| `tabular_infer_template` | inference | `MLPlatform/Dev/Templates` | `clearml/app.py` | `--task config/tasks/tabular_infer.yaml --profile config/profiles/clearml-dev.yaml` |
| `tabular_pipeline_template` | controller | `MLPlatform/Dev/Templates` | `clearml/pipelines.py` | `--task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml` |

Template count stayed fixed at four.

## UI Parameters

- Groups observed: `Input`, `Run`, `Model`, `Output`
- `Run/queue` is not exposed; queue remains profile and Agent configuration.
- No model-specific or dataset-specific template was introduced.

## Pipeline Dry-Run

- Project: `MLPlatform/Dev/Pipelines`
- Queue: `default`
- Steps: `train -> eval -> infer`
- Handoff: eval and infer receive `${train.artifacts.model.url}` as `Model/artifact_path`.

## Decision

Dry-run is acceptable for v1.
