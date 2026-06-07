# Specification

## Purpose

`ml_platform` manages small tabular regression runs locally and through ClearML while keeping reusable ML logic ClearML-free.

## Product Scope

This section is the canonical current product scope. Historical phase notes live
in `docs/PRODUCTIZATION_PHASES.md`.

### Supported

Supported means the behavior is implemented and exposed through the intended
interface. Local-only behavior needs local test/verification evidence; ClearML
behavior needs ClearML remote evidence before promotion.

- tabular scalar regression local train, eval, and infer task execution
- ClearML UI train, eval, and infer task execution
- local stage-based training pipeline through `config/tasks/tabular_pipeline.yaml`
- official models: `linear`, `ridge`, `random_forest`, and `gradient_boosting`
- comparison mode with `model.candidates` / `Model/candidates`
- `leaderboard.csv` and best model selection
- `mean_topk` and `weighted` ensemble saved as the standard model artifact
- train-time `grid` and `random` hyperparameter search
- local stage-based optimization pipeline with `grid` / `random` search
- standardized batch inference output for model, best-model, ensemble, and optimized artifacts
- optional CSV chunked prediction/write via `output.chunk_size` / `Output/chunk_size`
- metrics, artifacts, predictions, ClearML Dataset id/file handling, and minimal Agent deploy manifests

### Experimental

Experimental means the behavior is implemented but remote verification is
limited, dependency/runtime behavior has caveats, or the API/config may still
change before promotion to supported.

- additional sklearn regressors: `lasso`, `elasticnet`, `extra_trees`, `knn`, `svr`, and `mlp`
- ClearML stage-based training and optimization pipeline drafts:
  `tabular_train_pipeline_template`, `tabular_train_full_pipeline_template`,
  and `tabular_train_full_ensemble_pipeline_template`
- local `tabular_1d_output` utility
- compatibility simple full-run modes through `run.pipeline_mode` /
  `Run/pipeline_mode`
- model-specific runtime caveats such as convergence warnings or data-size sensitivity

Experimental features must use the existing task/profile config shape and the
same ClearML launch targets. Do not mark them supported until local and ClearML
remote evidence is documented.

### Future

- LightGBM, XGBoost, and CatBoost
- Optuna, Ray Tune, Bayesian search, and advanced optimization
- stacking and weight optimization
- per-trial ClearML child tasks
- advanced plots and reporting
- online serving APIs
- 1D / 2D productization
- distribution mode decomposition
- richer preprocessing and schema validation

### Discarded

- legacy full parity as a goal
- excessive contract docs and checklist pages
- broad diagnostics helpers
- old adapter splits
- live cleanup operations
- model-specific ClearML templates
- dataset-specific ClearML templates
- legacy repo directory, config, helper, test, or docs recreation

The four official models are verified for local train/eval/infer and ClearML
task train/eval/infer. Historical compatibility simple full-run evidence also
exists for `train -> eval -> infer`, but that flow is not the official training
pipeline. `scikit-learn` is a required runtime dependency because it provides
`random_forest` and `gradient_boosting`. Train supports a small
`model.candidates` comparison mode that writes `leaderboard.csv`, records a
comparison summary in `metrics.json`, and saves only the best model artifact.
This repo does not target full legacy parity: legacy `train_ensemble_full`,
separate runtime leaderboard tasks, broad diagnostics, and template
proliferation are not product scope. `mean_topk` and deterministic
validation-metric `weighted` ensemble are supported; stacking remains future
scope. Train-time hyperparameter search is limited to `grid` and `random`; it
does not add Optuna, Ray Tune, ClearML child tasks, or an optimize template.
Inference remains batch table inference only. It includes CSV chunked
prediction/write support, but not streaming readers, online serving, parquet as
a required format, or an inference pipeline.

## Pipeline Vocabulary

The official training pipeline definition is:

```text
preprocess_features -> train_<model>* -> build_ensemble optional -> evaluate_models
```

`config/tasks/tabular_pipeline.yaml` implements this graph locally. The ClearML
Pipeline-tab drafts implement the same graph through the internal
`tabular_stage_template`; remote verification is still required before they are
called supported. The old `tabular_pipeline_template` remains a deprecated
compatibility entrypoint for a simple full-run flow:

```text
train -> eval -> infer
```

This ClearML compatibility flow remains available only for historical smoke
checks and artifact handoff verification. It must not be described as the
official training pipeline.

Inference is separate from training pipeline execution. The intended inference
entrypoint is `tabular_infer_template`, which resolves a trained model, best
model, or ensemble artifact and writes `predictions.csv`.

Optimization is a separate stage-based pipeline shape, activated from the same
training pipeline config when `model.search.enabled=true` and
`model.ensemble.enabled=false`:

```text
preprocess_features -> search_trials -> retrain_best -> evaluate_best
```

Current user-facing templates:

```text
tabular_train_pipeline_template
tabular_train_full_pipeline_template
tabular_train_full_ensemble_pipeline_template
tabular_infer_template
```

Current internal template:

```text
tabular_stage_template
```

The stage template is for PipelineController steps in training and optimization
pipeline graphs only. Do not create model-specific, ensemble-specific,
optimization-specific, or dataset-specific templates.

## Boundaries

```text
scripts/local_run.py -> pkgs
clearml/app.py      -> clearml/adapter.py -> pkgs
clearml/pipelines.py -> ClearML PipelineController

pkgs/core    -> pandas, pyyaml, stdlib
pkgs/tabular -> pkgs/core, pandas, numpy, scikit-learn
```

Forbidden dependencies:

```text
pkgs -> clearml
pkgs -> deploy
pkgs -> scripts
```

## Config

Config uses two axes:

```text
config/tasks    what to run
config/profiles where to run
```

Task config values override profile values. CLI overrides are applied last.

Important task sections:

- `task`
- `run`
- `data`
- `split`
- `metrics`
- `features`
- `model`
- `output`

`metrics.names` is task config only. It is not a ClearML UI parameter.

## ClearML UI Parameters

The ClearML UI parameter surface is intentionally small and grouped only as:

```text
Input
Run
Model
Output
```

Current parameter names used across user-facing tasks, Pipeline-tab drafts, and
the internal stage template:

```text
Input/local_path
Input/clearml_dataset_id
Input/dataset_file
Input/target_column
Input/feature_columns
Input/id_columns
Input/preprocess_bundle
Input/feature_spec
Input/processed_train
Input/processed_valid
Input/model_refs
Input/ensemble_ref
Input/best_params
Input/optimization_summary
Input/model
Input/model_info

Run/task
Run/name
Run/seed
Run/stage
Run/pipeline_mode

Model/name
Model/params
Model/candidates
Model/selection_metric
Model/search_enabled
Model/search_method
Model/search_space
Model/max_trials
Model/ensemble_enabled
Model/ensemble_method
Model/ensemble_top_k
Model/source_type
Model/source_task_id
Model/model_selector
Model/model_artifact_url
Model/clearml_model_id
Model/local_model_path
Model/artifact_path
Model/info_path
Model/feature_spec_path
Model/preprocess_bundle_path
Model/feature_preset

Output/prediction_name
Output/chunk_size
```

Queue selection is profile and Agent configuration, not a UI parameter.

Inference model source parameters are used only by `tabular_infer_template`:

```text
Model/source_type=task_id | artifact_url | clearml_model_id | local_path
Model/model_selector=best | ensemble | <model_name>
```

Recommended ClearML inference uses `Model/source_type=task_id`,
`Model/source_task_id=<training pipeline or stage task id>`, and
`Model/model_selector=best` or `ensemble`. `task_id` resolution accepts both a
Pipeline controller task id and a direct stage task id. `artifact_url` resolves
`Model/model_artifact_url`; `clearml_model_id` downloads the ClearML model
weights with best-effort metadata; `local_path` uses `Model/local_model_path`.
`Model/artifact_path` remains a deprecated compatibility alias.

Current default ClearML launch targets are not model-specific:

```text
tabular_infer_template
tabular_stage_template
tabular_train_pipeline_template
tabular_train_full_pipeline_template
tabular_train_full_ensemble_pipeline_template
```

`tabular_stage_template` is internal. `Run/stage` and `Input/*` stage refs are
used by PipelineController step overrides, not by end users cloning arbitrary
stage tasks.

Training pipeline drafts use `Model/candidates` as a JSON list of model names
and `Model/selection_metric` for leaderboard ordering. `Model/params` may be a
JSON object keyed by model name.

Example:

```json
{
  "Model/candidates": "[\"linear\", \"ridge\", \"random_forest\"]",
  "Model/params": "{\"ridge\":{\"alpha\":1.0},\"random_forest\":{\"n_estimators\":50,\"random_state\":42,\"n_jobs\":1}}"
}
```

Historical compatibility simple full-run mode is explicit for the deprecated
Pipeline-tab draft:

```text
Run/pipeline_mode=auto
Run/pipeline_mode=single
Run/pipeline_mode=compare
Run/pipeline_mode=ensemble
Run/pipeline_mode=optimize
```

`auto` preserves compatibility by inferring mode from the Model parameters.
`single` uses `Model/name` and `Model/params` only. `compare` requires
`Model/candidates` and writes `leaderboard.csv`; eval and infer receive the
selected best model. `ensemble` requires candidates and saves a `mean_topk` or
`weighted` ensemble as the standard `model` artifact. `optimize` requires
`Model/search_space`, writes `optimization_trials.csv`,
`optimization_summary.json`, and `best_params.json`, then passes the optimized
model to eval and infer. These are compatibility flow modes, not official
training pipeline modes. V2.3 does not combine search and ensemble.
`single_model`, `comparison`, and `optimization` are accepted as compatibility
aliases.

Compatibility full-run dataset file parameters map to the matching step:

```text
Input/train_dataset_file -> train Input/dataset_file
Input/eval_dataset_file  -> eval Input/dataset_file
Input/infer_dataset_file -> infer Input/dataset_file
```

Compatibility full-run `Input/target_column` maps to train and eval.
Compatibility full-run `Input/id_columns` maps to train, eval, and infer.
Compatibility full-run
`Output/prediction_name` and `Output/chunk_size` map only to infer.

The same parameter surface is used for experimental sklearn models. Do not add
model-specific templates or ClearML adapter branches for `lasso`, `elasticnet`,
`extra_trees`, `knn`, `svr`, or `mlp`.

Use the flat `Model/ensemble_*` parameters with comparison or
`Run/pipeline_mode=ensemble`. Local config remains nested under
`model.ensemble`. Supported methods are `mean_topk` and `weighted`. The
supported ClearML shape is:

```json
{
  "Model/ensemble_enabled": true,
  "Model/ensemble_method": "mean_topk",
  "Model/ensemble_top_k": 3
}
```

When enabled, train saves `model.joblib` as an ensemble artifact and stores the
selected top-k base models under `base_models/`. `weighted` derives normalized
weights from `Model/selection_metric`; it does not run optimization.

Use `Model/search_*` parameters for `grid` and `random` hyperparameter search.
In the stage-based training pipeline, setting `Model/search_enabled=true` and
`Model/ensemble_enabled=false` switches the graph to
`preprocess_features -> search_trials -> retrain_best -> evaluate_best`.
Search writes `optimization_trials.csv`, `optimization_summary.json`, and
`best_params.json`; `retrain_best` writes the deployable `model.joblib`, and
`evaluate_best` writes `best_model.joblib`, `best_model.json`,
`evaluation_report.json`, and `metrics.json`. `Model/search_space` is a JSON
object string: direct parameter names for single-model search, or a model-keyed
object when `Model/candidates` is used. Search and ensemble are not combined in
Phase E.

## Artifacts

Typical local outputs:

```text
outputs/
  <run_name>_<timestamp>/
    config.yaml
    metrics.json
    manifest.json
    model.joblib
    model_info.json
    leaderboard.csv
    optimization_trials.csv
    optimization_summary.json
    best_params.json
    ensemble_info.json
    ensemble_predictions.csv
    predictions.csv

  latest_train/
    model.joblib
    model_info.json

  latest/
    latest completed task copy
```

Infer resolves models from an explicit source first. When no explicit source is
provided, local infer checks `latest_training_pipeline/evaluate_models/best_model.joblib`,
then `latest_train/model.joblib`, then `latest/model.joblib`. These `latest*`
directories are copied directories rather than symlinks for Windows, ClearML
Agent, and mounted volume compatibility.

Inference `predictions.csv` preserves the input columns and appends:

```text
prediction
model_name
artifact_kind
model_artifact_id
prediction_run_id
```

These appended column names are reserved in inference input tables. The ClearML
artifact key is `predictions`; the physical file name is controlled by
`output.prediction_name` or `Output/prediction_name`. `Output/chunk_size` is an
optional CSV inference control that chunks prediction and writing after the input
table has been loaded.
The inference manifest records `source_type`, `source_task_id`,
`model_selector`, resolved model path, and any resolved `model_info`,
`feature_spec`, or `preprocess_bundle` paths.

## Extension Points

- Add models in `pkgs/tabular/src/ml_platform_tabular/models.py`.
- Add feature presets in `pkgs/tabular/src/ml_platform_tabular/features.py`.
- Add metrics in `pkgs/tabular/src/ml_platform_tabular/metrics.py`.
- Use train `model.candidates` for small model comparison; do not add a template per model.
- Add small tabular analysis tasks in `pkgs/tabular/src/ml_platform_tabular/`.
- Change ClearML parameter mapping in `clearml/adapter.py`.
- Change ClearML reports in `clearml/reports.py`.
- Change template sync in `clearml/templates.py`.
- Change Agent runtime in `deploy/`.

Add an abstraction only after at least two concrete implementations need it.
