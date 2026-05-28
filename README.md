# ml_platform

Minimal ML execution platform for tabular regression and small tabular analysis outputs with a strict ClearML boundary.

V1 verified scope is tabular scalar regression with four official models:
`linear`, `ridge`, `random_forest`, and `gradient_boosting`. These models are
verified for local train/eval/infer/pipeline, ClearML task train/eval/infer, and
ClearML train -> eval -> infer pipeline execution.

V1.1 extends the same single-model interface with lightweight sklearn models:
`lasso`, `elasticnet`, `extra_trees`, `knn`, `svr`, and `mlp`. They use the same
`model.name` / `Model/name` and `model.params` / `Model/params` controls; no
model-specific templates or task YAML files are added.

V1.2 adds simple ensemble modes on top of comparison mode. `mean_topk` averages
the top-k models from `leaderboard.csv`; `weighted` uses validation metric based
weights for the same top-k set. Both save the ensemble as the standard
`model.joblib` and keep eval/infer/pipeline unchanged.

V1.3 standardizes batch inference output. `predictions.csv` preserves the input
columns and appends `prediction`, `model_name`, `artifact_kind`, and
`prediction_run_id`. Single-model, best-model, and ensemble artifacts all use the
same infer task.

V2.2 adds operational inference metadata and lightweight chunked prediction.
`predictions.csv` also includes `model_artifact_id`; `Output/chunk_size` can be
set for CSV write/predict chunking without adding serving APIs or a new template.

V2.1 adds minimal train-time hyperparameter search. `grid` and `random` search
run inside the train task, write `optimization_trials.csv` and
`optimization_summary.json` plus `best_params.json`, then save the best params
as the standard retrained `model.joblib`. No Optuna, child-task HPO, or
optimize template is added.

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
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml
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
the best model as `model.joblib`. V1.1 does not include ensemble,
train_ensemble_full, stacking, gaussian_process, LightGBM/XGBoost/CatBoost/TabPFN,
advanced plots, diagnostics, all-model pipeline DAGs, or a separate runtime
leaderboard task.

For V1.2 ensemble mode, add nested `model.ensemble` locally. In ClearML, use
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

For V2.1 search, add nested `model.search` locally or use the flat ClearML
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

Inference writes a table artifact named `predictions` in ClearML. The file name
comes from `output.prediction_name` locally or `Output/prediction_name` in
ClearML. Input tables must not already contain the reserved output columns
`prediction`, `model_name`, `artifact_kind`, `model_artifact_id`, or
`prediction_run_id`. Use `Output/chunk_size` only for CSV batch inference; input
tables are still read eagerly.

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

The ClearML templates are task-type based and remain four templates:
`tabular_train_template`, `tabular_eval_template`, `tabular_infer_template`, and
`tabular_pipeline_template`. Do not create model-specific or dataset-specific
templates. Remote pipeline execution needs enough worker slots for the controller
and step tasks when they share one queue.

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
- `docs/CODEX_HANDOFF.md`
