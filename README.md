# ml_platform

Minimal ML execution platform for tabular regression and small tabular analysis outputs with a strict ClearML boundary.

## Current V2 Scope

Primary scope is tabular scalar regression with a ClearML-visible training
pipeline and a separate inference task. Dependency-free supported models are
`linear`, `ridge`, `lasso`, `elasticnet`, `random_forest`, `extra_trees`, and
`gradient_boosting`. Optional-dependency supported models are `lightgbm`,
`xgboost`, and `catboost`. It includes multiple model training,
`leaderboard.csv`, best model selection, multiple ensemble methods,
standardized batch inference output, metrics, artifacts, predictions, residual
columns, feature/preprocess summary tables, lightweight validation plots,
feature importance where available, ensemble member/weight tables, and ClearML
Dataset id/file handling.

`config/tasks/tabular_pipeline.yaml` is the official training pipeline config.
It runs `preprocess_features -> train_<model>* -> build_ensemble_<method>* ->
evaluate_models` without inference. Each ensemble step reuses the same internal
stage template with a different method. ClearML sync exposes only
`tabular_train_pipeline_template`, `tabular_infer_template`, and the internal
`tabular_stage_template`.

Portable default candidates may remain dependency-free. Optional-dependency
supported models are runnable when the dependency is installed in the local or
ClearML Agent environment, for example with
`pip install -e "pkgs/tabular[gbm]"`. Missing optional dependencies
must not break dependency-free model runs.

Future scope includes optimization, `artifact_url` / `clearml_model_id`
inference sources, Optuna, Ray Tune, per-trial ClearML child tasks, advanced
diagnostics, online serving, 1D/2D productization, and distribution mode
decomposition.

Discarded scope includes legacy full parity, excessive contracts and checklists,
diagnostics helpers, old adapter splits, live cleanup, model-specific templates,
dataset-specific templates, one-template-per-ensemble-method variants, `knn`,
`svr`, `mlp`, `gaussian_process`, `tabpfn`, stacking, and legacy repo
directory/config recreation.

Detailed scope is defined in `docs/SPEC.md`. This repo is not full parity with
the legacy repos; they are reference material only.
ClearML screen-level operation details are in `docs/CLEARML_UI_SPEC.md`.

## Training And Inference Shape

The local training pipeline is:

```text
preprocess_features -> train_<model>* -> build_ensemble_<method>* -> evaluate_models
```

Inference is a separate `tabular_infer_template` task:

```text
trained model / best model / ensemble artifact -> inference dataset -> predict
```

Optimization remains future / experimental and is not a primary ClearML UI
entrypoint.

ClearML user-facing templates are `tabular_train_pipeline_template` and
`tabular_infer_template`. The internal ClearML stage template is
`tabular_stage_template`.

The product repo is intentionally small:

```text
config/   task and profile YAML
pkgs/     ClearML-free core and tabular packages
clearml/  ClearML adapters, template sync, and pipeline controller
scripts/  thin local/operator wrappers
deploy/   minimal ClearML Agent runtime manifests
docs/     short design and handoff notes
tests/    smoke and boundary tests
```

## Rules

- Do not import ClearML from `pkgs/core` or `pkgs/tabular`.
- Keep ClearML SDK usage under `clearml/`.
- Keep `scripts/` as wrappers only.
- Keep config on two axes: `config/tasks` and `config/profiles`.
- Do not copy legacy repo trees or recreate their directory layout.
- Use compact ClearML UI parameter groups by default, but semantic groups such
  as `Split`, `Features`, `Models`, `Ensemble`, and `Evaluation` are allowed
  when they make New Run forms easier to understand.

## Local Run

```powershell
uv venv .venv
.\.venv\Scripts\activate
uv pip install -e pkgs/core -e pkgs/tabular -r requirements-dev.txt

python scripts/make_sample_data.py
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml
python scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

`config/tasks/tabular_train.yaml` and `config/tasks/tabular_eval.yaml` remain
compatibility task configs. They are not the official training pipeline.

Training pipeline override example:

```powershell
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set model.candidates="[linear,ridge]" --set model.ensemble.enabled=false
```

The training pipeline uses `model.candidates`, model-keyed parameters,
feature/split settings, one or more ensemble methods, evaluation metrics, and a
selection metric. ClearML UI should expose these through semantic groups such as
`Models`, `Ensemble`, `Evaluation`, `Features`, and `Split`; existing `Model/*`
keys may remain compatibility aliases during implementation.
As the ClearML UI surface evolves, preprocessing and feature settings should be
visible through semantic groups such as `Split` and `Features` rather than
hidden as developer-only config.
Product scope does not include legacy `train_ensemble_full`, stacking, TabPFN,
KNN/SVR/MLP, advanced diagnostics, runtime leaderboard tasks, or weight
optimization.

ClearML users choose models through `Model/candidates`; this repo does not add
model-specific templates. Optional-dependency supported model names should be
used only in environments with the matching optional dependency installed.

Optimization is future / experimental. Do not present search settings as the
primary ClearML UI flow.

Inference writes table artifacts named `predictions` and `prediction_summary`,
plus a lightweight prediction distribution plot. The prediction file name comes
from `output.prediction_name` locally or `Output/prediction_name` in ClearML.
Input tables must not already contain the reserved output columns
`prediction`, `model_name`, `artifact_kind`, `model_artifact_id`, or
`prediction_run_id`. Use `Output/chunk_size` only for CSV batch inference; input
tables are still read eagerly.

For ClearML inference from a training pipeline, clone `tabular_infer_template`
and set `Model/source_type=task_id`, `Model/source_task_id=<pipeline or stage
task id>`, and `Model/model_selector=best` or `ensemble`. Local inference can
use `Model/source_type=local_path` with `Model/local_model_path` pointing at a
training pipeline run directory or a model file. `artifact_url` and
`clearml_model_id` are future / experimental sources and are not primary
template UI parameters.

## ClearML

ClearML is optional for local development. Install the SDK only when syncing templates or running tasks through a ClearML server.

```powershell
uv pip install clearml
python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml
```

Before a real sync or Agent run, update `config/profiles/clearml-dev.yaml` or `config/profiles/clearml-prod.yaml`:

- `repository`
- `branch`
- `working_dir`
- `queue`
- `artifact_output_uri` when the server has no default artifact storage

For local runs, use `data.local_path` or `Input/local_path`. For ClearML Agent
runs, prefer `Input/clearml_dataset_id` and use `Input/dataset_file` when a
Dataset contains multiple files. Dataset artifact URLs must be reachable from the
Agent environment; host-only `localhost` URLs and host filesystem paths usually
are not. `artifact_output_uri` controls newly produced run artifacts and does not
fix Dataset storage reachability.

Primary training parameters:

| parameter | local | ClearML remote | note |
| --- | --- | --- | --- |
| `Input/local_path` | required | avoid | Agent can use it only if the path exists inside the Agent container/PVC. |
| `Input/clearml_dataset_id` | optional | required | Preferred remote data source. |
| `Input/dataset_file` | optional | required when Dataset has multiple files | Example: `sample_train.csv`. |
| `Input/target_column` | required | required | Default sample value is `target`. |
| `Input/feature_columns` | optional | optional | Empty means auto-select non-target, non-id columns. |
| `Input/id_columns` | optional | optional | Excluded from features. |
| `Split/valid_size` | optional | optional | Validation split fraction. |
| `Features/preset` | optional | optional | Feature transformer preset, for example `basic` or `numeric_only`. |
| `Features/numeric_impute_strategy` | optional | optional | `median`, `mean`, or `zero`. |
| `Features/categorical_impute_strategy` | optional | optional | `missing_token` or `mode`. |
| `Features/categorical_encoder` | optional | optional | `onehot` or `drop`. |
| `Features/scaling` | optional | optional | `standard` or `none`. |
| `Features/drop_columns` | optional | optional | JSON array or comma list of selected columns to remove before fitting features. |
| `Features/passthrough_columns` | optional | optional | Numeric raw feature columns appended without impute/encoding/scaling. |
| `Model/candidates` | optional | optional | JSON array. Portable defaults may be dependency-free; optional supported models require their dependencies. |
| `Model/model_params_by_name` | optional | optional | JSON object keyed by model name. |
| `Model/ensemble_enabled` | optional | optional | Enables ensemble building. |
| `Model/ensemble_methods` | optional | optional | JSON array or comma list, for example `["mean_topk","weighted","median"]`. |
| `Model/ensemble_top_k` | optional | optional | Number of ranked base models for top-k methods. |
| `Model/evaluation_metrics` | optional | optional | JSON array or comma-separated metric names. |
| `Model/selection_metric` | optional | optional | `rmse`, `mae`, or `r2`; used for leaderboard selection. |
| `Output/report_plots` | optional | optional | Set false to skip ClearML plot media reporting. |

The default ClearML sync targets are `tabular_train_pipeline_template`,
`tabular_infer_template`, and `tabular_stage_template`. They appear in ClearML as
`template/tabular_train_pipeline`, `template/tabular_infer`, and
`internal/tabular_stage`. The stage template is internal; users should start the
training entry from the Pipeline tab or clone the inference task. Profiles route
templates, pipelines, stage runs, and task runs to separate ClearML projects such
as `MLPlatform/Dev/Templates/Tabular` and `MLPlatform/Dev/Pipelines/Tabular`.
Deprecated `tabular_train_template`, `tabular_eval_template`,
`tabular_pipeline_template`, and `tabular_train_full_*` templates are
sync-excluded and are not primary entrypoints. Old ClearML runs may remain
visible until manually archived on the server. Remote PipelineController
execution needs enough worker slots for the controller and step tasks when they
share one queue.

Pipeline dry-run:

```powershell
python clearml/pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
```

## Deploy

See `deploy/README.md`. The deploy manifests are a minimal ClearML Agent runtime. Secrets, image registry, namespace, and storage class are environment-owned.

## Read Next

- `AGENTS.md`
- `docs/SPEC.md`
- `docs/CLEARML_UI_SPEC.md`
- `docs/CODEX_HANDOFF.md`
- `verification/README.md`
