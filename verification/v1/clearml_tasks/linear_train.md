# V1 ClearML Task Verification: linear_train

## Summary

- Model: `linear`
- Mode: `single`
- Task type: `train`
- Template: `tabular_train_template`
- Task ID: `c066e2235b504004989740c32d6c2a07`
- Task URL: `http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/c066e2235b504004989740c32d6c2a07/output/log`
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
| `Model/candidates` | `[]` |
| `Model/name` | `linear` |
| `Model/params` | `{}` |
| `Model/selection_metric` | `rmse` |

## Metrics

| Metric | Value |
| --- | ---: |
| `metrics/mae` | `0.4354112148` |
| `metrics/rmse` | `0.5402973294` |
| `metrics/r2` | `0.9738912582` |

## Artifacts

`config`, `manifest`, `metrics`, `model`, `model_info`, `validation_predictions`

## Sanitized Console Log Tail

```text
task c066e2235b504004989740c32d6c2a07 pulled from 03cab0f718df4349bf327f1b22dfd0d4 by worker a8415e1b0aea:3
ClearML results page: http://webserver:80/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/c066e2235b504004989740c32d6c2a07/output/log
2026-05-24 14:32:41,411 - clearml.resource_monitor - WARNING - Could not fetch GPU stats: NVML Shared Library Not Found
2026-05-24 14:32:41,688 - clearml - INFO - Dataset.get() did not specify alias. Dataset information will not be automatically logged in ClearML Server.
ClearML Monitor: GPU monitoring failed getting GPU reading, switching off GPU monitoring
Process completed successfully
Sensitive ClearML environment lines omitted.
```

## Issues

- None found.

## V1 Decision

- Acceptable for V1: `yes`
