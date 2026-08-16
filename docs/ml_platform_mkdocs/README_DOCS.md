# MkDocs Notes

This directory contains the MkDocs site for `ml_platform`.

Use the root `pyproject.toml` docs dependency group as the source of truth:

```powershell
uv sync --group docs
uv run --group docs python -m mkdocs serve --config-file docs\ml_platform_mkdocs\mkdocs.yml
uv run --group docs python -m mkdocs build --config-file docs\ml_platform_mkdocs\mkdocs.yml --strict
```

Generated HTML is written to `docs/ml_platform_mkdocs/site/` and should not be
committed.
