# Add A Model

Add models through the existing candidate system. Do not add one template per
model.

## Implementation Points

- Add the model name and dependency class in `models.py`.
- Extend `build_model(name, params)` with a small, explicit branch.
- Add default or suite behavior in `policy.py` only when the model should be
  available through `Basic/model_suite`.
- Keep heavy libraries optional by adding them to the package extra, not the
  base requirements.
- Add tests for validation, model construction, and a small local training run.

## Feature Importance

If the estimator exposes `feature_importances_` or `coef_`, existing plotting
helpers can produce feature importance output. If it cannot, leave that artifact
absent instead of adding placeholder plots.

## Avoid

- New ClearML templates for each model.
- Model-specific orchestration in `training/orchestrator.py`.
- Required heavy dependencies for optional GBM-style models.
