# V1 ClearML Pipeline Verification: random_forest

## Summary

- Model: `random_forest`
- Pipeline task ID: `7b698322f4f34a5bbeb7e5b24f773996`
- Pipeline URL: `http://localhost:8080/projects/57d192f3bb8746acae1a10961ee597ae/experiments/7b698322f4f34a5bbeb7e5b24f773996/output/log`
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
| `Model/name` | `random_forest` |
| `Model/params` | `{"n_estimators": 50, "random_state": 42, "n_jobs": 1}` |
| `Model/selection_metric` | `rmse` |

## Steps

| Step | Status | Task ID | Artifacts | Metrics |
| --- | --- | --- | --- | --- |
| `train` | `completed` | `c52eaf540ff5400baf3a16f41196f980` | `config`, `manifest`, `metrics`, `model`, `model_info`, `validation_predictions` | `metrics/mae=0.9371984601`, `metrics/r2=0.8890656829`, `metrics/rmse=1.1137118340` |
| `eval` | `completed` | `409a12364f8245c98681cc1b4d8f5fc7` | `config`, `evaluation_predictions`, `manifest`, `metrics` | `metrics/mae=0.4248252511`, `metrics/r2=0.9639313817`, `metrics/rmse=0.6283116937` |
| `infer` | `completed` | `1a0bac910c4447609ef4fd4811305cf2` | `config`, `manifest`, `predictions` | none |

## Artifact Checks

- Train model artifact: `yes`
- Eval metrics: `metrics/mae=0.4248252511`, `metrics/r2=0.9639313817`, `metrics/rmse=0.6283116937`
- Infer predictions artifact: `yes`
- Artifact handoff: eval/infer consume `${train.artifacts.model.url}`

## Pipeline Graph Evaluation

- Expected graph: `train -> eval -> infer`
- Observed step order: `train -> eval -> infer`
- Graph acceptable for V1: `yes`

## Sanitized Step Log Tail

```text
task 7b698322f4f34a5bbeb7e5b24f773996 pulled from 03cab0f718df4349bf327f1b22dfd0d4 by worker a8415e1b0aea:2
Process completed successfully
Sensitive ClearML environment lines omitted.
--- train ---
task c52eaf540ff5400baf3a16f41196f980 pulled from 03cab0f718df4349bf327f1b22dfd0d4 by worker a8415e1b0aea:1
ClearML Monitor: GPU monitoring failed getting GPU reading, switching off GPU monitoring
Process completed successfully
Sensitive ClearML environment lines omitted.
--- eval ---
task 409a12364f8245c98681cc1b4d8f5fc7 pulled from 03cab0f718df4349bf327f1b22dfd0d4 by worker a8415e1b0aea:3
ClearML Monitor: GPU monitoring failed getting GPU reading, switching off GPU monitoring
Process completed successfully
Sensitive ClearML environment lines omitted.
--- infer ---
task 1a0bac910c4447609ef4fd4811305cf2 pulled from 03cab0f718df4349bf327f1b22dfd0d4 by worker a8415e1b0aea:1
ClearML Monitor: GPU monitoring failed getting GPU reading, switching off GPU monitoring
Process completed successfully
Sensitive ClearML environment lines omitted.
```

## Issues

- None found.

## V1 Decision

- Acceptable for V1: `yes`
