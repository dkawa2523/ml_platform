# Add A Feature Or Metric

## Feature Processing

Start with:

- `features.py` for transformer behavior.
- `training/preprocessing.py` for training artifacts and feature summaries.
- `inference/schema.py` for inference-time schema compatibility.

Keep any learned training-time state in the saved transformer or feature spec.
Inference must not infer a new feature schema from the input file.

## Metrics

Start with:

- `metrics.py` for metric calculation.
- `training/ranking.py` for sort direction and selectors.
- `training/evaluation.py` for evaluation orchestration and result assembly.
- `training/leaderboard_artifacts.py`, `training/prediction_artifacts.py`,
  `training/best_model_artifacts.py`, and `training/decision_artifacts.py` for
  user-facing evaluation artifacts.
- `clearml/reports.py` only when ClearML display behavior changes.

If a new metric can be used as `selection_metric`, define whether lower or
higher is better and cover that direction in tests.

## Checks

Run targeted tests first, then the full suite:

```powershell
uv run python -m pytest tests/test_pipeline_smoke.py tests/test_tabular_characterization.py
uv run python -m pytest
```
