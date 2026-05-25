# V1 ClearML Task Verification: gradient_boosting_eval

## Summary

- Model: `gradient_boosting`
- Mode: `single`
- Task type: `eval`
- Template: `tabular_eval_template`
- Task ID: `13a211088e924a2aa862e3027825a917`
- Task URL: `http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/13a211088e924a2aa862e3027825a917/output/log`
- Queue: `default`
- Agent: `a8415e1b0aea:3`
- Status: `completed`
- Leaderboard artifact: `no`
- Success: `yes`

## Changed UI Parameters

| Parameter | Value |
| --- | --- |
| `Input/clearml_dataset_id` | `<Agent-reachable dev Dataset ID>` |
| `Input/dataset_file` | `sample_train.csv` |
| `Input/local_path` | `` |
| `Model/artifact_path` | `<train model artifact URL>` |

## Metrics

| Metric | Value |
| --- | ---: |
| `metrics/mae` | `0.4104173481` |
| `metrics/rmse` | `0.5455435514` |
| `metrics/r2` | `0.9728082418` |

## Artifacts

`config`, `evaluation_predictions`, `manifest`, `metrics`

## Sanitized Console Log Tail

```text
task 13a211088e924a2aa862e3027825a917 pulled from 03cab0f718df4349bf327f1b22dfd0d4 by worker a8415e1b0aea:3
Process completed successfully
Sensitive ClearML environment lines omitted.
```

## Issues

- None found.

## V1 Decision

- Acceptable for V1: `yes`
