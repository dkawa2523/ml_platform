# V1 ClearML Pipeline Verification Summary

## Run Metadata

- Date: 2026-05-24
- Stamp: `20260524T144516Z`
- Project: `MLPlatform/Dev/Pipelines`
- Template: `tabular_pipeline_template`
- Queue: `default`
- Template sync: completed before pipeline execution
- Dataset: Agent-reachable dev Dataset ID, value redacted in markdown
- Raw logs: not stored
- Secrets: not stored; credential environment lines omitted from console tails
- Worker note: remote pipeline uses controller plus step tasks on the same queue, so at least two worker slots are required.

## Pipeline Success Matrix

| Model | Overall | Pipeline Task ID | Train | Eval | Infer |
| --- | --- | --- | --- | --- | --- |
| `linear` | `completed` | `130935055ba14282b8f2ee1d29c5e723` | `completed` | `completed` | `completed` |
| `ridge` | `completed` | `b1ac57b796b44187946030c1270614db` | `completed` | `completed` | `completed` |
| `random_forest` | `completed` | `7b698322f4f34a5bbeb7e5b24f773996` | `completed` | `completed` | `completed` |
| `gradient_boosting` | `completed` | `634f8d8ecf2a40efb2a1d63af154d578` | `completed` | `completed` | `completed` |

## Model Pipeline Evaluation

All four V1 official supported models were executed through the same fixed `train -> eval -> infer` ClearML pipeline template. Each train step produced a `model` artifact, each eval step reported metrics, and each infer step uploaded `predictions`.

## Pipeline UI Operability

- Pipeline graph is the fixed three-step DAG: `train -> eval -> infer`.
- Step task URLs are recorded in each per-model markdown file.
- Metrics are visible on eval step tasks as ClearML scalars under `metrics/*`.
- Artifacts are visible per step: train has `model`, eval has `evaluation_predictions`, infer has `predictions`.
- Console logs are available in ClearML UI; markdown keeps sanitized tails only.

## Comparison Mode Pipeline Decision

- Official V1 pipeline gate uses single model pipelines for the four supported models.
- Comparison mode pipeline is already covered by `verification/v1/models/leaderboard_verification.md`; it is not repeated here to keep this gate focused and avoid unnecessary remote runs.
- V1 accepts comparison mode as a train-task capability, with pipeline comparison available but not required for official model support.

## Issues

- No failures found.
- No code changes were required.

## Decision

- V1 pipeline ready: `yes`
