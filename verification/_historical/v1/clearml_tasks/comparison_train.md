# V1 ClearML Task Verification: comparison_train

## Summary

- Model: `comparison`
- Mode: `comparison`
- Task type: `train`
- Template: `tabular_train_template`
- Task ID: `c911b579120645e88f11c94361236ca9`
- Task URL: `http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/c911b579120645e88f11c94361236ca9/output/log`
- Queue: `default`
- Agent: `a8415e1b0aea:2`
- Status: `completed`
- Leaderboard artifact: `yes`
- Success: `yes`

## Changed UI Parameters

| Parameter | Value |
| --- | --- |
| `Input/clearml_dataset_id` | `<Agent-reachable dev Dataset ID>` |
| `Input/dataset_file` | `sample_train.csv` |
| `Input/local_path` | `` |
| `Model/candidates` | `<4 V1 model candidates JSON>` |
| `Model/selection_metric` | `rmse` |

## Metrics

| Metric | Value |
| --- | ---: |
| `metrics/mae` | `0.4354112148` |
| `metrics/rmse` | `0.5402973294` |
| `metrics/r2` | `0.9738912582` |

## Artifacts

`config`, `leaderboard`, `manifest`, `metrics`, `model`, `model_info`, `validation_predictions`

## Sanitized Console Log Tail

```text
task c911b579120645e88f11c94361236ca9 pulled from 03cab0f718df4349bf327f1b22dfd0d4 by worker a8415e1b0aea:2
Process completed successfully
Sensitive ClearML environment lines omitted.
```

## Issues

- None found.

## V1 Decision

- Acceptable for V1: `yes`
