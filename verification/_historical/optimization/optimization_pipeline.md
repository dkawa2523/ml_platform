# Phase E Optimization Pipeline Verification

> Future / experimental evidence: optimization is not primary product scope and
> this file is not a current release gate. Keep it as implementation evidence
> until `docs/SPEC.md` promotes optimization.

Date: 2026-06-04

## Scope

Verify stage-based optimization as a pipeline shape, not a train-internal-only
option.

Expected graph:

```text
preprocess_features -> search_trials -> retrain_best -> evaluate_best
```

No optimize-specific template, no per-trial ClearML child task, and no ClearML
import under `pkgs`.

## Local Commands

```powershell
.\.venv\Scripts\python.exe scripts\make_sample_data.py
.\.venv\Scripts\python.exe scripts\local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set model.ensemble.enabled=false --set 'model.candidates=[]' --set model.name=ridge --set 'model.params={}' --set model.search.enabled=true --set model.search.method=grid --set model.search.max_trials=2 --set 'model.search.search_space={"alpha":[0.1,1.0]}'
```

Result: pass.

The default local command remains the training+ensemble graph. The override run
produced `pipeline_kind=optimization` and stages:

```text
preprocess_features
search_trials
retrain_best
evaluate_best
```

## Local Artifacts

Observed optimization artifacts:

- `search_trials/optimization_trials.csv`
- `search_trials/optimization_summary.json`
- `search_trials/best_params.json`
- `retrain_best/model.joblib`
- `retrain_best/model_info.json`
- `evaluate_best/best_model.joblib`
- `evaluate_best/best_model.json`
- `evaluate_best/evaluation_report.json`
- root `metrics.json`
- root `manifest.json`

`evaluate_best` metrics use the selected validation trial metrics and mark
`metric_source=search_trials_validation`. The retrained artifact is the
deployable best model.

## ClearML Dry Run

```powershell
.\.venv\Scripts\python.exe clearml\pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run --set model.ensemble.enabled=false --set 'model.candidates=[]' --set model.name=ridge --set 'model.params={}' --set model.search.enabled=true --set model.search.method=grid --set model.search.max_trials=2 --set 'model.search.search_space={"alpha":[0.1,1.0]}'
```

Result: pass.

Dry-run graph:

```text
preprocess_features
  -> search_trials
  -> retrain_best
  -> evaluate_best
```

All steps use `tabular_stage_template`.

## Test Commands

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
git diff --check
rg -n "from clearml|import clearml|PipelineController|StorageManager" pkgs/core pkgs/tabular
```

Results:

- pytest: pass, 57 passed
- template sync dry-run: pass
- `git diff --check`: pass, line-ending warnings only
- ClearML import boundary search: pass, no matches

## Remote Status

ClearML remote optimization pipeline execution was not run in this pass. Product
promotion requires a dev-server run that confirms:

- Pipeline graph is visible as `preprocess_features -> search_trials -> retrain_best -> evaluate_best`
- `search_trials` artifacts include `optimization_trials`, `optimization_summary`, and `best_params`
- `retrain_best` publishes the deployable `model`
- `evaluate_best` publishes `best_model`, `evaluation_report`, `metrics`, and `manifest`

Remote status: blocked/not executed, not product pass.
