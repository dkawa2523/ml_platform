# Product Roadmap

This roadmap keeps future work explicit without adding half-implemented product
surfaces. Current product scope remains in `docs/SPEC.md`; ClearML screen
behavior remains in `docs/CLEARML_UI_SPEC.md`.

## Current Release Scope

- Tabular scalar regression only.
- Stage-based training graph:
  `preprocess_features -> train_<model>* -> build_ensemble_<method>* -> evaluate_models`.
- Separate user-facing inference task: `template/tabular_infer`.
- ClearML-free core packages under `pkgs/core` and `pkgs/tabular`.
- Basic ClearML training controls:
  `Basic/model_suite`, `Basic/quality_mode`, and `Basic/use_ensemble`.
- `Basic/quality_mode` uses fixed bounded parameter presets. It is not HPO.
- Holdout validation only: `random`, `group`, `time`, and `fixed`.
- Lightweight data-quality checks in preprocess.
- `evaluate_models/decision_summary.md` as the canonical inference decision
  artifact.
- Lightweight inference schema checks and slim predictions.

## P2: Future, Not Implemented

### HPO / Hyperparameter Optimization

Status: not implemented.

- Do not add ClearML HyperParameterOptimizer, Optuna, search stages, or
  user-facing search JSON fields in the current product.
- Existing `model.search.enabled=true` is rejected as a future/experimental
  guard.
- Future behavior should sit behind `Basic/quality_mode` or another small
  Basic-level control, not expose raw search spaces to ClearML UI users by
  default.

### Model Registry

Status: not implemented.

- No approved-model registry, promotion workflow, or registry-specific template
  exists today.
- Future behavior should start from `evaluate_models` outputs:
  `decision_summary.md`, `decision_summary.json`, and `recommendation.json`.
- A later flow may turn an accepted recommendation into an approved registered
  model, but training and inference should continue to work without registry
  services.

### Drift / Monitoring

Status: not implemented.

- No monitoring service, scheduled drift job, alerting, or dashboard is part of
  the current product.
- Future behavior should build on accumulated inference artifacts, especially
  `schema_check_summary.csv/json`, `prediction_summary.csv`, and
  `source_summary.csv`.
- Keep checks lightweight and decision-oriented before adding dedicated
  monitoring infrastructure.

### Task Registry

Status: not implemented.

- Current task scope is tabular scalar regression.
- Do not introduce a broad task registry for this release.
- Revisit a task registry only when adding non-scalar outputs, such as 1D/2D
  outputs or mode decomposition, and only if it reduces user-facing ambiguity.

### External Validation And CV

Status: not implemented.

- Current validation is single holdout only.
- `external_valid_file`, k-fold, nested CV, and `group_kfold` are future scope.
- Future UI should keep the common holdout path simple and avoid exposing many
  split variants in the first-run surface.

## Guardrails

- Do not add model-specific, dataset-specific, ensemble-specific, or
  optimization-specific ClearML templates.
- Do not make `pkgs/core` or `pkgs/tabular` import ClearML.
- Do not implement P2 items by adding large abstractions ahead of product need.
- Prefer small user-facing controls and clear artifacts over diagnostic volume.
