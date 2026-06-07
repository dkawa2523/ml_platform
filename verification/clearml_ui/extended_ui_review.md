# Extended ClearML UI review

> Historical note: this file reviews the old four-template UI surface and fixed
> `train -> eval -> infer` compatibility pipeline. It is not current product
> readiness evidence for the stage-based training or optimization pipelines.

Run date: 2026-05-25 08:45 +09:00
Git commit: 0756d3b

## Scope

This review covers the current extended surface after V1.1/V1.2/V1.3 changes:

- additional sklearn models through `Model/name`
- comparison mode through `Model/candidates`
- `leaderboard.csv` table artifact
- `mean_topk` and `weighted` ensemble modes
- standardized inference `predictions.csv`
- historical compatibility fixed train -> eval -> infer pipeline template

No screenshot was captured. No secrets, raw logs, or screenshots are stored.

## Important limitation

The active working tree contains uncommitted changes, while
`config/profiles/clearml-dev.yaml` points ClearML Agent execution at:

```text
repository=https://github.com/dkawa2523/ml_platform.git
branch=main
working_dir=.
```

Because the Agent clones GitHub `main`, a real dev-server task or pipeline run
before commit/push would not validate the current local code. This review
therefore records dry-run UI/template coverage and existing remote evidence, and
marks the extended remote run as pending after commit/push.

## Template dry-run

Command:

```powershell
.\.venv\Scripts\python.exe scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
```

Result: pass.

Exactly four templates are exposed:

| Template | Type | Entry point | Parameters |
| --- | --- | --- | --- |
| `tabular_train_template` | training | `clearml/app.py` | Run, Input, Model |
| `tabular_eval_template` | testing | `clearml/app.py` | Run, Input, Model |
| `tabular_infer_template` | inference | `clearml/app.py` | Run, Input, Model, Output |
| `tabular_pipeline_template` | controller | `clearml/pipelines.py` | Run, Input, Model |

No model-specific, dataset-specific, ensemble-specific, or leaderboard-specific
template was added.

## UI parameter review

The parameter groups remain within the approved ClearML groups:

- `Input`
- `Run`
- `Model`
- `Output`

Single-model execution is controlled by:

- `Model/name`
- `Model/params`

Comparison mode is controlled by:

- `Model/candidates`
- `Model/selection_metric`
- model-keyed `Model/params`

Ensemble mode is controlled by:

- `Model/ensemble_enabled`
- `Model/ensemble_method`
- `Model/ensemble_top_k`

Inference naming is controlled by:

- `Output/prediction_name`

The surface is larger than MVP but still understandable because controls are
task-type based and grouped under `Model`. The most error-prone field is
`Model/params` when using comparison mode because it must be JSON keyed by model
name. This is acceptable with the current docs and examples; no extra template is
recommended.

## Pipeline dry-run

Command:

```powershell
.\.venv\Scripts\python.exe clearml/pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
```

Result: pass.

Historical compatibility pipeline graph:

```text
train -> eval -> infer
```

Artifact handoff:

- eval receives `Model/artifact_path=${train.artifacts.model.url}`
- infer receives `Model/artifact_path=${train.artifacts.model.url}`

The graph is still simple and readable. The same handoff works for single-model,
comparison best-model, and ensemble artifacts because train always publishes the
selected artifact as `model`.

## Existing remote evidence

Previously recorded dev-server evidence remains valid for the base V1 surface:

- four official models train/eval/infer completed in ClearML tasks
- four official model pipelines completed in ClearML
- comparison train produced `leaderboard`
- comparison eval/infer consumed the best model artifact
- historical compatibility fixed train -> eval -> infer pipeline graph was
  visible

Files:

- `verification/v1/clearml_tasks/summary.md`
- `verification/v1/clearml_pipelines/summary.md`
- `verification/v1/models/leaderboard_verification.md`

V1.1/V1.2/V1.3 extension evidence currently consists of local verification and
ClearML dry-run compatibility:

- `verification/v1_1/leaderboard/clearml_leaderboard.md`
- `verification/v1_2/ensemble/mean_topk_clearml_task.md`
- `verification/v1_2/ensemble/weighted_clearml_task.md`
- `verification/v1_3/inference/infer_task_review.md`

## Task success/failure

| Capability | ClearML remote status | Evidence |
| --- | --- | --- |
| single model train/eval/infer for V1 models | pass | previous remote V1 task verification |
| comparison train/eval/infer | pass | previous remote V1 task verification |
| V1.1 sklearn model task execution | pending after commit/push | local tests + template dry-run |
| `mean_topk` task execution | pending after commit/push | local tests + template dry-run |
| `weighted` task execution | pending after commit/push | local tests + template dry-run |
| V1.3 standardized infer output in ClearML | pending after commit/push | local tests + template dry-run |

## Pipeline success/failure

| Capability | ClearML remote status | Evidence |
| --- | --- | --- |
| V1 single model pipelines | pass | previous remote pipeline verification |
| comparison/best model pipeline | compatible, not repeated in this review | previous leaderboard evidence + dry-run |
| ensemble pipeline | pending after commit/push | local tests + dry-run handoff check |
| standardized infer output in pipeline | pending after commit/push | local pipeline check + dry-run |

## Artifact summary

Expected ClearML artifacts remain generic:

- train: `model`, `model_info`, `metrics`, `manifest`, `validation_predictions`
- comparison train: plus `leaderboard`
- ensemble train: plus `ensemble_predictions` and selected `base_model_*`
- eval: `metrics`, `manifest`, `evaluation_predictions`
- infer: `manifest`, optional `model_info`, `predictions`

`leaderboard.csv` and prediction tables are uploaded by `clearml/reports.py`
through the generic `RunResult.tables` path. No ClearML model-specific code is
needed.

## Operational docs check

Docs include the key operational conditions:

- remote pipeline needs enough worker slots for controller and step tasks
- ClearML Dataset artifact URLs must be reachable from Agent
- `artifact_output_uri` is output artifact storage, not Dataset storage
- host-only `localhost` URLs and host filesystem paths are not valid for Agent runs

## Issues and recommendations

Must fix before claiming extended ClearML UI/task/pipeline reverified:

- Commit and push the current V1.1/V1.2/V1.3 changes to GitHub `main`, then sync
  templates and run one dev-server gate for:
  - V1.1 model task or pipeline sample
  - comparison train with all supported candidates
  - `mean_topk` or `weighted` ensemble train/eval/infer
  - infer task confirming standardized `predictions.csv`

Docs-only sufficient:

- The current UI parameter surface is acceptable with examples. No extra template
  is needed.

Code changes needed:

- None found in this review.

Do not add:

- model-specific templates
- ensemble-specific templates
- leaderboard-specific templates
- diagnostics helpers
- new ClearML UI groups

## Decision

Local and template compatibility were ready for this historical review. Extended
ClearML remote task/pipeline verification was not complete until that phase's
code was committed, pushed, and run by the dev Agent from GitHub `main`.

Release decision for the historical extended ClearML UI gate: not ready yet for
a remote reverification claim; ready to proceed to commit/push and dev-server
rerun for that phase only.
