# Development Guidelines

Keep changes close to the current ownership boundary.

| Change | Start here | Notes |
| --- | --- | --- |
| Model support | `models.py`, `policy.py`, tests | Do not add model-specific templates. |
| Feature processing | `features.py`, `training/preprocessing.py` | Preserve fit/transform consistency. |
| Metrics or ranking | `metrics.py`, `training/ranking.py`, `training/evaluation.py` | Keep selection direction explicit; keep artifact writes out of ranking helpers. |
| Evaluation artifacts | `training/leaderboard_artifacts.py`, `training/prediction_artifacts.py`, `training/best_model_artifacts.py` | Keep `training/evaluation.py` as orchestration and do not rename existing artifacts without characterization tests. |
| Tabular stage execution | `stage.py`, `stage_inputs.py`, `stage_result.py` | Keep stage dispatch, input resolution, and result writing separate. |
| Inference behavior | `inference/*` | Preserve schema check and prediction column order. |
| Plot/table output | `plotting/*` | Keep ClearML-readable tables and small, useful plots. |
| Pipeline graph plan | `domain_plan.py`, `clearml/pipeline_plan.py` | Keep domain step expansion separate from ClearML SDK draft sync. |
| Inference source resolution | `clearml/source_resolution.py`, `clearml/adapter.py` | Keep task/artifact selection separate from SDK import and logger wrappers. |
| ClearML result reporting | `clearml/reports.py`, `clearml/reporting_scalars.py`, `clearml/reporting_targets.py` | Report domain-produced artifacts; keep scalar extraction and UI naming rules separate. |
| ClearML runtime behavior | `clearml/adapter.py`, `clearml/pipeline_controller.py`, `clearml/templates.py`, `clearml/reports.py` | Keep SDK usage out of `pkgs/core` and `pkgs/tabular`. |

Prefer `uv run python ...` commands for local checks.

Before opening a PR:

```powershell
uv run python -m compileall clearml pkgs scripts
uv run python -m pytest
uv run python -m ruff check .
```

Formatting-only cleanup should be a separate commit.
