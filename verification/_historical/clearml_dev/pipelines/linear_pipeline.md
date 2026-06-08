# ClearML Pipeline Verification: linear

- Model: `linear`
- Template: `tabular_pipeline_template`
- Pipeline task name: `linear_pipeline_clearml_dev_params_loaded`
- Pipeline task ID: `29df0b860fd04e37a5c796858cb434c9`
- URL: `http://localhost:8080/projects/57d192f3bb8746acae1a10961ee597ae/experiments/29df0b860fd04e37a5c796858cb434c9/output/log`
- Pipeline UI URL: `http://localhost:8080/pipelines/57d192f3bb8746acae1a10961ee597ae/experiments/29df0b860fd04e37a5c796858cb434c9`
- Project: `MLPlatform/Dev/Pipelines`
- Queue: `default`
- Status: completed

## UI Parameters

- `Input/clearml_dataset_id`: Docker-network dev dataset
- `Input/train_dataset_file`: `sample_train.csv`
- `Input/eval_dataset_file`: `sample_train.csv`
- `Input/infer_dataset_file`: `sample_infer.csv`
- `Model/name`: `linear`
- `Model/params`: `{}`
- `Model/feature_preset`: `basic`

## Steps

| Step | Task ID | Status | Key output |
| --- | --- | --- | --- |
| train | `2a62fc0c97954f9685f8633707cd2b96` | completed | model artifact, metrics |
| eval | `d204b47e9ff94638a7a6866d665f2ae3` | completed | metrics, evaluation predictions |
| infer | `a36d1c83f5ee415cb0d316bf7d636c26` | completed | predictions |

## Metrics

| Step | MAE | RMSE | R2 |
| --- | ---: | ---: | ---: |
| train | 0.4354112148 | 0.5402973294 | 0.9738912582 |
| eval | 0.4219971597 | 0.5218273997 | 0.9751210213 |

## Artifact Handoff

- Eval `Model/artifact_path`: `http://clearml-fileserver:8081/MLPlatform/Dev/Pipelines/train.2a62fc0c97954f9685f8633707cd2b96/artifacts/model/model.joblib`
- Infer `Model/artifact_path`: `http://clearml-fileserver:8081/MLPlatform/Dev/Pipelines/train.2a62fc0c97954f9685f8633707cd2b96/artifacts/model/model.joblib`

## Product Review

Accepted for v1 MVP. The same pipeline template works for a second MVP model with only `Model/name` and `Model/params` changed.
