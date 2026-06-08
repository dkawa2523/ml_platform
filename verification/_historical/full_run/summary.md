# V1 Full Model / Full Pipeline Summary

> Historical note: this file records V1 task evidence plus the old fixed
> full-run compatibility pipeline. It is not current product readiness evidence
> for the official stage-based training pipeline.

## Run Metadata

- Date: 2026-05-24
- Verified commit: `0d4b2eb`
- Scope: local plus ClearML dev full model verification
- V1 official models: `linear`, `ridge`, `random_forest`, `gradient_boosting`
- Raw logs: not stored
- Screenshots: not stored
- Secrets: not stored

## Local Matrix

| Model | Train | Eval | Infer | Pipeline |
| --- | --- | --- | --- | --- |
| `linear` | pass | pass | pass | pass |
| `ridge` | pass | pass | pass | pass |
| `random_forest` | pass | pass | pass | pass |
| `gradient_boosting` | pass | pass | pass | pass |

## ClearML Template URLs

| Template | Task ID | URL |
| --- | --- | --- |
| `tabular_train_template` | `c2ef58062a5347c9b8f3e7ed13945be9` | `http://localhost:8080/projects/739356ee8e354bb48283539ced2a99eb/experiments/c2ef58062a5347c9b8f3e7ed13945be9/output/log` |
| `tabular_eval_template` | `641a810049c84a6dbeafefb2ae513bcb` | `http://localhost:8080/projects/739356ee8e354bb48283539ced2a99eb/experiments/641a810049c84a6dbeafefb2ae513bcb/output/log` |
| `tabular_infer_template` | `a6c147c9768b4c0f9de5cef470ad8257` | `http://localhost:8080/projects/739356ee8e354bb48283539ced2a99eb/experiments/a6c147c9768b4c0f9de5cef470ad8257/output/log` |
| `tabular_pipeline_template` | `d8d4fe66b7f8499bbe69178a09eaece2` | `http://localhost:8080/projects/739356ee8e354bb48283539ced2a99eb/experiments/d8d4fe66b7f8499bbe69178a09eaece2/output/log` |

## ClearML Task Matrix

| Model | Train | Eval | Infer |
| --- | --- | --- | --- |
| `linear` | pass `f529c70234f34f58a095a0da63577829` | pass `4a93dc5d4a8a4ac38bd361b8665b228b` | pass `6ee2e3d23c8d432bb157737e64423288` |
| `ridge` | pass `102084a83f8f42b9a40238f5875cf3a3` | pass `449e03d117b3452b89b6213dbd967d37` | pass `3666b10eb11c46039b91acd71d95d199` |
| `random_forest` | pass `ad882a176a4344e6b75236be0eff2804` | pass `41d5ffbcdfbd4c8eb86ea7e66b6224e6` | pass `1ed9662de9774ae59fd15cce88173163` |
| `gradient_boosting` | pass `ccc64849d35c43998b0abab1539bda3e` | pass `106292432ad24be2a2a45a520af3e2fd` | pass `40bd5133bbd54b629264ad3b12a84ca3` |

## ClearML Pipeline Matrix

| Model | Pipeline | Pipeline URL |
| --- | --- | --- |
| `linear` | pass `dc3f88850d854ae087642532fb1e70f9` | `http://localhost:8080/pipelines/57d192f3bb8746acae1a10961ee597ae/experiments/dc3f88850d854ae087642532fb1e70f9` |
| `ridge` | pass `d2cff4a829b44c37a3ce92b8b76117d7` | `http://localhost:8080/pipelines/57d192f3bb8746acae1a10961ee597ae/experiments/d2cff4a829b44c37a3ce92b8b76117d7` |
| `random_forest` | pass `cb4795e92d044b7ea51b9a0c8ce031b0` | `http://localhost:8080/pipelines/57d192f3bb8746acae1a10961ee597ae/experiments/cb4795e92d044b7ea51b9a0c8ce031b0` |
| `gradient_boosting` | pass `d4c80526d83543b8bc17425c2a43e341` | `http://localhost:8080/pipelines/57d192f3bb8746acae1a10961ee597ae/experiments/d4c80526d83543b8bc17425c2a43e341` |

## Metrics Summary

| Model | ClearML train RMSE | ClearML eval RMSE | ClearML eval R2 |
| --- | ---: | ---: | ---: |
| `linear` | `0.5402973294258118` | `0.5218273997306824` | `0.975121021270752` |
| `ridge` | `0.5406374335289001` | `0.5226283669471741` | `0.9750446081161499` |
| `random_forest` | `1.1137118339538574` | `0.6283116936683655` | `0.9639313817024231` |
| `gradient_boosting` | `0.9494244456291199` | `0.5455435514450073` | `0.9728082418441772` |

## Artifact Summary

- Train tasks produce `config`, `manifest`, `metrics`, `model`, `model_info`, and `validation_predictions`.
- Eval tasks produce `config`, `evaluation_predictions`, `manifest`, and `metrics`.
- Infer tasks produce `config`, `manifest`, and `predictions`.
- Pipelines create three completed step tasks: `train`, `eval`, `infer`.
- Pipeline eval/infer receive the train step `model` artifact through `Model/artifact_path`.

## Fixes Made During Verification

- Promoted `scikit-learn` to V1 runtime dependency.
- Fixed local pipeline model param override so RF/GB do not inherit stale `alpha`.
- Normalized ClearML `Model/params` to a JSON string and removed stale nested `Model/params/*` template parameters.

## Gate Results

| Gate | Result | Notes |
| --- | --- | --- |
| Architecture | pass | ClearML dependency remains outside `pkgs`; scripts are wrappers; config remains tasks plus profiles |
| Local | pass | all four V1 models passed train/eval/infer/pipeline |
| ClearML dev | pass | four templates synced; all four models passed task and pipeline execution |
| UI evidence | pass | direct browser access unavailable; SDK metadata and task URLs were used |
| Docs | pass | V1 scope, sklearn dependency, worker slots, Dataset URL reachability, and future scope are documented |
| Secrets | pass | no raw logs or credentials stored |

## V1 Decision

V1 historical scope ready: four verified tabular scalar regression models
through local execution and ClearML task execution, plus old compatibility
pipeline execution.
