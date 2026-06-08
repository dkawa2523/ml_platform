# Productization History

Current product scope is defined in `docs/SPEC.md`. This file is only a compact
history index and must not be used as the release gate.

## Current Direction

The product was narrowed to:

```text
training: preprocess_features -> train_<model>* -> build_ensemble -> evaluate_models
inference: tabular_infer_template with source_task_id + model_selector or local_model_path
templates: tabular_train_pipeline_template, tabular_infer_template, internal tabular_stage_template
```

## Historical Notes

- Early V1/V2 work proved single train, eval, infer, leaderboard, ensemble, and
  simple compatibility flows.
- The old `train -> eval -> infer` flow is historical compatibility evidence,
  not the official training pipeline.
- V2.3 `Run/pipeline_mode`, full pipeline variants, and optimization evidence
  were moved out of primary scope.
- Historical verification files live under `verification/_historical/`.

## Release Gate

Use `verification/training_pipeline/release_gate.md` and
`verification/README.md` for current readiness status.
