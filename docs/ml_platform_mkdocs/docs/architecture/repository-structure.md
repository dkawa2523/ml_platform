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
| Models and metrics | `models.py`, `metrics.py`, `ensemble.py`, `policy.py` |
| Training flow | `training/preprocessing.py`, `training/candidate_training.py`, `training/ensemble.py`, `training/evaluation.py`, `training/orchestrator.py` |
| Inference flow | `inference/resolver.py`, `inference/metadata.py`, `inference/schema.py`, `inference/prediction_frame.py`, `inference/prediction_writer.py`, `inference/runner.py` |
| Plots and tables | `plotting/feature.py`, `plotting/prediction.py`, `plotting/candidate.py`, `plotting/leaderboard.py`, `plotting/summary.py` |
| Stage execution | `stage.py`, `stage_inputs.py`, `stage_result.py` |
| Runtime contracts and graph plan | `manifest.py`, `domain_plan.py` |

Runner paths now point directly at the implementation packages:
`ml_platform_tabular.inference:run_infer` and
`ml_platform_tabular.training:run_pipeline`. Plot helpers live under
`ml_platform_tabular.plotting`.

`manifest.py` should stay declarative: task, stage, parameter, and artifact
specifications only. Pipeline step expansion belongs in `domain_plan.py`, and
stage input/path resolution belongs in `stage_inputs.py`.

## ClearML Runtime

| File | Role |
| --- | --- |
| `app.py` | Direct task entrypoint for stage and inference templates. |
| `source_resolution.py` | Resolve inference model sources and stage artifact references. |
| `pipeline_plan.py` | ClearML pipeline parameter defaults and stage graph rendering. |
| `pipeline_controller.py` | PipelineController draft sync and pipeline run orchestration. |
| `pipelines.py` | Direct pipeline entrypoint. |
| `templates.py` | Template sync and Pipeline-tab draft sync. |
| `adapter.py` | ClearML Task, Dataset, StorageManager, and Logger wrapper. |
| `reports.py` | `RunResult` reporting orchestration. |
| `reporting_scalars.py` | Scalar extraction from metrics artifacts and tables. |
| `reporting_targets.py` | ClearML table/plot reporting names and duplicate-suppression rules. |

The direct `clearml/app.py` and `clearml/pipelines.py` paths are kept for
synced ClearML template compatibility.
