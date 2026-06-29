# Repository Structure

The repository is split by runtime boundary and tabular domain ownership.

| Path | Role |
| --- | --- |
| `pkgs/core/` | ClearML-free shared config, IO, artifacts, result, and runtime contracts. |
| `pkgs/tabular/` | ClearML-free tabular regression implementation. |
| `clearml/` | ClearML SDK adapter, task entrypoints, template sync, pipeline rendering, and reporting. |
| `scripts/` | Local operator wrappers. |
| `config/tasks/` | User-facing and internal task YAML. |
| `config/profiles/` | Local and ClearML environment profiles. |
| `tests/` | Contract, smoke, characterization, and adapter tests. |

## Tabular Package

| Area | Canonical modules |
| --- | --- |
| Data and features | `data.py`, `data_quality.py`, `features.py` |
| Models and metrics | `models.py`, `metrics.py`, `ensemble.py` |
| Training flow | `training/preprocessing.py`, `training/candidate_training.py`, `training/ensemble.py`, `training/evaluation.py`, `training/orchestrator.py` |
| Inference flow | `inference/resolver.py`, `inference/metadata.py`, `inference/schema.py`, `inference/prediction_frame.py`, `inference/prediction_writer.py`, `inference/runner.py` |
| Plots and tables | `plotting/feature.py`, `plotting/prediction.py`, `plotting/candidate.py`, `plotting/leaderboard.py`, `plotting/summary.py` |
| ClearML-free stage task | `stage.py` |
| Compatibility facades | `infer.py`, `pipeline.py`, `plots.py` |

`infer.py` and `pipeline.py` are thin runner facades kept for existing runner
paths. New internal code should import implementation modules directly.

`plots.py` is a public compatibility facade. New internal code should import
from `ml_platform_tabular.plotting`.

## ClearML Runtime

| File | Role |
| --- | --- |
| `app.py` | Direct task entrypoint for stage and inference templates. |
| `pipelines.py` | PipelineController rendering and pipeline draft/run orchestration. |
| `templates.py` | Template sync and Pipeline-tab draft sync. |
| `adapter.py` | ClearML Task, Dataset, StorageManager, and Logger wrapper. |
| `reports.py` | `RunResult` to ClearML artifacts, tables, plots, and scalars. |

The direct `clearml/app.py` and `clearml/pipelines.py` paths are kept for
synced ClearML template compatibility.
