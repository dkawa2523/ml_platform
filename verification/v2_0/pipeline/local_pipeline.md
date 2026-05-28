# V2.0 Local Pipeline Verification

Date: 2026-05-26 JST

Git commit at verification time: working tree with V2.0 pipeline productization changes.

## Commands

```powershell
.\.venv\Scripts\python.exe scripts/make_sample_data.py
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml

$candidates='[{name: linear, params: {}}, {name: ridge, params: {alpha: 1.0}}, {name: random_forest, params: {n_estimators: 20, random_state: 42, n_jobs: 1}}, {name: gradient_boosting, params: {n_estimators: 20, random_state: 42}}]'
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set "model.candidates=$candidates" --set "model.params={}" --set "model.selection_metric=rmse" --set "model.ensemble.enabled=false"
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set "model.candidates=$candidates" --set "model.params={}" --set "model.selection_metric=rmse" --set "model.ensemble.enabled=true" --set "model.ensemble.method=mean_topk" --set "model.ensemble.top_k=3"
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set "model.candidates=$candidates" --set "model.params={}" --set "model.selection_metric=rmse" --set "model.ensemble.enabled=true" --set "model.ensemble.method=weighted" --set "model.ensemble.top_k=3"
```

## Results

| Mode | Status | Pipeline mode | Model | Artifact kind | Key artifacts/tables |
| --- | --- | --- | --- | --- | --- |
| Single model | pass | `single_model` | `ridge` | `model` | `model`, `train_model_info`, `eval_evaluation_predictions`, `infer_predictions` |
| Comparison / best model | pass | `comparison_best_model` | `linear` | `model` | `model`, `train_model_info`, `train_leaderboard`, `eval_evaluation_predictions`, `infer_predictions` |
| mean_topk ensemble | pass | `mean_topk_ensemble` | `mean_topk` | `ensemble` | `model`, `train_model_info`, `train_leaderboard`, `train_ensemble_predictions`, `train_base_model_*`, `eval_evaluation_predictions`, `infer_predictions` |
| weighted ensemble | pass | `weighted_ensemble` | `weighted` | `ensemble` | `model`, `train_model_info`, `train_leaderboard`, `train_ensemble_predictions`, `train_base_model_*`, `eval_evaluation_predictions`, `infer_predictions` |

## Summary Artifact

`pipeline_summary.json` now records:

- `pipeline_mode`
- `model_name`
- `produced_model_name`
- `artifact_kind`
- `selection_metric`
- child run directories
- standard model artifact
- `model_info`
- `leaderboard` when comparison mode is used
- `ensemble_predictions` when ensemble mode is used
- `evaluation_predictions`
- `predictions`
- artifact/table path maps

`manifest.json` now repeats the key train/eval/infer artifacts and tables so a local user can inspect the pipeline result from the pipeline run directory.

## Notes

Local runs that update `outputs/latest*` should be executed sequentially. A parallel local shell run can race on Windows while updating the ignored `outputs/latest` directories; this is not part of the product pipeline contract.

V2.0 local pipeline status: ready.
