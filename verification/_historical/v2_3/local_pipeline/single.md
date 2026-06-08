# V2.3 Local Pipeline: single

Date: 2026-06-01

## Command

```powershell
python scripts/make_sample_data.py
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set runtime.output_dir=outputs/v2_3_local_pipeline/single --set run.pipeline_mode=single
```

## Result

- status: passed
- pipeline_mode: `single`
- run_dir: `outputs\v2_3_local_pipeline\single\tabular_pipeline_20260601T062930Z`
- graph: train -> eval -> infer
- artifact handoff: eval and infer used the train step `model` artifact

## Artifacts

- `model`
- `train_model_info`
- `eval_evaluation_predictions`
- `infer_predictions`
- `summary`
- `metrics`
- `manifest`

## Notes

- No `leaderboard`, `ensemble_info`, or optimization artifacts are expected for single mode.
