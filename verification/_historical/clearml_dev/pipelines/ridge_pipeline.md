# ClearML Pipeline Verification: ridge

- Model: `ridge`
- Template: `tabular_pipeline_template`
- Pipeline task name: `ridge_pipeline_clearml_dev_params_loaded`
- Pipeline task ID: `f299a5603b994553b1823a6da3600200`
- URL: `http://localhost:8080/projects/57d192f3bb8746acae1a10961ee597ae/experiments/f299a5603b994553b1823a6da3600200/output/log`
- Pipeline UI URL: `http://localhost:8080/pipelines/57d192f3bb8746acae1a10961ee597ae/experiments/f299a5603b994553b1823a6da3600200`
- Project: `MLPlatform/Dev/Pipelines`
- Queue: `default`
- Status: completed

## UI Parameters

- `Input/clearml_dataset_id`: Docker-network dev dataset
- `Input/train_dataset_file`: `sample_train.csv`
- `Input/eval_dataset_file`: `sample_train.csv`
- `Input/infer_dataset_file`: `sample_infer.csv`
- `Model/name`: `ridge`
- `Model/params`: `{"alpha": 1.0}`
- `Model/feature_preset`: `basic`

## Steps

| Step | Task ID | Status | Key output |
| --- | --- | --- | --- |
| train | `9c70d09592ae4985b8a4116e28a23198` | completed | model artifact, metrics |
| eval | `c374e088276a4b299a2e17c78786fb5a` | completed | metrics, evaluation predictions |
| infer | `6cf6e646c7de457c8a33caaff812f725` | completed | predictions |

## Metrics

| Step | MAE | RMSE | R2 |
| --- | ---: | ---: | ---: |
| train | 0.4351933300 | 0.5406374335 | 0.9738583565 |
| eval | 0.4216107428 | 0.5226283669 | 0.9750446081 |

## Artifact Handoff

- Eval `Model/artifact_path`: `http://clearml-fileserver:8081/MLPlatform/Dev/Pipelines/train.9c70d09592ae4985b8a4116e28a23198/artifacts/model/model.joblib`
- Infer `Model/artifact_path`: `http://clearml-fileserver:8081/MLPlatform/Dev/Pipelines/train.9c70d09592ae4985b8a4116e28a23198/artifacts/model/model.joblib`

## Product Review

Accepted for v1 MVP. The fixed three-step pipeline is clear, and model artifact handoff is visible in step parameters.
