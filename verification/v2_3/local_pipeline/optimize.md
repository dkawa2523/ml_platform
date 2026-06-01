# V2.3 Local Pipeline: optimize

Date: 2026-06-01

## Command

```powershell
python scripts/make_sample_data.py
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set runtime.output_dir=outputs/v2_3_local_pipeline/optimize --set run.pipeline_mode=optimize --set "model.search.search_space={alpha: [0.1, 1.0]}" --set model.selection_metric=rmse
```

## Result

- status: passed
- pipeline_mode: `optimize`
- run_dir: `outputs\v2_3_local_pipeline\optimize\tabular_pipeline_20260601T062930Z`
- graph: train -> eval -> infer
- artifact handoff: eval and infer used the optimized train `model` artifact

## Artifacts

- `model`
- `train_model_info`
- `train_optimization_trials`
- `train_optimization_summary`
- `train_best_params`
- `eval_evaluation_predictions`
- `infer_predictions`
- `summary`
- `metrics`
- `manifest`

## Notes

- `optimization_trials.csv` and `best_params.json` are produced by the train step.
- Search and ensemble are intentionally not combined in V2.3.
