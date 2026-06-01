# V2.3 Local Pipeline: compare

Date: 2026-06-01

## Command

```powershell
python scripts/make_sample_data.py
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set runtime.output_dir=outputs/v2_3_local_pipeline/compare --set run.pipeline_mode=compare --set "model.candidates=[linear, ridge, random_forest]" --set model.selection_metric=rmse
```

## Result

- status: passed
- pipeline_mode: `compare`
- run_dir: `outputs\v2_3_local_pipeline\compare\tabular_pipeline_20260601T062930Z`
- graph: train -> eval -> infer
- artifact handoff: eval and infer used the selected best train `model` artifact

## Artifacts

- `model`
- `train_model_info`
- `train_leaderboard`
- `eval_evaluation_predictions`
- `infer_predictions`
- `summary`
- `metrics`
- `manifest`

## Notes

- `leaderboard.csv` is produced by the train step.
- No separate leaderboard pipeline node is created.
