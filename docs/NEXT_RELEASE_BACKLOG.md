# Next Release Backlog

Current scope is defined in `docs/SPEC.md`. Keep this backlog short; do not add
issue-template style process docs.

## Now

1. ClearML remote verification for `tabular_train_pipeline_template`.
   - Purpose: prove the stage graph on the dev server.
   - Scope: run with ClearML Dataset id/file, supported model candidates, ensemble on.
   - Acceptance: graph shows `preprocess_features -> train_<model>* -> build_ensemble -> evaluate_models`; required artifacts are visible.
   - Do not do: add full templates, optimization templates, or model-specific templates.

2. ClearML remote inference verification for `tabular_infer_template`.
   - Purpose: prove source-task inference from a completed training pipeline.
   - Scope: run `model_selector=best` and `model_selector=ensemble`.
   - Acceptance: `predictions.csv` and `manifest.json` are visible; source task and selector are recorded.
   - Do not do: create an inference pipeline or online serving API.

3. ClearML UI input polish.
   - Purpose: make required remote parameters obvious.
   - Scope: template tags, descriptions, and short docs for `clearml_dataset_id`, `dataset_file`, `target_column`, candidates, and ensemble.
   - Acceptance: users can distinguish local path from remote Dataset usage without reading code.
   - Do not do: add broad troubleshooting, contracts, or diagnostics helpers.

## Later

- Revisit optimization pipeline only after the primary training and inference
  route is stable.
- Keep experimental LightGBM, XGBoost, CatBoost out of default candidates until
  optional dependency and remote evidence are recorded.
- Keep Optuna, Ray Tune, per-trial child tasks, stacking, advanced diagnostics,
  and online serving out of the primary flow.

## Delete Candidates After Human Review

- Remaining historical verification files that continue to be mistaken for
  current readiness evidence.
- Obsolete compatibility docs that duplicate `docs/SPEC.md`.
- Legacy `tabular_train_template`, `tabular_eval_template`, and old
  `train -> eval -> infer` instructions if no longer useful for migration.
