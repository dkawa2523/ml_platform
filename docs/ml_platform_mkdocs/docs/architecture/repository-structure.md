# Repository Structure

The repository is split by runtime boundary and tabular domain ownership.

| Path | Role |
| --- | --- |
| `pkgs/core/` | ClearML-free shared config, IO, artifacts, results, runtime contracts, and source-version lookup. |
| `pkgs/tabular/` | ClearML-free tabular regression implementation. |
| `pkgs/clearml/` | ClearML SDK adapter, template sync, pipeline rendering, and reporting. |
| `clearml/` | Thin direct-file wrappers retained for synced template paths. |
| `scripts/` | Local operator wrappers. |
| `config/tasks/` | User-facing and internal task YAML. |
| `config/profiles/` | Local and ClearML environment profiles. |
| `tests/` | Behavior and smoke tests grouped by product responsibility. |

## Tabular Package

| Area | Canonical modules |
| --- | --- |
| Data loading and split | `data/loading.py`, `data/selection.py`, `data/splitting.py`, `data_quality.py` |
| Feature processing | `feature_config.py`, `features.py` |
| Models and metrics | `model_catalog.py`, `model_candidates.py`, `model_presets.py`, `models.py`, `metrics.py`, `ensemble.py`, `policy.py` |
| Runtime parameter defaults | `runtime_defaults.py` |
| Training flow | `training/preprocess_data.py`, `training/preprocess_artifacts.py`, `training/candidate_training.py`, `training/ensemble.py`, `training/evaluation.py`, `training/orchestrator.py` |
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

## ClearML Runtime Package

| File | Role |
| --- | --- |
| `app.py` | Direct task entrypoint for stage and inference templates. |
| `naming.py` | Project layout, task naming, and tags. |
| `model_source_resolution.py` | Select inference model artifacts from task families. |
| `stage_input_resolution.py` | Expand stage artifact references into local paths. |
| `template_spec.py` | Template definitions, metadata, and default parameters. |
| `pipeline_params.py` | Pipeline New Run defaults and parameter normalization. |
| `pipeline_plan.py` | Training plan orchestration and dry-run presentation. |
| `pipeline_steps.py` | Artifact handoff wiring and ClearML step rendering. |
| `pipeline_controller.py` | PipelineController draft sync and pipeline run orchestration. |
| `pipelines.py` | Direct pipeline entrypoint. |
| `templates.py` | Template persistence and Pipeline-tab draft sync. |
| `adapter.py` | ClearML Task, Dataset, StorageManager, and Logger wrapper. |
| `reports.py` | `RunResult` reporting orchestration. |
| `reporting_scalars.py` | Scalar extraction from metrics artifacts and tables. |
| `reporting_targets.py` | ClearML table/plot reporting names and duplicate-suppression rules. |

All files in this table are under
`pkgs/clearml/src/ml_platform_clearml/`. The direct `clearml/app.py` and
`clearml/pipelines.py` paths only preserve synced template compatibility.
