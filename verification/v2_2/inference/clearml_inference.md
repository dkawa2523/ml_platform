# V2.2 ClearML Inference Verification

Date: 2026-05-28 JST

## Dry-Run Command

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

`tabular_infer_template` exposes inference controls under the existing groups:

- `Model/artifact_path`
- `Output/prediction_name`
- `Output/chunk_size`

No inference-specific, model-specific, ensemble-specific, optimization-specific, or dataset-specific template was added.

## ClearML Artifact Expectations

The infer task uploads the generic `predictions` table artifact. The physical file name is controlled by `Output/prediction_name`; the table schema includes:

- original input columns
- `prediction`
- `model_name`
- `artifact_kind`
- `model_artifact_id`
- `prediction_run_id`

`Output/chunk_size` chunks prediction and CSV writing after the input table is loaded. It is not a streaming reader or serving API.

## Remote Status

ClearML dev remote execution was not run in this implementation turn. The code path is dry-run ready; a dev-server gate should clone `tabular_infer_template`, set an Agent-reachable dataset and `Model/artifact_path`, optionally set `Output/chunk_size`, and confirm the `predictions` artifact in the UI.

V2.2 ClearML inference status: dry-run ready, remote pending.
