# V1 ClearML Pipeline Verification: ridge

## Summary

- Model: `ridge`
- Pipeline task ID: `b1ac57b796b44187946030c1270614db`
- Pipeline URL: `http://localhost:8080/projects/57d192f3bb8746acae1a10961ee597ae/experiments/b1ac57b796b44187946030c1270614db/output/log`
- Queue: `default`
- Agent: `a8415e1b0aea:2`
- Overall status: `completed`
- Success: `yes`

## Changed UI Parameters

| Parameter | Value |
| --- | --- |
| `Input/clearml_dataset_id` | `<Agent-reachable dev Dataset ID>` |
| `Input/eval_dataset_file` | `sample_train.csv` |
| `Input/infer_dataset_file` | `sample_infer.csv` |
| `Input/train_dataset_file` | `sample_train.csv` |
| `Model/candidates` | `[]` |
| `Model/feature_preset` | `basic` |
| `Model/name` | `ridge` |
| `Model/params` | `{"alpha": 1.0}` |
| `Model/selection_metric` | `rmse` |

## Steps

| Step | Status | Task ID | Artifacts | Metrics |
| --- | --- | --- | --- | --- |
| `train` | `completed` | `593b2f12e4624b6a9f5374d4eefd998e` | `config`, `manifest`, `metrics`, `model`, `model_info`, `validation_predictions` | `metrics/mae=0.4351933300`, `metrics/r2=0.9738583565`, `metrics/rmse=0.5406374335` |
| `eval` | `completed` | `a45bf4b2a5c84bbe9c8dd21942e0ec77` | `config`, `evaluation_predictions`, `manifest`, `metrics` | `metrics/mae=0.4216107428`, `metrics/r2=0.9750446081`, `metrics/rmse=0.5226283669` |
| `infer` | `completed` | `e6f4cd1fefbf41db9c1f74b3b2d8e5c2` | `config`, `manifest`, `predictions` | none |

## Artifact Checks

- Train model artifact: `yes`
- Eval metrics: `metrics/mae=0.4216107428`, `metrics/r2=0.9750446081`, `metrics/rmse=0.5226283669`
- Infer predictions artifact: `yes`
- Artifact handoff: eval/infer consume `${train.artifacts.model.url}`

## Pipeline Graph Evaluation

- Expected graph: `train -> eval -> infer`
- Observed step order: `train -> eval -> infer`
- Graph acceptable for V1: `yes`

## Sanitized Step Log Tail

```text
task b1ac57b796b44187946030c1270614db pulled from 03cab0f718df4349bf327f1b22dfd0d4 by worker a8415e1b0aea:2
Process completed successfully
Sensitive ClearML environment lines omitted.
--- train ---
task 593b2f12e4624b6a9f5374d4eefd998e pulled from 03cab0f718df4349bf327f1b22dfd0d4 by worker a8415e1b0aea:3
ClearML Monitor: GPU monitoring failed getting GPU reading, switching off GPU monitoring
Process completed successfully
Sensitive ClearML environment lines omitted.
--- eval ---
task a45bf4b2a5c84bbe9c8dd21942e0ec77 pulled from 03cab0f718df4349bf327f1b22dfd0d4 by worker a8415e1b0aea:1
ClearML Monitor: GPU monitoring failed getting GPU reading, switching off GPU monitoring
Process completed successfully
Sensitive ClearML environment lines omitted.
--- infer ---
task e6f4cd1fefbf41db9c1f74b3b2d8e5c2 pulled from 03cab0f718df4349bf327f1b22dfd0d4 by worker a8415e1b0aea:3
ClearML Monitor: GPU monitoring failed getting GPU reading, switching off GPU monitoring
Process completed successfully
Sensitive ClearML environment lines omitted.
```

## Issues

- None found.

## V1 Decision

- Acceptable for V1: `yes`
