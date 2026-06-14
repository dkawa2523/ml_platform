# Next Release Backlog

Keep this list short. Product scope is in `docs/SPEC.md`.

## Required Before Release

1. Re-sync templates after the inference Dataset-default update.
   - Goal: `template/tabular_infer` defaults to an Agent-reachable ClearML
     Dataset instead of repo-local `data/sample_infer.csv`.

2. Remote inference verification from `template/tabular_infer`.
   - Goal: `model_selector=best` and `model_selector=ensemble` both produce
     `predictions.csv`, prediction summary, and prediction distribution plots.

3. Archive stale ClearML server tasks manually after the latest templates are
   confirmed.

## Current Evidence

- Remote training from `template/tabular_train_pipeline` completed on task
  `cf12d910fcbf44d8a94b5b1a6cfef4ff`.
- The run used commit `647bcdfb53283b0fd37ab81535117661c5edfe7a`.
- The graph included 10 `train_<model>` steps, three
  `build_ensemble_<method>` steps, and `evaluate_models`.
- The Agent venv included LightGBM, XGBoost, and CatBoost.

## Later

- Optional local GBM smoke in an environment with `pkgs/tabular[gbm]`.
- Stacking and optimization only after the primary training and inference route
  is stable.
- Advanced diagnostics only when they have a clear user-facing decision value.
