# Next Release Backlog

Keep this list short. Product scope is in `docs/SPEC.md`.

## Required Before Release

1. Publish the profile execution image with `pkgs/tabular[gbm]`.
   - Goal: default 10-model New Run executes on any worker that can pull the image.
   - Evidence: Agent log shows LightGBM, XGBoost, and CatBoost imports work.

2. Remote training verification from `template/tabular_train_pipeline`.
   - Goal: graph shows `preprocess_features`, 10 `train_<model>` steps, three
     `build_ensemble_<method>` steps, and `evaluate_models`.
   - Evidence: `evaluate_models` leaderboard includes base models and ensemble
     rows; Scalars, Tables, Plots, and Artifacts are visible.

3. Remote inference verification from `template/tabular_infer`.
   - Goal: `model_selector=best` and `model_selector=ensemble` both produce
     `predictions.csv`, prediction summary, and prediction distribution plots.

4. Archive stale ClearML server tasks manually after the latest templates are
   confirmed.

## Later

- Optional local GBM smoke in an environment with `pkgs/tabular[gbm]`.
- Stacking and optimization only after the primary training and inference route
  is stable.
- Advanced diagnostics only when they have a clear user-facing decision value.
