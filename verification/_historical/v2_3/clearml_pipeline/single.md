# V2.3 ClearML Pipeline: single

Date: 2026-06-02
Code commit: `f94dea7`
Template: `tabular_pipeline_template`
Dataset: Agent-reachable dev Dataset ID, redacted
Queue: `default`

## Result

- status: completed
- pipeline_mode: `single`
- controller task: `ca43cf91bbce40d28568afa063dcbae3`
- controller URL: http://localhost:8080/projects/a2efd51096e24eceb0ac39dedbc96c2e/experiments/ca43cf91bbce40d28568afa063dcbae3/output/log
- pipeline URL: http://localhost:8080/pipelines/a2efd51096e24eceb0ac39dedbc96c2e/experiments/ca43cf91bbce40d28568afa063dcbae3

## Step Tasks

| step | task id | status | artifacts |
| --- | --- | --- | --- |
| train | `8ae320cda319477c91cff0bd894b0048` | completed | `model`, `model_info`, `metrics`, `manifest`, `validation_predictions`, `config` |
| eval | `665dc61bbacd466e8cf46afafcebffe0` | completed | `evaluation_predictions`, `metrics`, `manifest`, `config` |
| infer | `8abc07ea121f4d6e858c038d4c3c6678` | completed | `predictions`, `manifest`, `config` |

## Handoff

- train used `Model/name=ridge` and no candidates/search/ensemble settings.
- eval received `Model/artifact_path=${train.artifacts.model.url}`.
- infer received `Model/artifact_path=${train.artifacts.model.url}`.

## Notes

- No leaderboard, ensemble, or optimization artifacts are expected for single mode.
