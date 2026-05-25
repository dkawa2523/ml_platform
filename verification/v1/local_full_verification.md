# V1 Local Full Verification

## Run Metadata

- Date: 2026-05-24 23:25:09 +09:00
- Git commit: `0756d3b`
- Git status before run: clean tracked tree; ignored artifacts only
- Scope: local train/eval/infer/pipeline for V1 official supported models plus comparison mode
- Raw logs: not stored
- Outputs: generated under `outputs/` and not committed

## Commands

```powershell
python scripts/make_sample_data.py

python scripts/local_run.py --task config/tasks/tabular_train.yaml --profile config/profiles/local.yaml --set "model.name=<model>" --set "model.params=<params>"
python scripts/local_run.py --task config/tasks/tabular_eval.yaml --profile config/profiles/local.yaml
python scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set "model.name=<model>" --set "model.params=<params>"

python scripts/local_run.py --task config/tasks/tabular_train.yaml --profile config/profiles/local.yaml --set "model.candidates=<4 model candidates>" --set "model.selection_metric=rmse"
python scripts/local_run.py --task config/tasks/tabular_eval.yaml --profile config/profiles/local.yaml
python scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set "model.candidates=<4 model candidates>" --set "model.selection_metric=rmse"

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest -q
```

## Single Model Results

| Model | Params | Train | Eval | Infer | Pipeline | Eval RMSE | Eval R2 |
| --- | --- | --- | --- | --- | --- | ---: | ---: |
| `linear` | `{}` | pass | pass | pass | pass | `0.5218273825248825` | `0.975121016854341` |
| `ridge` | `{alpha: 1.0}` | pass | pass | pass | pass | `0.522628388463519` | `0.9750445796690351` |
| `random_forest` | `{n_estimators: 50, random_state: 42, n_jobs: 1}` | pass | pass | pass | pass | `0.6283117085198283` | `0.9639314069203292` |
| `gradient_boosting` | `{n_estimators: 50, random_state: 42}` | pass | pass | pass | pass | `0.5455435326303649` | `0.9728082148686884` |

## Run Directories

| Model | Train | Eval | Infer | Pipeline |
| --- | --- | --- | --- | --- |
| `linear` | `outputs/tabular_train_20260524T142441Z` | `outputs/tabular_eval_20260524T142441Z` | `outputs/tabular_infer_20260524T142442Z` | `outputs/tabular_pipeline_20260524T142442Z` |
| `ridge` | `outputs/tabular_train_20260524T142442Z` | `outputs/tabular_eval_20260524T142443Z` | `outputs/tabular_infer_20260524T142443Z` | `outputs/tabular_pipeline_20260524T142444Z` |
| `random_forest` | `outputs/tabular_train_20260524T142444Z` | `outputs/tabular_eval_20260524T142445Z` | `outputs/tabular_infer_20260524T142446Z` | `outputs/tabular_pipeline_20260524T142447Z` |
| `gradient_boosting` | `outputs/tabular_train_20260524T142448Z` | `outputs/tabular_eval_20260524T142449Z` | `outputs/tabular_infer_20260524T142450Z` | `outputs/tabular_pipeline_20260524T142452Z` |

## Comparison Mode

- Candidates: `linear`, `ridge`, `random_forest`, `gradient_boosting`
- Selection metric: `rmse`
- Train run: `outputs/tabular_train_20260524T142453Z`
- Eval run using best model: `outputs/tabular_eval_20260524T142454Z`
- Infer run using best model: `outputs/tabular_infer_20260524T142454Z`
- Pipeline run: `outputs/tabular_pipeline_20260524T142455Z`
- Train `leaderboard.csv`: present
- Pipeline train-step `leaderboard.csv`: present
- Best model: `linear`
- Best params: `{}`
- Eval RMSE with best model: `0.5218273825248825`
- Eval R2 with best model: `0.975121016854341`

| Rank | Model | RMSE | R2 | Selected |
| --- | --- | ---: | ---: | --- |
| 1 | `linear` | `0.5402973079870903` | `0.9738912606564274` | yes |
| 2 | `ridge` | `0.5406374501969393` | `0.9738583769845428` | no |
| 3 | `gradient_boosting` | `0.9494244655990696` | `0.9193803083551461` | no |
| 4 | `random_forest` | `1.1137118773680839` | `0.8890656615829372` | no |

## Artifact Checks

| Artifact | Result |
| --- | --- |
| `metrics.json` | present for train/eval/pipeline runs |
| `manifest.json` | present for train/eval/infer/pipeline runs |
| `model_info.json` | present for train runs and stores selected model name/params |
| `validation_predictions.csv` | present for train runs |
| `evaluation_predictions.csv` | present for eval runs |
| `predictions.csv` | present for infer runs |
| `leaderboard.csv` | present for comparison train and comparison pipeline train step |
| best model handoff | eval/infer used the latest comparison train model artifact |

## Pytest

- Command: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q`
- Result: `22 passed in 1.16s`

## Issues And Fixes

- Issues found: none
- Code changes: none
- Test changes: none
- Generated outputs remain under ignored `outputs/`

## Decision

- V1 local ready: yes
- ClearML verification can proceed: yes
