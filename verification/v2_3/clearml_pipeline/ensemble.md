# V2.3 ClearML Pipeline: ensemble

Date: 2026-06-02
Code commit: `f94dea7`
Template: `tabular_pipeline_template`
Dataset: Agent-reachable dev Dataset ID, redacted
Queue: `default`

## Result

- status: completed
- pipeline_mode: `ensemble`
- controller task: `8639e65cb2744820a3154c19b513c8f3`
- controller URL: http://localhost:8080/projects/a2efd51096e24eceb0ac39dedbc96c2e/experiments/8639e65cb2744820a3154c19b513c8f3/output/log
- pipeline URL: http://localhost:8080/pipelines/a2efd51096e24eceb0ac39dedbc96c2e/experiments/8639e65cb2744820a3154c19b513c8f3

## Step Tasks

| step | task id | status | artifacts |
| --- | --- | --- | --- |
| train | `5e7db002aebe402ea1d00bbf05afea39` | completed | `leaderboard`, `ensemble_info`, `ensemble_predictions`, `base_model_1_linear`, `base_model_2_ridge`, `model`, `model_info`, `metrics`, `manifest`, `validation_predictions`, `config` |
| eval | `bbb4da916be6451db6ce72d0fa2729cf` | completed | `evaluation_predictions`, `metrics`, `manifest`, `config` |
| infer | `72cf842561e24f048a474d3dc4c74181` | completed | `predictions`, `manifest`, `config` |

## Handoff

- train used `Model/candidates=["linear", "ridge"]`.
- train used `Model/ensemble_enabled=true`, `Model/ensemble_method=mean_topk`, and `Model/ensemble_top_k=2`.
- train saved the ensemble as the standard `model` artifact.
- eval and infer received `Model/artifact_path=${train.artifacts.model.url}`.

## Notes

- No separate ensemble step, child task, or `train_ensemble_full` flow was created.
