# Local Full Run: ridge

## Inputs

- Model: `ridge`
- Params: `{"alpha": 1.0}`
- Data: `data/sample_train.csv`, `data/sample_infer.csv`
- Profile: `config/profiles/local.yaml`

## Commands

```powershell
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_train.yaml --profile config\profiles\local.yaml --set "model.name=ridge" --set "model.params={alpha: 1.0}"
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_eval.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_infer.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_pipeline.yaml --profile config\profiles\local.yaml --set "model.name=ridge" --set "model.params={alpha: 1.0}"
```

## Result

| Task | Status | Run directory |
| --- | --- | --- |
| train | succeeded | `outputs/tabular_train_20260524T132347Z` |
| eval | succeeded | `outputs/tabular_eval_20260524T132347Z` |
| infer | succeeded | `outputs/tabular_infer_20260524T132347Z` |
| pipeline | succeeded | `outputs/tabular_pipeline_20260524T132348Z` |

## Metrics

| Context | MAE | RMSE | R2 |
| --- | ---: | ---: | ---: |
| train | 0.4351933423 | 0.5406374502 | 0.9738583770 |
| eval | 0.4216107571 | 0.5226283885 | 0.9750445797 |
| pipeline train | 0.4351933423 | 0.5406374502 | 0.9738583770 |
| pipeline eval | 0.4216107571 | 0.5226283885 | 0.9750445797 |

## Artifacts

- Train: `model.joblib`, `model_info.json`, `metrics.json`, `manifest.json`, `validation_predictions.csv`, `config.yaml`
- Eval: `metrics.json`, `manifest.json`, `evaluation_predictions.csv`, `config.yaml`
- Infer: `predictions.csv`, `manifest.json`, `config.yaml`
- Pipeline: `pipeline_summary.json`, `metrics.json`, `manifest.json`, step prediction tables, model artifact

## Review

Accepted for V1 official support. Feature columns and target column were resolved from task config; eval/infer used the latest train model artifact as intended.
