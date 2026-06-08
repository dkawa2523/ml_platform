# ClearML Rerun And User Review

> Historical note: this file records an old full-run compatibility rerun and its
> fixed `train -> eval -> infer` graph. It is not current product readiness
> evidence for the official stage-based training pipeline.

## Run Metadata

- Date: 2026-05-24
- Purpose: resolve queue wait concern, rerun required models, and review ClearML usability
- Scope: dev ClearML server and dev `default` queue only
- Required models: `ridge`, `linear`
- Dataset: existing Agent-reachable dev Dataset
- Raw logs: not stored
- Screenshots: not stored
- Secrets: not stored

## Agent / Queue Check

- Running Agent containers observed:
  - `clearml-default`
  - `clearml-controller`
  - `clearml-heavy-model`
- This gives more than the two worker slots required when a remote pipeline controller and its step tasks share the same queue.
- No ClearML task was deleted, archived, aborted, reset, or cleaned up.
- Existing completed tasks were left as evidence; rerun tasks were created with `rerun_*` names.

## Template Check

Dry-run and real sync passed with the same four templates:

- `tabular_train_template`
- `tabular_eval_template`
- `tabular_infer_template`
- `tabular_pipeline_template`

The UI parameter groups stayed limited to:

- `Input`
- `Run`
- `Model`
- `Output`

Pipeline dry-run still shows the historical compatibility fixed DAG:

```text
train -> eval -> infer
```

Eval and infer receive the train `model` artifact URL through `Model/artifact_path`.

## ClearML Task Rerun Matrix

| Model | Task | Task ID | Status | Worker | Elapsed observed by operator | Metrics / artifacts |
| --- | --- | --- | --- | --- | --- | --- |
| `ridge` | train | `08a2babc08994d6b9048e439362847c8` | completed | `a8415e1b0aea:2` | about 30s | MAE `0.4351933300`, RMSE `0.5406374335`, R2 `0.9738583565`; model and validation predictions present |
| `ridge` | eval | `9b0251d935d34b7bb61963db8dde79a4` | completed | `a8415e1b0aea:1` | about 20s | MAE `0.4216107428`, RMSE `0.5226283669`, R2 `0.9750446081`; evaluation predictions present |
| `ridge` | infer | `d0e2fe67d62e40bd8bffa6087f612d85` | completed | `a8415e1b0aea:3` | about 20s | predictions present |
| `linear` | train | `ff682a14b4b34e22879049074c859f85` | completed | `a8415e1b0aea:2` | about 20s | MAE `0.4354112148`, RMSE `0.5402973294`, R2 `0.9738912582`; model and validation predictions present |
| `linear` | eval | `b816c73fc52342b9844990698c43fd21` | completed | `a8415e1b0aea:1` | about 20s | MAE `0.4219971597`, RMSE `0.5218273997`, R2 `0.9751210213`; evaluation predictions present |
| `linear` | infer | `5552bd0ba534430bb99bd1223259984c` | completed | `a8415e1b0aea:3` | about 20s | predictions present |

## ClearML Pipeline Rerun Matrix

| Model | Pipeline ID | Status | Pipeline URL | Result |
| --- | --- | --- | --- | --- |
| `ridge` | `b18282584c0f468591d0fbedb1d7e4ad` | completed | `http://localhost:8080/pipelines/57d192f3bb8746acae1a10961ee597ae/experiments/b18282584c0f468591d0fbedb1d7e4ad` | train, eval, infer steps completed |
| `linear` | `24bfeda182dd40a38d732a074c35f01b` | completed | `http://localhost:8080/pipelines/57d192f3bb8746acae1a10961ee597ae/experiments/24bfeda182dd40a38d732a074c35f01b` | train, eval, infer steps completed |

### Ridge Pipeline Steps

| Step | Task ID | Status | Metrics / artifacts |
| --- | --- | --- | --- |
| `train` | `244a4f2d458c4c558946aba9e7a7e739` | completed | MAE `0.4351933300`, RMSE `0.5406374335`, R2 `0.9738583565`; model artifact present |
| `eval` | `cf12ca4db8714707bf498c523f388938` | completed | MAE `0.4216107428`, RMSE `0.5226283669`, R2 `0.9750446081`; model artifact URL received |
| `infer` | `78052c27e677467787e66d64c15f434e` | completed | predictions present; model artifact URL received |

### Linear Pipeline Steps

| Step | Task ID | Status | Metrics / artifacts |
| --- | --- | --- | --- |
| `train` | `fc16f98349a348c6b25afc6c20d48142` | completed | MAE `0.4354112148`, RMSE `0.5402973294`, R2 `0.9738912582`; model artifact present |
| `eval` | `a194d27a78cc4688835638eb6f94a905` | completed | MAE `0.4219971597`, RMSE `0.5218273997`, R2 `0.9751210213`; model artifact URL received |
| `infer` | `d11fd99f56b44da2bc91116988e0986a` | completed | predictions present; model artifact URL received |

## Local Regression Check

The local acceptance path was rerun after ClearML execution:

```powershell
.\.venv\Scripts\python.exe scripts\make_sample_data.py
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_train.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_eval.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_infer.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_pipeline.yaml --profile config\profiles\local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\pytest.exe -q
```

Result:

```text
18 passed in 0.40s
```

## ClearML UI Availability

- `http://localhost:8080` returned HTTP 200 from this workspace.
- Direct browser interaction or screenshot capture from Codex was not available.
- UI-facing evidence was reviewed through task URLs and ClearML SDK metadata.
- Sanitized screenshots can be added manually later, but are not required for this gate.

## User View Review

### Sufficient Points

- A user sees only four templates, which is appropriately small.
- Model switching is done by editing `Model/name` and `Model/params`; no model-specific templates are needed.
- Dataset selection is clear for Agent runs: use `Input/clearml_dataset_id`, plus `Input/dataset_file` when needed.
- `Input/local_path` remains available but docs now warn that it must exist inside the Agent container or PVC.
- Metrics are visible for train and eval.
- Artifacts are named plainly and are enough for v1: model, model_info, metrics, manifest, validation/evaluation predictions, predictions.
- Pipeline graph is the expected three-step flow.
- Step artifact handoff is traceable from the train model artifact URL to eval and infer.
- Console logs remain the right place to inspect failures, while raw logs are not saved in repo.

### Remaining Friction

- A visual UI review still depends on a human opening ClearML and optionally saving sanitized screenshots.
- `localhost:8080` URLs are dev-local evidence; they are not portable release URLs.
- Pipeline runs still rely on at least two worker slots when controller and steps share a queue.

### User-Facing Decision

Sufficient for v1. The rerun confirms the previous bottleneck was operational capacity, not product code behavior.

## Final Decision

v1 remains ready. No code change was required.
