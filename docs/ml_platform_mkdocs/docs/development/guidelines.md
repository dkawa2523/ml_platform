# Development Guidelines

Keep changes close to the current ownership boundary.

| Change | Start here | Notes |
| --- | --- | --- |
| Model support | `model_catalog.py`, `models.py`, `model_presets.py`, tests | Do not add model-specific templates. |
| Feature processing | `feature_config.py`, `features.py`, `training/preprocess_data.py` | Preserve fit/transform consistency. |
| Metrics or ranking | `metrics.py`, `training/ranking.py`, `training/evaluation.py` | Keep selection direction explicit; keep artifact writes out of ranking helpers. |
| Evaluation artifacts | `training/leaderboard_artifacts.py`, `training/prediction_artifacts.py`, `training/best_model_artifacts.py` | Keep `training/evaluation.py` as orchestration and do not rename existing artifacts without characterization tests. |
| Tabular stage execution | `stage.py`, `stage_inputs.py`, `stage_result.py` | Keep stage dispatch, input resolution, and result writing separate. |
| Inference behavior | `inference/*` | Preserve schema check and prediction column order. |
| Plot/table output | `plotting/*` | Keep ClearML-readable tables and small, useful plots. |
| Pipeline graph plan | `domain_plan.py`, `ml_platform_clearml.pipeline_*` | Keep domain expansion independent from ClearML graph rendering. |
| Inference source resolution | `ml_platform_clearml.model_source_resolution`, `ml_platform_clearml.adapter` | Validate task metadata before downloading model artifacts. |
| ClearML result reporting | `ml_platform_clearml.reporting_*`, `ml_platform_clearml.reports` | Report domain-produced artifacts; keep UI naming out of tabular processing. |
| ClearML runtime behavior | `pkgs/clearml/src/ml_platform_clearml` | Keep SDK usage out of `pkgs/core` and `pkgs/tabular`. |

Prefer `uv run python ...` commands for local checks.

Before opening a PR:

```powershell
uv run --group quality nox -s quality-fast
uv run --group quality nox -s quality-pr
```

Formatting-only cleanup should be a separate commit.
