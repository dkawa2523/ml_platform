# ClearML Template Sync Dry-Run

## Run Metadata

- Date: 2026-05-24
- Commit: `3773e03`
- Command: `python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run`
- Status: succeeded

## Profile Values

| Key | Value |
| --- | --- |
| `clearml.project_root` | `MLPlatform/Dev` |
| `clearml.queue` | `default` |
| `clearml.repository` | `https://github.com/dkawa2523/ml_platform.git` |
| `clearml.branch` | `main` |
| `clearml.working_dir` | `.` |
| `clearml.artifact_output_uri` | `null` |
| `clearml.dataset_project` | `datasets-dev` |

## Templates

| Template | Type | Project | Entry point | Note |
| --- | --- | --- | --- | --- |
| `tabular_train_template` | `training` | `MLPlatform/Dev/Templates` | `clearml/app.py` | clone-run target |
| `tabular_eval_template` | `testing` | `MLPlatform/Dev/Templates` | `clearml/app.py` | clone-run target |
| `tabular_infer_template` | `inference` | `MLPlatform/Dev/Templates` | `clearml/app.py` | clone-run target |
| `tabular_pipeline_template` | `controller` | `MLPlatform/Dev/Templates` | `clearml/pipelines.py` | PipelineController entrypoint |

Template count stayed fixed at four.

## UI Parameters

Observed groups:

- `Input`
- `Run`
- `Model`
- `Output`

| Template | Parameters |
| --- | --- |
| `tabular_train_template` | `Run/task`, `Run/name`, `Run/seed`, `Input/local_path`, `Input/clearml_dataset_id`, `Input/dataset_file`, `Input/target_column`, `Input/feature_columns`, `Input/id_columns`, `Model/name`, `Model/params`, `Model/feature_preset` |
| `tabular_eval_template` | `Run/task`, `Run/name`, `Run/seed`, `Input/local_path`, `Input/clearml_dataset_id`, `Input/dataset_file`, `Input/target_column`, `Input/feature_columns`, `Input/id_columns`, `Model/artifact_path` |
| `tabular_infer_template` | `Run/task`, `Run/name`, `Run/seed`, `Input/local_path`, `Input/clearml_dataset_id`, `Input/dataset_file`, `Input/target_column`, `Input/feature_columns`, `Input/id_columns`, `Model/artifact_path`, `Output/prediction_name` |
| `tabular_pipeline_template` | `Run/task`, `Run/name`, `Run/seed`, `Input/clearml_dataset_id`, `Input/train_dataset_file`, `Input/eval_dataset_file`, `Input/infer_dataset_file`, `Model/name`, `Model/params`, `Model/feature_preset` |

No `Run/queue` parameter was emitted. Queue remains profile and Agent configuration.

## Decision

Dry-run definition is acceptable. Real sync succeeded after this dry-run.
