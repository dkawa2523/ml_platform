# ml_platform

Minimal ML execution platform for tabular regression and small tabular analysis outputs with a strict ClearML boundary.

## Current V2 Scope

Primary scope is tabular scalar regression with a ClearML-visible training
pipeline and a separate inference task for the official models `linear`,
`ridge`, `random_forest`, and `gradient_boosting`. It includes multiple model
training, `leaderboard.csv`, best model selection, `mean_topk` and `weighted`
ensemble artifacts, standardized batch inference output, metrics, artifacts,
predictions, and ClearML Dataset id/file handling.

`config/tasks/tabular_pipeline.yaml` is the official training pipeline config.
It runs `preprocess_features -> train_<model>* -> build_ensemble ->
evaluate_models` without inference. ClearML sync exposes only
`tabular_train_pipeline_template`, `tabular_infer_template`, and the internal
`tabular_stage_template`.

Experimental / future scope includes optimization, `artifact_url` /
`clearml_model_id` inference sources, external model full pipelines, `lasso`,
`elasticnet`, `extra_trees`, `knn`, `svr`, `mlp`, and the local
`tabular_1d_output` utility.

Future scope includes LightGBM, XGBoost, CatBoost, Optuna, Ray Tune, stacking,
per-trial ClearML child tasks, advanced plots, online serving, 1D/2D
productization, and distribution mode decomposition.

Discarded scope includes legacy full parity, excessive contracts and checklists,
diagnostics helpers, old adapter splits, live cleanup, model-specific templates,
dataset-specific templates, and legacy repo directory/config recreation.

Detailed scope is defined in `docs/SPEC.md`. This repo is not full parity with
the legacy repos; they are reference material only.

## Training And Inference Shape

The local training pipeline is:

```text
preprocess_features -> train_<model>* -> build_ensemble optional -> evaluate_models
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
- Keep ClearML UI parameters within `Input`, `Run`, `Model`, and `Output`.

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

The training pipeline uses `model.candidates` / `Model/candidates`,
`model.ensemble` / `Model/ensemble_*`, and `Model/selection_metric`. Product
scope does not include legacy `train_ensemble_full`, stacking,
LightGBM/XGBoost/CatBoost/TabPFN, advanced plots, diagnostics, runtime
leaderboard tasks, or weight optimization.

Optimization is future / experimental. Do not present search settings as the
primary ClearML UI flow.

Inference writes a table artifact named `predictions` in ClearML. The file name
comes from `output.prediction_name` locally or `Output/prediction_name` in
ClearML. Input tables must not already contain the reserved output columns
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

The default ClearML sync targets are `tabular_train_pipeline_template`,
`tabular_infer_template`, and `tabular_stage_template`. `tabular_stage_template`
is an internal PipelineController step target; users should start
`tabular_train_pipeline_template` from the Pipeline tab or clone
`tabular_infer_template` for inference. Deprecated `tabular_train_template`,
`tabular_eval_template`, `tabular_pipeline_template`, and `tabular_train_full_*`
templates are not primary sync targets. Do not create model-specific,
ensemble-specific, optimization-specific, or dataset-specific templates. Remote
PipelineController execution needs enough worker slots for the controller and
step tasks when they share one queue.

Pipeline dry-run:

```powershell
python clearml/pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
```

## Deploy

See `deploy/README.md`. The deploy manifests are a minimal ClearML Agent runtime. Secrets, image registry, namespace, and storage class are environment-owned.

## Read Next

- `AGENTS.md`
- `docs/SPEC.md`
- `docs/PROHIBITIONS.md`
- `docs/LEGACY_REPO_POLICY.md`
- `docs/PRODUCTIZATION_PHASES.md`
- `docs/NEXT_RELEASE_BACKLOG.md`
- `docs/CODEX_HANDOFF.md`
- `verification/README.md`
