# ml_platform Development Charter

`ml_platform` is a ClearML-based product foundation for tabular scalar
regression. Keep it easy to run from ClearML UI, easy to inspect after a run,
and easy for data scientists to extend without copying legacy repository
structure.

## Product Boundary

- `pkgs/core`: ClearML-free config, IO, result, registry, and artifact helpers.
- `pkgs/tabular`: ClearML-free tabular data, features, models, ensembles,
  metrics, plots, evaluation, and inference.
- `clearml/`: ClearML SDK boundary: Task, Dataset, PipelineController,
  parameter mapping, template sync, and reporting.
- `scripts/`: thin operator wrappers only.
- `config/tasks`: product task definitions; `config/profiles`: runtime and
  ClearML environment definitions.

Never import ClearML SDK objects from `pkgs/core` or `pkgs/tabular`.

## Current Product Flow

Training is:

```text
preprocess_features -> train_<model>* -> build_ensemble_<method>* -> evaluate_models
```

Inference is separate:

```text
source_task_id + model_selector
or local_model_path
-> predict -> predictions.csv
```

Current user-facing templates are:

- `tabular_train_pipeline_template`
- `tabular_infer_template`

`tabular_stage_template` is internal and used by PipelineController steps.

## Models And Ensembles

Supported models:

- `linear`, `ridge`, `lasso`, `elasticnet`
- `random_forest`, `extra_trees`, `gradient_boosting`
- `lightgbm`, `xgboost`, `catboost`

The GBM packages are optional Python dependencies. Remote ClearML templates use
the profile's `clearml.execution.image`; that image must include
`pkgs/tabular[gbm]` when running the 10-model default. Slim/local environments
may run the dependency-free subset by overriding `model.candidates`.

Out-of-scope models are `knn`, `svr`, `mlp`, `gaussian_process`, and `tabpfn`.

Supported ensemble methods are `mean_topk`, `weighted`, and `median`.
`stacking` and optimization are future work.

## Extension Rules

Prefer small, product-facing additions:

- feature logic in `features.py`
- model builders in `models.py`
- ensemble behavior in `ensemble.py`
- metrics in `metrics.py`
- plot/table writers in `plots.py`
- ClearML presentation in `clearml/reports.py`

Avoid sprawl:

- no model-specific templates
- no dataset-specific templates
- no one-template-per-ensemble-method variants
- no broad diagnostics or contract framework
- no bulk copy from reference repositories
- no business logic in scripts

Use reference repositories only as reading material. Reimplement only the
small behavior needed inside this repo's current architecture.

## ClearML UX Standard

A successful run is not enough. ClearML UI must show:

- dataset and feature choices
- trained models and ensemble methods
- metrics and leaderboard
- useful plots and tables
- reusable artifacts and manifests
- inference source and predictions

`docs/SPEC.md` is the product source of truth.
`docs/CLEARML_UI_SPEC.md` is the screen-level UI contract.

## Checks

For product-flow changes, run:

```powershell
python scripts/make_sample_data.py
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set "model.candidates=[linear,ridge,lasso,elasticnet,random_forest,extra_trees,gradient_boosting]"
python scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

Boundary check:

```powershell
rg -n "from clearml|import clearml|PipelineController|StorageManager" pkgs/core pkgs/tabular
```
