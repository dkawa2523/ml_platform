# Environment

Use uv for local development:

```powershell
uv sync --group dev
```

The root `pyproject.toml` and `uv.lock` are the source of truth.
`requirements.txt` and `requirements-dev.txt` remain compatibility files for
Docker, ClearML remote setup, and legacy pip-based environments.

## Local Smoke

```powershell
uv run python scripts/make_sample_data.py
uv run python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set "model.candidates=[linear,ridge,lasso,elasticnet,random_forest,extra_trees,gradient_boosting]"
uv run python scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
uv run python -m pytest -q
```

## Optional GBM Dependencies

The base environment stays light. Install tabular GBM extras only when local
runs need LightGBM, XGBoost, or CatBoost:

```powershell
uv sync --extra gbm --group dev
```

ClearML synced templates add GBM packages to the remote execution venv for
10-model runs.

## Docs

```powershell
uv sync --group docs
uv run --group docs python -m mkdocs serve --config-file docs\ml_platform_mkdocs\mkdocs.yml
uv run --group docs python -m mkdocs build --config-file docs\ml_platform_mkdocs\mkdocs.yml --strict
```
