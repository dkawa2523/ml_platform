# Verification Scope Index

This directory contains both current product evidence and older compatibility
evidence. Historical records are preserved, but they are not the readiness gate
for the current stage-based training or inference specifications.

## Current Product Evidence

| area | evidence | status |
| --- | --- | --- |
| Release gate | `verification/training_pipeline/release_gate.md` | Current gate. Local/dry-run pass; remote ClearML execution pending. |
| Model policy | `verification/product_ux/model_policy.md` | Current local/dry-run pass for supported, experimental, and out-of-scope model policy. |
| ClearML project layout | `verification/product_ux/clearml_project_layout.md` | Current dry-run pass for project routing, task naming, and tags. |
| Pipeline input UX | `verification/product_ux/pipeline_inputs.md` | Current dry-run pass for required/optional Pipeline UI parameters. |
| Results and plots UX | `verification/product_ux/results_and_plots.md` | Current local/dry-run pass for result artifacts, tables, scalars, and lightweight plots. |
| Local training pipeline | `verification/training_pipeline/local_training_pipeline.md` | Current local pass for `preprocess_features -> train_<model>* -> build_ensemble optional -> evaluate_models`. |
| ClearML training pipeline | `verification/training_pipeline/clearml_training_pipeline.md` | Dry-run pass. Remote ClearML run is still required before support promotion. |
| Inference task | `verification/inference/infer_task_reference.md` | Current evidence for `tabular_infer_template` source resolution. Remote best/ensemble task-id runs may still be blocked or pending. |

## Experimental Evidence

These records can support future promotion decisions, but they do not by
themselves make a feature supported:

- ClearML stage-based training and optimization dry-runs without matching
  remote dev-server runs.
- `verification/_historical/optimization/optimization_pipeline.md`, which
  records future / experimental optimization evidence only.
- Experimental optional-dependency models `lightgbm`, `xgboost`, and
  `catboost`.
- Historical KNN / SVR / MLP evidence is out of current product scope.
- Historical ensemble and optimization task evidence that predates the current
  stage-based graph.

## Historical Compatibility Evidence

The following areas were moved under `verification/_historical/` because they
primarily prove legacy simple full-run compatibility or old release gates:

- `verification/_historical/v1/clearml_pipelines/*`
- `verification/_historical/v1/summary.md`
- `verification/_historical/v1_3/*`
- `verification/_historical/clearml_ui/*`
- `verification/_historical/full_run/*`
- `verification/_historical/full_run_rerun/*`
- `verification/_historical/clearml_dev/*`
- `verification/_historical/v2_0/pipeline/*`
- `verification/_historical/v2_1/*`
- `verification/_historical/v2_2/*`
- `verification/_historical/v2/ui/*`
- `verification/_historical/v2_3/*`
- `verification/_historical/v2_remote/*`

Old `train -> eval -> infer` records prove compatibility behavior only. They do
not prove the current official training pipeline, which is:

```text
preprocess_features -> train_<model>* -> build_ensemble optional -> evaluate_models
```

## Deprecated Readiness Gates

Treat these as historical unless a newer file explicitly references them:

- `tabular_pipeline_template` as an official training pipeline.
- `Run/pipeline_mode` as an official training pipeline mode.
- Old V2.3 and V2 remote "ready" decisions for fixed `train -> eval -> infer`
  graphs.

Do not delete verification files without human review. Do not store raw logs,
secrets, private Dataset IDs, private artifact URLs, or screenshots unless they
are explicitly sanitized.
