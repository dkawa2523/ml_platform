# ClearML UI Review

> Historical note: this file reviews the old full-run compatibility flow and its
> fixed `train -> eval -> infer` graph. It is not current product readiness
> evidence for the official stage-based training pipeline.

## Evidence Reviewed

- Template sync evidence for four templates.
- Linear, ridge, random_forest, and gradient_boosting train/eval/infer task URLs.
- Linear, ridge, random_forest, and gradient_boosting pipeline URLs.
- SDK metadata for task status, parameters, metrics, artifacts, and pipeline steps.
- Docs for worker slots and Dataset artifact URL reachability.

## ClearML UI User View

- Templates are limited to four: train, eval, infer, pipeline.
- Parameters remain under `Input`, `Run`, `Model`, and `Output`.
- Dataset selection is clear enough for v1:
  - Use `Input/clearml_dataset_id` for Agent runs.
  - Use `Input/dataset_file` when the Dataset has multiple files.
  - Use `Input/local_path` only for paths inside the Agent container or mounted PVC.
- Model switching is simple: edit `Model/name` and `Model/params`.
- Metrics are visible for train and eval tasks.
- Artifacts are named plainly: `metrics`, `manifest`, `model`, `model_info`, `validation_predictions`, `evaluation_predictions`, and `predictions`.
- Pipeline evidence shows the historical compatibility fixed `train -> eval -> infer` graph with traceable model artifact handoff.
- Raw console logs were not stored because Agent configuration output can include credentials.

## Data Scientist View

- Model additions are localized in `pkgs/tabular/src/ml_platform_tabular/models.py`.
- Feature and preprocessing additions are localized in `features.py`.
- Metrics additions are localized in `metrics.py`.
- Local execution remains available without ClearML.
- `random_forest` and `gradient_boosting` are part of V1 after promoting `scikit-learn` to a runtime dependency.

## Architect View

- `pkgs` remains ClearML-independent.
- ClearML SDK usage remains in `clearml/`.
- `scripts` remain wrappers.
- Config remains task plus profile based.
- No model-specific or dataset-specific templates were added.
- No new diagnostics helpers, contract docs, or plugin framework were added.
- Operational docs now cover remote pipeline worker slots and Agent-reachable Dataset artifact URLs.

## Issues

- Direct visual UI inspection was not available from this Codex environment.
- Manual sanitized screenshots can improve handoff confidence, but are not required because task URLs and SDK metadata cover the v1 evidence.

## Decision

Accepted for the historical v1 compatibility flow. UI evidence is sufficient for
that release gate, with optional manual screenshots as a post-gate enhancement.
