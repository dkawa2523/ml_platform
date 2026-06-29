# Development Guidelines

Keep changes close to the current ownership boundary.

| Change | Start here | Notes |
| --- | --- | --- |
| Model support | `models.py`, `policy.py`, tests | Do not add model-specific templates. |
| Feature processing | `features.py`, `training/preprocessing.py` | Preserve fit/transform consistency. |
| Metrics or ranking | `metrics.py`, `training/ranking.py`, `training/evaluation.py` | Keep selection direction explicit. |
| Evaluation artifacts | `training/evaluation.py`, `training/summary.py`, `training/recommendation.py` | Do not rename existing artifacts without characterization tests. |
| Inference behavior | `inference/*` | Preserve schema check and prediction column order. |
| Plot/table output | `plotting/*` | Keep ClearML-readable tables and small, useful plots. |
| ClearML runtime behavior | `clearml/adapter.py`, `clearml/pipelines.py`, `clearml/templates.py`, `clearml/reports.py` | Keep SDK usage out of `pkgs/core` and `pkgs/tabular`. |

Prefer `uv run python ...` commands for local checks.

Before opening a PR:

```powershell
uv run python -m compileall clearml pkgs scripts
uv run python -m pytest
uv run python -m ruff check .
```

Formatting-only cleanup should be a separate commit.
