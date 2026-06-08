# V2.3 ClearML Pipeline: compare

Date: 2026-06-02
Code commit: `f94dea7`
Template: `tabular_pipeline_template`
Dataset: Agent-reachable dev Dataset ID, redacted
Queue: `default`

## Result

- status: completed
- pipeline_mode: `compare`
- controller task: `8f54c9e9faea4cfd99a50bd542a026a1`
- controller URL: http://localhost:8080/projects/a2efd51096e24eceb0ac39dedbc96c2e/experiments/8f54c9e9faea4cfd99a50bd542a026a1/output/log
- pipeline URL: http://localhost:8080/pipelines/a2efd51096e24eceb0ac39dedbc96c2e/experiments/8f54c9e9faea4cfd99a50bd542a026a1

## Step Tasks

| step | task id | status | artifacts |
| --- | --- | --- | --- |
| train | `64db6fb6306543c68903ec78f0d25870` | completed | `leaderboard`, `model`, `model_info`, `metrics`, `manifest`, `validation_predictions`, `config` |
| eval | `89d325c65dcb4439b1b55cf1be4c1c91` | completed | `evaluation_predictions`, `metrics`, `manifest`, `config` |
| infer | `f0c06dceb41d4880b69d06067a364f5d` | completed | `predictions`, `manifest`, `config` |

## Handoff

- train used `Model/candidates=["linear", "ridge"]`.
- train produced `leaderboard` and saved the selected best model as the standard `model` artifact.
- eval and infer received `Model/artifact_path=${train.artifacts.model.url}`.

## Notes

- No separate leaderboard step or template was created.
