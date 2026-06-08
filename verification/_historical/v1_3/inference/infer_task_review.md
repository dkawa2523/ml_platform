# V1.3 inference verification

Run date: 2026-05-25
Git commit: 0756d3b

## Scope

V1.3 standardizes batch inference output for:

- single model artifacts
- comparison best-model artifacts
- `mean_topk` ensemble artifacts
- `weighted` ensemble artifacts

No serving API, optimization, chunked reader, required parquet output, or new
ClearML template was added.

## Local checks

Commands:

```powershell
.\.venv\Scripts\python.exe scripts/make_sample_data.py
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_train.yaml --profile config/profiles/local.yaml
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_eval.yaml --profile config/profiles/local.yaml
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
.\.venv\Scripts\python.exe scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\pytest.exe -q
```

Results:

- `make_sample_data`: passed
- local train: passed
- local eval: passed
- local infer: passed
- local pipeline: passed
- pytest: 32 passed

Note: local wrapper tasks that share `outputs/latest` should be run
sequentially on Windows. Parallel verification can hit file locks while one task
updates `latest` and another reads or updates it.

## Output schema

`predictions.csv` preserves the input columns and appends:

- `prediction`
- `model_name`
- `artifact_kind`
- `prediction_run_id`

Observed sample from local pipeline infer:

```text
id,x1,x2,category,prediction,model_name,artifact_kind,prediction_run_id
```

The inference manifest records:

- prediction row count
- prediction file name
- model source path
- model name
- artifact kind
- feature columns

Inference input tables now reject reserved output columns:

- `prediction`
- `model_name`
- `artifact_kind`
- `prediction_run_id`

## Artifact behavior

ClearML reporting remains generic. The infer result exposes:

- table artifact key: `predictions`
- file name: `output.prediction_name` / `Output/prediction_name`
- optional artifact: `model_info`
- manifest artifact: `manifest`

Because best models and ensembles are saved as `model.joblib` with `.predict(X)`,
infer does not need model-specific or ensemble-specific code.

## ClearML compatibility

Command:

```powershell
.\.venv\Scripts\python.exe scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
```

Result:

- four templates only
- `tabular_infer_template` remains the only inference template
- `Output/prediction_name` remains available
- no new ClearML UI group was added

## Readiness

V1.3 inference is ready for batch table inference. V2 remains the right place
for online single-row APIs, streaming/chunked readers, optimization workflows,
and required parquet outputs.
