# V2 Remote ClearML UI Review

Date: 2026-06-01T02:00:00+09:00
Git commit under test: `d864267`

Direct browser / screenshot tooling was not available in this Codex session.
This review is read-only and uses ClearML task URLs plus SDK-visible UI metadata:
task status, configuration parameters, scalar names, artifact names, and sanitized
console summaries. No screenshots or raw logs were saved.

Read-only recheck: 2026-06-01. The ClearML SDK was used only to read metadata
that is shown in the dev UI; no task mutation, clone, enqueue, archive, delete,
reset, or cleanup action was performed.

## Checked Tasks And Pipeline

| Run | Task ID | Status | UI URL |
| --- | --- | --- | --- |
| optimization random train | `90b60c3aa6e94980b8ccb57f8f8297b2` | completed | http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/90b60c3aa6e94980b8ccb57f8f8297b2/output/log |
| optimization grid train | `cf5616f7025d4bd498fa8d7be8cb2528` | completed | http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/cf5616f7025d4bd498fa8d7be8cb2528/output/log |
| chunked infer | `6433f95f018042309544d1ec82091518` | completed | http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/6433f95f018042309544d1ec82091518/output/log |
| optimization pipeline | `0154d6206bc14677aee172eef89609bf` | completed | http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/0154d6206bc14677aee172eef89609bf/output/log |

All four checked runs are in `completed` status.

## UI Parameter Review

Configuration / Hyperparameters are grouped under the existing `Input`, `Run`,
`Model`, and `Output` sections. No model-, optimization-, dataset-, or
pipeline-specific template was needed.

- Optimization train uses `Model/search_enabled`, `Model/search_method`,
  `Model/search_space`, `Model/max_trials`, and `Model/selection_metric`.
- Chunked infer uses `Model/artifact_path`, `Output/prediction_name`, and
  `Output/chunk_size`.
- Pipeline uses `Input/train_dataset_file`, `Input/eval_dataset_file`,
  `Input/infer_dataset_file`, and passes `Model/search_*` only to the train
  step.

The parameter surface is acceptable for V2, but the train `Model` group is dense.
Operators should use `verification/v2_remote/parameter_sets.md` or the README
examples when editing `Model/search_space`.

Read-only metadata confirmed the UI parameter groups contain only the existing
`Input`, `Run`, `Model`, and `Output` keys. No unsupported `Run/profile`,
`Run/output_dir`, `Output/artifact_name`, `Output/report_plots`, or
`Output/register_model` key was needed for the V2 remote gate.

## Metrics Review

Optimization random/grid train tasks expose scalar series:

- `metrics/mae`
- `metrics/rmse`
- `metrics/r2`

Infer tasks do not report scalar metrics, which is expected for pure prediction
runs. Evaluation metrics for the optimization pipeline are expected on the eval
step task rather than the parent pipeline controller task.

## Artifact Review

Optimization random/grid train artifacts are visible by artifact name:

- `optimization_trials`
- `optimization_summary`
- `best_params`
- `model`
- `model_info`
- `metrics`
- `manifest`
- `validation_predictions`
- `config`

Chunked infer artifacts are visible by artifact name:

- `predictions`
- `manifest`
- `config`

Artifact check matrix:

| Run | Confirmed artifact keys |
| --- | --- |
| optimization random train | `best_params`, `config`, `manifest`, `metrics`, `model`, `model_info`, `optimization_summary`, `optimization_trials`, `validation_predictions` |
| optimization grid train | `best_params`, `config`, `manifest`, `metrics`, `model`, `model_info`, `optimization_summary`, `optimization_trials`, `validation_predictions` |
| chunked infer | `config`, `manifest`, `predictions` |
| optimization pipeline | parent controller has no required artifacts; step artifacts are the source of train/eval/infer outputs |

The artifact names are readable in ClearML UI and align with the product
contracts. The parent pipeline controller task has no required artifacts; the
step tasks are the source of train/eval/infer artifacts.

## Pipeline Graph And Step Details

The pipeline controller task completed and its console summary records the fixed
graph:

```text
Launching step [train]
Launching step [eval]
eval receives Model/artifact_path=${train.artifacts.model.url}
Launching step [infer]
infer receives Model/artifact_path=${train.artifacts.model.url}
Process completed successfully
```

This is sufficient evidence that the V2 remote pipeline ran as
`train -> eval -> infer` with model artifact handoff. Final human UI review
should open the pipeline URL and inspect Step details for the train HPO
artifacts, eval metrics, and infer predictions.

## Console Log Review

Per-task verification files include sanitized console tails. They show:

- dev worker pulled each task
- GitHub `main` was checked out at `d864267`
- environment setup completed
- Dataset access completed
- task or pipeline process completed successfully

The saved logs are enough to classify failures at a high level without storing
raw agent config or credentials.

## Product Assessment

V2 remote UI gate is acceptable:

- V2.1 optimization artifacts are visible and named clearly.
- V2.2 chunked inference exposes the `predictions` artifact.
- Metrics are visible where expected.
- The pipeline graph remains simple and understandable.
- Console logs are sufficient for first-pass failure triage.

No code fix is required. Documentation is sufficient if operators follow
`verification/v2_remote/parameter_sets.md`.

## Required Fixes

None.

## Docs-Only Items

- Keep `verification/v2_remote/parameter_sets.md` as the operator runbook for
  exact V2 remote gate parameters.
- If screenshots are required for a release package, add sanitized human-captured
  images later; do not store raw logs or credentials.

## Code Fixes

None required.

## Follow-up

- Optional: add sanitized screenshots from a human UI session if a release
  package requires visual evidence.
- Optional: reduce future train UI density by replacing the four `Model/search_*`
  parameters with one JSON parameter, but do not change this for the current V2
  gate.
