# V1 ClearML Task Verification: random_forest_eval

## Summary

- Model: `random_forest`
- Mode: `single`
- Task type: `eval`
- Template: `tabular_eval_template`
- Task ID: `02dcc9d6a55c4e77bf72032d586247b4`
- Task URL: `http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/02dcc9d6a55c4e77bf72032d586247b4/output/log`
- Queue: `default`
- Agent: `a8415e1b0aea:1`
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
| `metrics/mae` | `0.4248252511` |
| `metrics/rmse` | `0.6283116937` |
| `metrics/r2` | `0.9639313817` |

## Artifacts

`config`, `evaluation_predictions`, `manifest`, `metrics`

## Sanitized Console Log Tail

```text
task 02dcc9d6a55c4e77bf72032d586247b4 pulled from 03cab0f718df4349bf327f1b22dfd0d4 by worker a8415e1b0aea:1
Process completed successfully
Sensitive ClearML environment lines omitted.
```

## Issues

- None found.

## V1 Decision

- Acceptable for V1: `yes`
