# V2.2 Local Inference Verification

Date: 2026-05-28 JST

## Commands

```powershell
.\.venv\Scripts\python.exe scripts/make_sample_data.py

.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_train.yaml --profile config/profiles/local.yaml
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml --set output.chunk_size=10

.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_train.yaml --profile config/profiles/local.yaml --set "model.candidates=[linear, ridge]" --set "model.params={ridge: {alpha: 1.0}}"
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml

.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_train.yaml --profile config/profiles/local.yaml --set "model.candidates=[linear, ridge]" --set "model.params={ridge: {alpha: 1.0}}" --set "model.ensemble.enabled=true" --set "model.ensemble.method=weighted" --set "model.ensemble.top_k=2"
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml --set output.chunk_size=7

$space='{alpha: [0.1, 1.0, 10.0]}'
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_train.yaml --profile config/profiles/local.yaml --set "model.params={}" --set "model.search.enabled=true" --set "model.search.method=grid" --set "model.search.max_trials=3" --set "model.search.search_space=$space"
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml --set output.chunk_size=9

.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\pytest.exe -q
```

## Results

| Check | Status | Notes |
| --- | --- | --- |
| Single model infer | pass | `predictions.csv` includes V2.2 metadata columns. |
| Best comparison model infer | pass | Best artifact from comparison train was consumed by the same infer task. |
| Weighted ensemble infer | pass | Ensemble artifact was consumed by the same infer task. |
| Optimized model infer | pass | Grid-search best model artifact was consumed by the same infer task. |
| Chunked infer | pass | `output.chunk_size` produced the same `predictions` table contract. |
| Local pipeline smoke | pass | Pipeline still writes infer predictions. |
| Pytest | pass | 41 passed. |

## Prediction Schema

`predictions.csv` preserves the input columns and appends:

- `prediction`
- `model_name`
- `artifact_kind`
- `model_artifact_id`
- `prediction_run_id`

The infer manifest includes `prediction_schema_version=v2.2`, row count, model metadata, selected feature columns, id columns, target column, and `chunk_size`.

## Readiness

V2.2 local inference status: ready.
