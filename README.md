# ml_platform

Minimal ML execution platform for tabular regression and small tabular analysis outputs with a strict ClearML boundary.

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
