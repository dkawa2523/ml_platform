# V1 Verification Summary

> Historical note: this file mixes current task evidence with the old fixed
> `train -> eval -> infer` compatibility pipeline evidence. Use
> `verification/README.md` and `docs/SPEC.md` for current product readiness.

## Supported Scope

- Official models: `linear`, `ridge`, `random_forest`, `gradient_boosting`
- Verified local execution: train, eval, infer, and historical compatibility
  `train -> eval -> infer` pipeline
- Verified ClearML task execution: train, eval, infer for each official model
- Verified historical compatibility ClearML pipeline execution:
  `train -> eval -> infer` for each official model
- Verified comparison mode: `Model/candidates` plus `Model/selection_metric` writes `leaderboard.csv` and saves only the best model artifact

## Evidence

- Local full verification: `verification/v1/local_full_verification.md`
- ClearML task verification: `verification/v1/clearml_tasks/summary.md`
- ClearML pipeline verification: `verification/v1/clearml_pipelines/summary.md`
- Leaderboard verification: `verification/v1/models/leaderboard_verification.md`

## ClearML Template Policy

- Templates remain task-type based:
  - `tabular_train_template`
  - `tabular_eval_template`
  - `tabular_infer_template`
  - `tabular_pipeline_template`
- Use `Model/name` and `Model/params` for single-model runs.
- Use `Model/candidates` and `Model/selection_metric` for comparison mode.
- Do not add model-specific, dataset-specific, or leaderboard-specific templates.

## Not Included In V1

- ensemble, stacking, weighted ensemble, and train_ensemble_full
- LightGBM, XGBoost, CatBoost, and TabPFN
- advanced plots
- diagnostics helpers
- all-model pipeline DAGs
- separate runtime leaderboard tasks

## Operational Notes

- ClearML Agent runs should use an Agent-reachable Dataset artifact URL.
- `artifact_output_uri` controls output artifact storage and does not fix Dataset storage reachability.
- Remote pipeline execution on one queue needs enough worker slots for the controller and step tasks.

## Decision

- V1 verified scope ready: yes, including historical compatibility pipeline
  evidence only
