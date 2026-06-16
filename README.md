# ml_platform

ClearML-based tabular regression platform for training, comparing, and running
inference with multiple models and ensemble methods.

## Product Flow

Training is one stage-based pipeline:

```text
preprocess_features -> train_<model>* -> build_ensemble_<method>* -> evaluate_models
```

The preprocess stage reports lightweight data-quality checks so ClearML users
can spot missing values, duplicate rows, high-cardinality columns, and possible
leakage-like feature names early.

After training, open `evaluate_models/decision_summary.md` to choose the
inference settings: `Model/source_type`, `Model/source_task_id`, and
`Model/model_selector`.

Inference is a separate task:

```text
tabular_infer_template -> predictions.csv
```

Inference writes a lightweight schema check and slim predictions with
`row_index`, available ID columns, and `prediction` rather than copying every
input feature.

Primary task configs are:

- `config/tasks/tabular_pipeline.yaml`
- `config/tasks/tabular_stage.yaml`
- `config/tasks/tabular_infer.yaml`

There are no compatibility-only training/evaluation task configs in the current
product surface.

## Models

Supported model names are `linear`, `ridge`, `lasso`, `elasticnet`,
`random_forest`, `extra_trees`, `gradient_boosting`, `lightgbm`, `xgboost`, and
`catboost`.

`lightgbm`, `xgboost`, and `catboost` are supported optional-dependency models.
They are not required package dependencies. Remote ClearML templates reference
the profile's `clearml.execution.image` and install GBM packages into the
Agent-created execution venv. Slim local or custom runs can remove the GBM names
from `Model/candidates`.

Out of scope: `knn`, `svr`, `mlp`, `gaussian_process`, and `tabpfn`.

## Local Run

Install the lightweight local environment:

```powershell
uv venv .venv
.\.venv\Scripts\activate
uv pip install -e pkgs/core -e pkgs/tabular -r requirements-dev.txt
```

Generate sample data and run the portable dependency-free smoke path:

```powershell
python scripts/make_sample_data.py
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set "model.candidates=[linear,ridge,lasso,elasticnet,random_forest,extra_trees,gradient_boosting]"
python scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

Install `pkgs/tabular[gbm]` locally before running the default 10-candidate
training config without an override.

## ClearML

Sync templates:

```powershell
python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml
```

User-facing templates:

- `template/tabular_train_pipeline`
- `template/tabular_infer`

Internal template:

- `internal/tabular_stage`

Profiles route templates, pipelines, stage runs, inference runs, and experiments
to separate ClearML projects. Old server-side tasks can remain visible until a
human archives them.

For a first training run from the Pipeline tab, set the remote input fields and
the Basic group:

- `Input/clearml_dataset_id`
- `Input/dataset_file`
- `Input/target_column`
- `Basic/model_suite=default|fast|interpretable|tree|gbm|custom`
- `Basic/quality_mode=fast|standard|quality`
- `Basic/use_ensemble=true|false`

`Basic/model_suite` changes the generated `train_<model>` steps without editing
JSON. `fast` removes optional GBM models, `interpretable` uses linear-family
models, `tree` uses sklearn tree ensembles, `gbm` uses LightGBM/XGBoost/CatBoost,
and `custom` uses the detailed `Model/candidates` value. `Basic/quality_mode`
applies small fixed parameter presets: `fast` keeps tree/GBM estimator counts
low, `standard` matches the default config, and `quality` modestly increases
estimator counts without HPO.

Advanced JSON parameters remain available for compatibility and precise control:
`Model/candidates`, `Model/model_params_by_name`, `Features/drop_columns`, and
`Features/passthrough_columns`. `Model/ensemble_enabled` is also available as a
detailed override; when explicitly set, it takes precedence over
`Basic/use_ensemble`.

Remote training normally uses `Input/clearml_dataset_id`,
`Input/dataset_file`, and `Input/target_column`. `Input/local_path` is for local
runs or mounted Agent paths only.

Synced remote templates install GBM packages into the ClearML Agent-created venv.
Local or slim custom environments can still fail on `Basic/model_suite=gbm`
unless `pkgs/tabular[gbm]` or equivalent packages are installed.

Pipeline dry-run:

```powershell
python scripts/clearml_pipeline.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
```

## Boundaries

- `pkgs/core` and `pkgs/tabular` do not import ClearML.
- ClearML SDK usage stays under `clearml/`.
- `scripts/` are wrappers around package and ClearML entrypoints.
- Local operators should use `scripts/`; remote ClearML templates still execute
  `clearml/app.py` and `clearml/pipelines.py` directly.
- Do not add model-specific, ensemble-specific, or dataset-specific templates.
- Do not copy legacy repo trees into this repo.

## Read Next

- `AGENTS.md`: development charter
- `docs/SPEC.md`: product source of truth
- `docs/CLEARML_UI_SPEC.md`: ClearML screen behavior
- `docs/ROADMAP.md`: short current-vs-future product roadmap
- `docs/CODEX_HANDOFF.md`: current operator handoff
- `verification/README.md`: current evidence index
