# V1 ClearML Task Verification: linear_infer

## Summary

- Model: `linear`
- Mode: `single`
- Task type: `infer`
- Template: `tabular_infer_template`
- Task ID: `b6c037cf7a5d44bdaa4974bac282a074`
- Task URL: `http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/b6c037cf7a5d44bdaa4974bac282a074/output/log`
- Queue: `default`
- Agent: `a8415e1b0aea:1`
- Status: `completed`
- Leaderboard artifact: `no`
- Success: `yes`

## Changed UI Parameters

| Parameter | Value |
| --- | --- |
| `Input/clearml_dataset_id` | `<Agent-reachable dev Dataset ID>` |
| `Input/dataset_file` | `sample_infer.csv` |
| `Input/local_path` | `` |
| `Model/artifact_path` | `<train model artifact URL>` |

## Metrics

| Metric | Value |
| --- | --- |
| none | - |

## Artifacts

`config`, `manifest`, `predictions`

## Sanitized Console Log Tail

```text
task b6c037cf7a5d44bdaa4974bac282a074 pulled from 03cab0f718df4349bf327f1b22dfd0d4 by worker a8415e1b0aea:1
ClearML results page: http://webserver:80/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/b6c037cf7a5d44bdaa4974bac282a074/output/log
2026-05-24 14:33:44,657 - clearml.resource_monitor - WARNING - Could not fetch GPU stats: NVML Shared Library Not Found
2026-05-24 14:33:44,683 - clearml - INFO - Dataset.get() did not specify alias. Dataset information will not be automatically logged in ClearML Server.
ClearML Monitor: GPU monitoring failed getting GPU reading, switching off GPU monitoring
Process completed successfully
Sensitive ClearML environment lines omitted.
```

## Issues

- None found.

## V1 Decision

- Acceptable for V1: `yes`
