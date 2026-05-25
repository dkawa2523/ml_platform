# V1 ClearML Pipeline Verification: gradient_boosting

## Summary

- Model: `gradient_boosting`
- Pipeline task ID: `634f8d8ecf2a40efb2a1d63af154d578`
- Pipeline URL: `http://localhost:8080/projects/57d192f3bb8746acae1a10961ee597ae/experiments/634f8d8ecf2a40efb2a1d63af154d578/output/log`
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
| `Model/name` | `gradient_boosting` |
| `Model/params` | `{"n_estimators": 50, "random_state": 42}` |
| `Model/selection_metric` | `rmse` |

## Steps

| Step | Status | Task ID | Artifacts | Metrics |
| --- | --- | --- | --- | --- |
| `train` | `completed` | `764acf324c2942ff8a801e5accfbd443` | `config`, `manifest`, `metrics`, `model`, `model_info`, `validation_predictions` | `metrics/mae=0.8024467826`, `metrics/r2=0.9193803072`, `metrics/rmse=0.9494244456` |
| `eval` | `completed` | `776780a239f84539b02e5e2de5c36022` | `config`, `evaluation_predictions`, `manifest`, `metrics` | `metrics/mae=0.4104173481`, `metrics/r2=0.9728082418`, `metrics/rmse=0.5455435514` |
| `infer` | `completed` | `69efd4f94150449eb761075c71a6997c` | `config`, `manifest`, `predictions` | none |

## Artifact Checks

- Train model artifact: `yes`
- Eval metrics: `metrics/mae=0.4104173481`, `metrics/r2=0.9728082418`, `metrics/rmse=0.5455435514`
- Infer predictions artifact: `yes`
- Artifact handoff: eval/infer consume `${train.artifacts.model.url}`

## Pipeline Graph Evaluation

- Expected graph: `train -> eval -> infer`
- Observed step order: `train -> eval -> infer`
- Graph acceptable for V1: `yes`

## Sanitized Step Log Tail

```text
task 634f8d8ecf2a40efb2a1d63af154d578 pulled from 03cab0f718df4349bf327f1b22dfd0d4 by worker a8415e1b0aea:2
Process completed successfully
Sensitive ClearML environment lines omitted.
--- train ---
task 764acf324c2942ff8a801e5accfbd443 pulled from 03cab0f718df4349bf327f1b22dfd0d4 by worker a8415e1b0aea:3
ClearML Monitor: GPU monitoring failed getting GPU reading, switching off GPU monitoring
Process completed successfully
Sensitive ClearML environment lines omitted.
--- eval ---
task 776780a239f84539b02e5e2de5c36022 pulled from 03cab0f718df4349bf327f1b22dfd0d4 by worker a8415e1b0aea:1
ClearML Monitor: GPU monitoring failed getting GPU reading, switching off GPU monitoring
Process completed successfully
Sensitive ClearML environment lines omitted.
--- infer ---
task 69efd4f94150449eb761075c71a6997c pulled from 03cab0f718df4349bf327f1b22dfd0d4 by worker a8415e1b0aea:3
ClearML Monitor: GPU monitoring failed getting GPU reading, switching off GPU monitoring
Process completed successfully
Sensitive ClearML environment lines omitted.
```

## Issues

- None found.

## V1 Decision

- Acceptable for V1: `yes`
