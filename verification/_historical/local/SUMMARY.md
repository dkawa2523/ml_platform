# Local Verification Summary

## Run Metadata

- Date: 2026-05-24 15:50 JST
- Commit: `3773e03`
- Profile: `config/profiles/local.yaml`
- ClearML: not used
- Raw logs: not stored

## Commands

```powershell
.\.venv\Scripts\python.exe scripts\make_sample_data.py
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_train.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_eval.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_infer.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_pipeline.yaml --profile config\profiles\local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\pytest.exe -q
```

All commands exited with code 0.

## Run Outputs

| Task | Run directory | Main artifacts |
| --- | --- | --- |
| train | `outputs/tabular_train_20260524T065013Z` | `model.joblib`, `model_info.json`, `metrics.json`, `validation_predictions.csv`, `manifest.json`, `config.yaml` |
| eval | `outputs/tabular_eval_20260524T065013Z` | `metrics.json`, `evaluation_predictions.csv`, `manifest.json`, `config.yaml` |
| infer | `outputs/tabular_infer_20260524T065013Z` | `predictions.csv`, `manifest.json`, `config.yaml` |
| pipeline | `outputs/tabular_pipeline_20260524T065014Z` | `pipeline_summary.json`, `metrics.json`, `manifest.json`, `config.yaml` |

Generated `outputs/` are ignored and are not commit evidence.

## Metrics

| Context | MAE | RMSE | R2 |
| --- | ---: | ---: | ---: |
| train | 0.4351933423 | 0.5406374502 | 0.9738583770 |
| eval | 0.4216107571 | 0.5226283885 | 0.9750445797 |
| pipeline train | 0.4351933423 | 0.5406374502 | 0.9738583770 |
| pipeline eval | 0.4216107571 | 0.5226283885 | 0.9750445797 |

## Artifact Checks

- Train model, metrics, manifest, config, model info, and validation predictions exist.
- Eval metrics, manifest, config, and evaluation predictions exist.
- Infer predictions, manifest, and config exist.
- Pipeline summary, aggregate metrics, manifest, and step table references exist.

## Pytest

```text
18 passed in 0.43s
```

## Boundary Checks

- Local execution does not require ClearML.
- `pkgs` remains ClearML-free.
- `outputs/` remains ignored.

## Decision

Local verification passed. The current repo state is suitable for ClearML dev verification and v1 MVP review.
