# Next Release Backlog

Keep this list short. Product scope is in `docs/SPEC.md`.

## Required Before Release

1. Archive stale ClearML server tasks manually after the latest templates are
   confirmed.

## Current Evidence

- Remote training from `template/tabular_train_pipeline` completed on task
  `cf12d910fcbf44d8a94b5b1a6cfef4ff`.
- The run used commit `647bcdfb53283b0fd37ab81535117661c5edfe7a`.
- The graph included 10 `train_<model>` steps, three
  `build_ensemble_<method>` steps, and `evaluate_models`.
- The Agent venv included LightGBM, XGBoost, and CatBoost.
- Remote inference from `template/tabular_infer` completed on task
  `f47d25d6862f4949ba56825c0ae3b002`.
- The inference run used commit `2d5e2f6b4950253c299500a3f667e78ecda85520`
  and produced prediction tables, distribution plot, and artifacts.

## Later

- Optional local GBM smoke in an environment with `pkgs/tabular[gbm]`.
- Stacking and optimization only after the primary training and inference route
  is stable.
- Advanced diagnostics only when they have a clear user-facing decision value.
