# V1 ClearML Task Verification: random_forest_train

## Summary

- Model: `random_forest`
- Mode: `single`
- Task type: `train`
- Template: `tabular_train_template`
- Task ID: `9275966d715b4cbea0bde46e6df5de4b`
- Task URL: `http://localhost:8080/projects/dff412a3cc954606bd3718c3d1ef8fe2/experiments/9275966d715b4cbea0bde46e6df5de4b/output/log`
- Queue: `default`
- Agent: `a8415e1b0aea:2`
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
| `Model/name` | `random_forest` |
| `Model/params` | `{"n_estimators": 50, "random_state": 42, "n_jobs": 1}` |
| `Model/selection_metric` | `rmse` |

## Metrics

| Metric | Value |
| --- | ---: |
| `metrics/mae` | `0.9371984601` |
| `metrics/rmse` | `1.1137118340` |
| `metrics/r2` | `0.8890656829` |

## Artifacts

`config`, `manifest`, `metrics`, `model`, `model_info`, `validation_predictions`

## Sanitized Console Log Tail

```text
task 9275966d715b4cbea0bde46e6df5de4b pulled from 03cab0f718df4349bf327f1b22dfd0d4 by worker a8415e1b0aea:2
Process completed successfully
Sensitive ClearML environment lines omitted.
```

## Issues

- None found.

## V1 Decision

- Acceptable for V1: `yes`
