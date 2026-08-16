# ml_platform Development Charter

`ml_platform` is a ClearML-based product foundation for tabular regression.
It supports a scalar table and a sparse collection of target-specific tables
with a shared coordinate schema. Keep it easy to run from ClearML UI, easy to
inspect after a run, and easy for data scientists to extend without copying
legacy repository structure.

## Product Boundary

- `pkgs/core`: ClearML-free config, IO, result, and artifact helpers.
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
the profile's `clearml.execution.image` and install GBM packages into the
Agent-created execution venv when running the 10-model default. Slim/local
environments may run the dependency-free subset by overriding `model.candidates`.

Out-of-scope models are `knn`, `svr`, `mlp`, `gaussian_process`, and `tabpfn`.

Supported ensemble methods are `mean_topk`, `weighted`, and `median`.
Sparse target collections use one independent scalar model per target inside a
single model bundle; they do not align, fill, or pivot target coordinates.
Optimization, stacking, broad task registries, and joint tensor outputs are P2
roadmap items. Do not implement them in the current product flow.

## Extension Rules

Prefer small, product-facing additions:

- feature presets in `feature_config.py`, transformer behavior in `features.py`
- model registration in `model_catalog.py`, candidate parsing in `model_candidates.py`, builders in `models.py`
- ensemble behavior in `ensemble.py`
- metrics in `metrics.py`
- plot/table writers in `plotting/` and `training/*_artifacts.py`
- ClearML presentation in `pkgs/clearml/src/ml_platform_clearml/reports.py`

Avoid sprawl:

- no model-specific templates
- no dataset-specific templates
- no one-template-per-ensemble-method variants
- no broad diagnostics or validation framework
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
`docs/CLEARML_UI_SPEC.md` is the screen-level UI guide.
`docs/ROADMAP.md` is the current-vs-future boundary.

## Checks

During development, run:

```powershell
uv run --group quality nox -s quality-fast
```

Before finishing a change, run:

```powershell
uv run --group quality nox -s quality-pr
```

## Review Response Rules

- Do not run `git push` from this repository unless the user explicitly requests it.
- Do not display, create, or commit secrets, credentials, ClearML API keys, or `.env` contents.
- Keep each change focused on one purpose. Do not mix review responses with unrelated improvements.
- Add characterization tests before large refactors.
- Split `pipeline.py`, `infer.py`, and `plots.py` only after existing-output compatibility tests are in place.
- If ClearML localhost UI or Kubernetes verification cannot be run, record `manual verification required`.
- Prefer `pyproject.toml` / uv-managed dependencies for dependency changes.
- Edit requirements files only for compatibility reasons, and record the reason in the work log.
