# V2.3 Local Pipeline: ensemble

Date: 2026-06-01

## Command

```powershell
python scripts/make_sample_data.py
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set runtime.output_dir=outputs/v2_3_local_pipeline/ensemble --set run.pipeline_mode=ensemble --set "model.candidates=[linear, ridge, random_forest]" --set model.selection_metric=rmse --set model.ensemble.method=mean_topk --set model.ensemble.top_k=2
```

## Result

- status: passed
- pipeline_mode: `ensemble`
- artifact_kind: `ensemble`
- run_dir: `outputs\v2_3_local_pipeline\ensemble\tabular_pipeline_20260601T062930Z`
- graph: train -> eval -> infer
- artifact handoff: eval and infer used the train step ensemble `model` artifact

## Artifacts

- `model`
- `train_model_info`
- `train_ensemble_info`
- `train_ensemble_predictions`
- `train_leaderboard`
- `train_base_model_1_linear`
- `train_base_model_2_ridge`
- `eval_evaluation_predictions`
- `infer_predictions`
- `summary`
- `metrics`
- `manifest`

## Notes

- `ensemble_info.json` is produced by the train step.
- No separate ensemble pipeline node or `train_ensemble_full` flow is created.
