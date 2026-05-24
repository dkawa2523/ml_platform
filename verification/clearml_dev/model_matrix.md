# ClearML Dev Model Matrix

## Run Metadata

- Date: 2026-05-24
- Commit: `3773e03`
- Environment: local `.venv` plus ClearML dev Agent
- `clearml` installed: yes
- `sklearn` installed: no

## Decision

| Model | Execute | Result | Required dependency | Model params | Tasks |
| --- | --- | --- | --- | --- | --- |
| `ridge` | yes | train/eval/infer/pipeline completed | `numpy` | `{"alpha": 1.0}` | train, eval, infer, pipeline |
| `linear` | yes | train/eval/infer/pipeline completed | `numpy` | `{}` | train, eval, infer, pipeline |
| `random_forest` | no | skipped | `scikit-learn` | not used | skipped |
| `gradient_boosting` | no | skipped | `scikit-learn` | not used | skipped |

## Notes

- No optional dependency was installed just to expand this matrix.
- No model-specific template or task config was added.
- Model switching was verified by changing `Model/name` and `Model/params` on existing templates.
