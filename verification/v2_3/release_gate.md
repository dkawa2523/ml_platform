# V2.3 Pipeline Execution UX Release Gate

> Historical note: this file records the deprecated V2.3 compatibility full-run
> flow (`train -> eval -> infer`). It is not current product readiness evidence
> for the official stage-based training or optimization pipelines.

Date: 2026-06-02
Validated code commit: `146dd53`
Scope: local pipeline, ClearML task templates, ClearML Pipeline-tab draft, and
four ClearML dev pipeline runs
Prod access: not touched
Screenshots: none saved
Secrets/Dataset IDs: not stored

## Result

| gate | status | evidence |
| --- | --- | --- |
| Architecture | pass | ClearML SDK references are limited to `clearml/`; `pkgs` has no ClearML import. |
| Local pipeline modes | pass | `single`, `compare`, `ensemble`, and `optimize` verification files exist and passed. |
| ClearML pipeline modes | pass | `single`, `compare`, `ensemble`, and `optimize` dev runs completed. |
| Artifacts | pass | Required train/eval/infer artifacts are present on step tasks. |
| ClearML UI | pass | Pipeline-tab draft exposes `Run/pipeline_mode` and grouped Input/Run/Model/Output parameters. |
| Docs / verification | pass | README/docs match the V2.3 scope and verification records exist. |

Overall decision: V2.3 compatibility full-run UX was ready for that historical
flow only.

## Commands

| command | status | note |
| --- | --- | --- |
| `python scripts/make_sample_data.py` | pass with venv Python | `python` resolves to the Windows Store alias in this shell; `.\.venv\Scripts\python.exe` was used. |
| `python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml` | pass with venv Python | Default config ran as `pipeline_mode=single`. |
| `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q` | pass with venv Python | `46 passed`. |
| `python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run` | pass with venv Python | Reports three task templates plus one Pipeline-tab draft. |
| `python clearml/pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run` | pass with venv Python | Reports historical compatibility fixed `train -> eval -> infer` graph. |

## Architecture Gate

- `pkgs/core` and `pkgs/tabular` do not import ClearML.
- `PipelineController` and `StorageManager` references are limited to
  `clearml/pipelines.py` and `clearml/adapter.py`.
- Local orchestration stays in `pkgs/tabular/src/ml_platform_tabular/pipeline.py`.
- ClearML orchestration stays in `clearml/pipelines.py`.
- Scripts remain wrappers around config loading, local execution, template sync,
  or ClearML pipeline launch.
- Template count is unchanged: `tabular_train_template`,
  `tabular_eval_template`, `tabular_infer_template`, and
  `tabular_pipeline_template`.
- No model-specific, ensemble-specific, optimize-specific, or dataset-specific
  templates were added.

## Pipeline Mode Gate

| mode | local | ClearML dev | product status |
| --- | --- | --- | --- |
| `single` | pass | pass | historical compatibility ready |
| `compare` | pass | pass | historical compatibility ready |
| `ensemble` | pass | pass | historical compatibility ready |
| `optimize` | pass | pass | historical compatibility ready |

## Artifact Gate

| artifact | status | produced by |
| --- | --- | --- |
| `leaderboard` / `leaderboard.csv` | pass | train step in compare/ensemble |
| best model artifact | pass | train step standard `model` artifact |
| ensemble artifact | pass | train step `ensemble_info`, `ensemble_predictions`, base models, and standard `model` artifact |
| `optimization_trials.csv` | pass | train step in optimize |
| `best_params.json` | pass | train step in optimize |
| `evaluation_predictions.csv` | pass | eval step |
| `predictions.csv` | pass | infer step |
| `metrics.json` | pass | train/eval and aggregate local outputs |
| `manifest.json` | pass | train/eval/infer and aggregate local outputs |

## ClearML UI Gate

- `Run/pipeline_mode` makes the mode explicit.
- Input / Run / Model / Output grouping is preserved.
- Metrics are visible on train and eval step Scalars.
- Artifacts are visible on producing step tasks.
- Pipeline graph remains readable as train, eval, infer.
- Logs show step launch and model artifact handoff.
- Parameter count is acceptable for V2.3, but the Model group is dense and needs
  operator examples.

## Non-Blocking Follow-Up

- Document short UI recipes for `single`, `compare`, `ensemble`, and `optimize`.
- Explain that parent controller tasks do not aggregate artifacts or scalars;
  step details are the source of truth.
- Consider setting effective mode-derived params on the parent controller so
  optimize mode does not show misleading default search flags.
- Consider adding train as an explicit infer parent in ClearML pipeline setup to
  avoid the auto-parent console warning.
- Consider de-emphasizing `Run/task` and `Model/feature_preset` later, but do
  not remove them in V2.3.

## Do Not Add

- model-specific templates
- ensemble-specific templates
- optimize-specific templates
- dataset-specific templates
- dynamic DAG framework
- per-trial ClearML child tasks
- parent aggregation task in V2.3
- legacy repo directory/config recreation
- extra checklist, diagnostics, or troubleshooting docs beyond focused
  verification records

## Commit Scope

Commit:

- `verification/v2_3/ui/pipeline_ui_review.md`
- `verification/v2_3/release_gate.md`

Do not commit:

- `outputs/`
- raw ClearML logs
- screenshots
- secrets or local ClearML credentials
- unredacted Dataset IDs
- virtualenv files

Recommended commit message: `Record V2.3 pipeline UX release gate`
Recommended tag after commit: `v2.3.0-pipeline-ux`
