# V2.3 ClearML Pipeline UI Review

> Historical note: this file reviews the deprecated V2.3 compatibility full-run
> flow and `Run/pipeline_mode`. It is not current product readiness evidence for
> the official stage-based training or optimization pipelines.

Date: 2026-06-02
Scope: ClearML dev only
Prod access: not touched
Screenshots: none saved
Secrets/Dataset IDs: not stored

This review used ClearML SDK metadata for the Pipeline-tab draft and the four
verified V2.3 pipeline runs. No task was deleted, archived, reset, or cleaned.

## Reviewed Objects

| object | task id | status |
| --- | --- | --- |
| `tabular_pipeline_template` Pipeline-tab draft | `0cf37fc9b7084842a58862fddd52261f` | created |
| single pipeline | `ca43cf91bbce40d28568afa063dcbae3` | completed |
| compare pipeline | `8f54c9e9faea4cfd99a50bd542a026a1` | completed |
| ensemble pipeline | `8639e65cb2744820a3154c19b513c8f3` | completed |
| optimize pipeline | `ed8e23088e28460c8c6700610f6c2bc6` | completed |

## Hyperparameters

The Pipeline-tab draft exposes 24 user-facing parameters:

| group | count | parameters |
| --- | ---: | --- |
| Run | 4 | `Run/task`, `Run/name`, `Run/seed`, `Run/pipeline_mode` |
| Input | 6 | `Input/clearml_dataset_id`, `Input/train_dataset_file`, `Input/eval_dataset_file`, `Input/infer_dataset_file`, `Input/target_column`, `Input/id_columns` |
| Model | 12 | `Model/name`, `Model/params`, `Model/candidates`, `Model/selection_metric`, `Model/search_enabled`, `Model/search_method`, `Model/search_space`, `Model/max_trials`, `Model/ensemble_enabled`, `Model/ensemble_method`, `Model/ensemble_top_k`, `Model/feature_preset` |
| Output | 2 | `Output/prediction_name`, `Output/chunk_size` |

ClearML also displays internal PipelineController parameters such as
`pipeline/default_queue`, `pipeline/target_project`, and `properties/version`.
These are not product parameters.

## Mode Review

| mode | UI operation | result |
| --- | --- | --- |
| `single` | set `Run/pipeline_mode=single`, use `Model/name` and `Model/params` | clear |
| `compare` | set `Run/pipeline_mode=compare`, set `Model/candidates` | usable, but JSON candidates need docs |
| `ensemble` | set `Run/pipeline_mode=ensemble`, set candidates and `Model/ensemble_*` | usable |
| `optimize` | set `Run/pipeline_mode=optimize`, set `Model/search_space` and search options | usable, but parent UI can show `Model/search_enabled=false` while the train step is normalized to true |

## Artifacts And Metrics

| mode | train artifacts | eval artifacts | infer artifacts | scalars |
| --- | --- | --- | --- | --- |
| single | `model`, `model_info`, `metrics`, `manifest`, `validation_predictions`, `config` | `evaluation_predictions`, `metrics`, `manifest`, `config` | `predictions`, `manifest`, `config` | train/eval `mae`, `rmse`, `r2` |
| compare | single artifacts plus `leaderboard` | `evaluation_predictions`, `metrics`, `manifest`, `config` | `predictions`, `manifest`, `config` | train/eval `mae`, `rmse`, `r2` |
| ensemble | compare artifacts plus `ensemble_info`, `ensemble_predictions`, base models | `evaluation_predictions`, `metrics`, `manifest`, `config` | `predictions`, `manifest`, `config` | train/eval `mae`, `rmse`, `r2` |
| optimize | `optimization_trials`, `optimization_summary`, `best_params`, `model`, `model_info`, `metrics`, `manifest`, `validation_predictions`, `config` | `evaluation_predictions`, `metrics`, `manifest`, `config` | `predictions`, `manifest`, `config` | train/eval `mae`, `rmse`, `r2` |

Controller tasks do not aggregate artifacts or scalars. Operators must open step
details to inspect train/eval/infer outputs.

## Pipeline Graph And Logs

- The product graph remains simple: train, eval, infer.
- ClearML logs show each step launch and the parameter override dictionary.
- eval and infer receive `Model/artifact_path=${train.artifacts.model.url}`.
- The controller console includes the checked-out commit, step launches, and
  parameter overrides, so failures should be traceable from controller plus step
  logs.
- ClearML adds a parent reference from train to infer because infer consumes the
  train artifact. The console reports `Node "infer" missing parent reference,
  adding: {'train'}`. This is operationally correct but slightly noisy.

## Good Points

- `Run/pipeline_mode` is visible and makes the intended flow clear.
- All four modes run from the same Pipeline-tab draft.
- No model-, ensemble-, optimize-, leaderboard-, or dataset-specific template is
  needed.
- Artifacts are visible where they are produced: train for model/leaderboard/
  ensemble/search, eval for `evaluation_predictions`, infer for `predictions`.
- Metrics are visible on train and eval step Scalars.
- Console logs are useful enough for failure triage.
- Worker requirement does not increase beyond the existing controller plus step
  tasks model.

## Confusing Points

- The Model group is dense because it covers single, compare, ensemble, and
  optimize in one template.
- `Model/name` and `Model/candidates` can be confusing: in compare/ensemble,
  candidates drive training while `Model/name` remains visible.
- `Model/params` needs JSON knowledge, especially when params are keyed by model.
- Mode-specific unused parameters remain visible. This is acceptable for V2.3
  but requires docs.
- Parent controller tasks have no required artifacts/scalars, so operators must
  know to click step details.
- `optimize` normalizes search to enabled in the train step even if the parent
  UI parameter still shows `Model/search_enabled=false`.
- Historical dev objects may still show a non-Pipeline-tab
  `tabular_pipeline_template`; operators should use the Pipeline tab draft.

## Parameter Reduction Candidates

- Do not remove parameters in V2.3; the current surface is still manageable.
- Consider hiding or de-emphasizing `Run/task` for pipeline users in a later
  polish pass.
- Consider whether `Model/feature_preset` belongs in Pipeline UI or task config
  only.
- Do not add `params_by_model`, `save_leaderboard`, `save_predictions`,
  `artifact_name`, `report_plots`, or `register_model` in V2.3.

## Docs Candidates

- Add a compact operator table: mode -> required parameters -> expected step
  artifacts.
- Explain that parent controller artifacts are intentionally empty and step
  details are the source of truth.
- Explain `Model/name` vs `Model/candidates`.
- Provide JSON examples for `Model/candidates`, keyed `Model/params`, and
  `Model/search_space`.
- Mention that ClearML may show an extra train dependency for infer because
  infer consumes the train model artifact.

## Code Candidates

- Update controller parameters with resolved effective mode settings, so
  `Run/pipeline_mode=optimize` also shows effective `Model/search_enabled=true`
  on the parent task.
- Explicitly set infer parents to include both `eval` and `train` to avoid the
  ClearML auto-parent console warning.
- Keep artifacts on step tasks; do not add a parent aggregation task in V2.3.

## Decision

ClearML UI status: ready for the historical V2.3 compatibility flow.

The UI is usable for single, compare, ensemble, and optimize pipeline execution.
The remaining issues are documentation/polish items, not release blockers.
