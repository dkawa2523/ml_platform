# Verification Index

This directory keeps current evidence and historical evidence. Current release
readiness should be judged only from the current sections below.

## Current Evidence

| area | evidence |
| --- | --- |
| Training pipeline | `verification/training_pipeline/local_training_pipeline.md` |
| Training release gate | `verification/training_pipeline/release_gate.md` |
| ClearML dry-run | `verification/training_pipeline/clearml_training_pipeline.md` |
| Inference | `verification/inference/infer_task_reference.md` |
| Model policy | `verification/product_ux/model_policy.md` |
| ClearML project layout | `verification/product_ux/clearml_project_layout.md` |
| Pipeline inputs | `verification/product_ux/pipeline_inputs.md` |
| Results and plots | `verification/product_ux/results_and_plots.md` |
| ClearML plot reporting | `verification/product_ux/clearml_plots.md` |

Remote ClearML browser evidence for the latest Agent image and templates is
still the final release gate when it is requested.

## Historical Evidence

Historical records live under `verification/_historical/**`. Keep them for
traceability, but do not use them as current product readiness evidence.

Do not store secrets, private Dataset IDs, private artifact URLs, or unsanitized
screenshots in verification files.
