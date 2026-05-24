# Local Full Run: linear

## Inputs

- Model: `linear`
- Params: `{}`
- Data: `data/sample_train.csv`, `data/sample_infer.csv`
- Profile: `config/profiles/local.yaml`

## Commands

```powershell
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_train.yaml --profile config\profiles\local.yaml --set "model.name=linear" --set "model.params={}"
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_eval.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_infer.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_pipeline.yaml --profile config\profiles\local.yaml --set "model.name=linear" --set "model.params={}"
```

## Result

| Task | Status | Run directory |
| --- | --- | --- |
| train | succeeded | `outputs/tabular_train_20260524T132345Z` |
| eval | succeeded | `outputs/tabular_eval_20260524T132346Z` |
| infer | succeeded | `outputs/tabular_infer_20260524T132346Z` |
| pipeline | succeeded | `outputs/tabular_pipeline_20260524T132346Z` |

## Metrics

| Context | MAE | RMSE | R2 |
| --- | ---: | ---: | ---: |
| train | 0.4354112291 | 0.5402973080 | 0.9738912607 |
| eval | 0.4219971587 | 0.5218273825 | 0.9751210169 |
| pipeline train | 0.4354112291 | 0.5402973080 | 0.9738912607 |
| pipeline eval | 0.4219971587 | 0.5218273825 | 0.9751210169 |

## Artifacts

- Train: `model.joblib`, `model_info.json`, `metrics.json`, `manifest.json`, `validation_predictions.csv`, `config.yaml`
- Eval: `metrics.json`, `manifest.json`, `evaluation_predictions.csv`, `config.yaml`
- Infer: `predictions.csv`, `manifest.json`, `config.yaml`
- Pipeline: `pipeline_summary.json`, `metrics.json`, `manifest.json`, step prediction tables, model artifact

## Review

Accepted for V1 official support. Linear uses the same local execution path as the other V1 models.
