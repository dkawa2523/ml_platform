# Verification Scope Index

This directory contains both current product evidence and older compatibility
evidence. Historical records are preserved, but they are not the readiness gate
for the current stage-based training, inference, or optimization specifications.

## Current Product Evidence

| area | evidence | status |
| --- | --- | --- |
| Release gate | `verification/training_pipeline/release_gate.md` | Current gate. Local/dry-run pass; remote ClearML execution blocked until commit/push. |
| Local training pipeline | `verification/training_pipeline/local_training_pipeline.md` | Current local pass for `preprocess_features -> train_<model>* -> build_ensemble optional -> evaluate_models`. |
| ClearML training pipeline | `verification/training_pipeline/clearml_training_pipeline.md` | Dry-run pass. Remote ClearML run is still required before support promotion. |
| Inference task | `verification/inference/infer_task_reference.md` | Current evidence for `tabular_infer_template` source resolution. Remote best/ensemble task-id runs may still be blocked or pending. |
| Optimization pipeline | `verification/optimization/optimization_pipeline.md` | Current local and ClearML dry-run pass for `preprocess_features -> search_trials -> retrain_best -> evaluate_best`. Remote ClearML run is still required before support promotion. |

## Experimental Evidence

These records can support future promotion decisions, but they do not by
themselves make a feature supported:

- ClearML stage-based training and optimization dry-runs without matching
  remote dev-server runs.
- Implemented but not fully remote-verified sklearn models such as `lasso`,
  `elasticnet`, `extra_trees`, `knn`, `svr`, and `mlp`.
- Historical ensemble and optimization task evidence that predates the current
  stage-based graph.

## Historical Compatibility Evidence

The following areas primarily prove legacy simple full-run compatibility or old
release gates:

- `verification/v1/clearml_pipelines/*`
- `verification/v1/summary.md`
- `verification/v1_3/*`
- `verification/clearml_ui/*`
- `verification/full_run/*`
- `verification/full_run_rerun/*`
- `verification/clearml_dev/*`
- `verification/v2_0/pipeline/*`
- `verification/v2_1/*`
- `verification/v2_2/*`
- `verification/v2/ui/*`
- `verification/v2_3/*`
- `verification/v2_remote/*`

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
