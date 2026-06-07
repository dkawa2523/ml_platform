# ml_platform

Minimal ML execution platform for tabular regression and small tabular analysis outputs with a strict ClearML boundary.

## Current V2 Scope

Supported scope is tabular scalar regression with local and ClearML remote
train, eval, and infer task execution for the official models `linear`, `ridge`,
`random_forest`, and `gradient_boosting`. It also includes comparison mode,
`leaderboard.csv`, best model selection, `mean_topk` and `weighted` ensemble
artifacts, train-time `grid` and `random` search, standardized batch inference
output, optional CSV chunked inference, metrics, artifacts, predictions, and
ClearML Dataset id/file handling. Local stage-based optimization is available
with the same `grid` / `random` search by enabling `model.search` and disabling
ensemble.

`config/tasks/tabular_pipeline.yaml` is the local training pipeline entrypoint.
It runs `preprocess_features -> train_<model>* -> build_ensemble optional ->
evaluate_models` without inference. ClearML stage-based training pipeline drafts
are available through `tabular_train_pipeline_template`,
`tabular_train_full_pipeline_template`, and
`tabular_train_full_ensemble_pipeline_template`; remote verification is still
required before promoting those drafts to supported.

Experimental scope includes implemented features with limited remote
verification or operational caveats: the ClearML stage-based training pipeline
drafts, `lasso`, `elasticnet`, `extra_trees`, `knn`, `svr`, `mlp`, and the
local `tabular_1d_output` utility.

Future scope includes LightGBM, XGBoost, CatBoost, Optuna, Ray Tune, stacking,
per-trial ClearML child tasks, advanced plots, online serving, 1D/2D
productization, distribution mode decomposition, and advanced optimization.

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

Optimization is a separate stage-based pipeline shape, activated by search:

```text
preprocess_features -> search_trials -> retrain_best -> evaluate_best
```

ClearML user-facing training pipeline templates are
`tabular_train_pipeline_template`, `tabular_train_full_pipeline_template`, and
`tabular_train_full_ensemble_pipeline_template`. The internal ClearML stage
template is `tabular_stage_template`.

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
python scripts/local_run.py --task config/tasks/tabular_train.yaml --profile config/profiles/local.yaml
python scripts/local_run.py --task config/tasks/tabular_eval.yaml --profile config/profiles/local.yaml
python scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
# Local stage-based training pipeline. Inference is intentionally separate.
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml
# Local stage-based optimization pipeline. Quote JSON-like overrides in PowerShell.
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set model.ensemble.enabled=false --set 'model.candidates=[]' --set model.name=ridge --set 'model.params={}' --set model.search.enabled=true --set model.search.method=grid --set model.search.max_trials=2 --set 'model.search.search_space={"alpha":[0.1,1.0]}'
python scripts/local_run.py --task config/tasks/tabular_1d_output.yaml --profile config/profiles/local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

Example override:

```powershell
python scripts/local_run.py --task config/tasks/tabular_train.yaml --profile config/profiles/local.yaml --set data.local_path=data/sample_train.csv --set model.name=ridge --set metrics.names=mse,rmse
```

Single-model runs use `model.name` and `model.params` locally, or `Model/name`
and `Model/params` in ClearML. Train also supports comparison mode with
`model.candidates` / `Model/candidates` as a list of model names and
`selection_metric` / `Model/selection_metric`. In comparison mode, `model.params`
can be a mapping from model name to params. The train task writes
`leaderboard.csv`, records comparison summary in `metrics.json`, and saves only
the best model as `model.joblib`. Product scope does not include
legacy `train_ensemble_full`, stacking, gaussian_process,
LightGBM/XGBoost/CatBoost/TabPFN, advanced plots, diagnostics, or a separate
runtime leaderboard task.

For ensemble mode, add nested `model.ensemble` locally. In ClearML, use
the flat Model parameters `Model/ensemble_enabled`, `Model/ensemble_method`, and
`Model/ensemble_top_k`:

```json
{
  "Model/ensemble_enabled": true,
  "Model/ensemble_method": "mean_topk",
  "Model/ensemble_top_k": 3
}
```

Use `Model/ensemble_method=weighted` for validation metric based weights. This is
a best-of-comparison ensemble artifact, not train_ensemble_full, stacking, or
weight optimization.

For train-time search, add nested `model.search` locally or use the flat ClearML
parameters `Model/search_enabled`, `Model/search_method`, `Model/search_space`,
and `Model/max_trials`. `Model/search_space` is a JSON object string:

```json
{
  "Model/search_enabled": true,
  "Model/search_method": "grid",
  "Model/search_space": "{\"alpha\":[0.1,1.0,10.0]}",
  "Model/max_trials": 20
}
```

With `Model/candidates`, use a model-keyed search space such as
`{"ridge":{"alpha":[0.1,1.0]},"random_forest":{"max_depth":[null,5]}}`.
In the stage-based training pipeline, `model.search.enabled=true` switches the
graph to `preprocess_features -> search_trials -> retrain_best -> evaluate_best`
when ensemble is disabled.

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
training pipeline run directory or a model file.

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

The default ClearML sync targets are `tabular_infer_template`,
`tabular_stage_template`, and three Pipeline-tab drafts:
`tabular_train_pipeline_template`, `tabular_train_full_pipeline_template`, and
`tabular_train_full_ensemble_pipeline_template`. `tabular_stage_template` is an
internal PipelineController step target; users should start the user-facing
Pipeline-tab drafts or the inference task. Deprecated
`tabular_train_template`, `tabular_eval_template`, and
`tabular_pipeline_template` are legacy compatibility targets and are not the
official training pipeline templates. Do not create model-specific or
dataset-specific templates. Remote PipelineController execution needs enough
worker slots for the controller and step tasks when they share one queue.

Compatibility simple full-run executions use `Run/pipeline_mode` to make the
old flow explicit while keeping the physical graph fixed:

```text
auto
single
compare
ensemble
optimize
```

V2.3 local mode names are `single`, `compare`, `ensemble`, and `optimize`;
`single_model`, `comparison`, and `optimization` are accepted as compatibility
aliases. `compare` requires `Model/candidates`, `ensemble` requires candidates
and uses `Model/ensemble_*`, and `optimize` requires `Model/search_space`.
Compatibility flow `eval` and `infer` always consume the standard `model`
artifact from the `train` step, whether that artifact is a single model,
selected best model, ensemble, or optimized model. These modes are not official
training pipeline modes.

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
