# ClearML Dev Full Verification Summary

## Run Metadata

- Date: 2026-05-24 15:47 JST
- Code commit verified by Agent: `3773e03`
- Profile: `config/profiles/clearml-dev.yaml`
- Dev project root: `MLPlatform/Dev`
- Pipeline project: `MLPlatform/Dev/Pipelines`
- Dev queue: `default`
- Repository: `https://github.com/dkawa2523/ml_platform.git`
- Branch: `main`
- Working directory: `.`
- Raw logs: not stored
- Secrets: not stored

## Commands Executed

```powershell
git status --short
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\pytest.exe -q
.\.venv\Scripts\python.exe clearml\pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
rg -n "from clearml|import clearml|PipelineController|StorageManager" pkgs
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml
```

ClearML task and pipeline execution was performed through the ClearML SDK by cloning the dev templates, setting UI parameters, and enqueueing on the `default` dev queue.

## Preflight Result

- Local smoke had already passed before ClearML execution.
- Pytest after the pipeline parameter fix: `18 passed`.
- `pkgs` ClearML import boundary: no matches.
- Product repo dirty state after verification: untracked `verification/` only.

## Template URLs

| Template | Task ID | URL |
| --- | --- | --- |
| `tabular_train_template` | `c2ef58062a5347c9b8f3e7ed13945be9` | `http://localhost:8080/projects/739356ee8e354bb48283539ced2a99eb/experiments/c2ef58062a5347c9b8f3e7ed13945be9/output/log` |
| `tabular_eval_template` | `641a810049c84a6dbeafefb2ae513bcb` | `http://localhost:8080/projects/739356ee8e354bb48283539ced2a99eb/experiments/641a810049c84a6dbeafefb2ae513bcb/output/log` |
| `tabular_infer_template` | `a6c147c9768b4c0f9de5cef470ad8257` | `http://localhost:8080/projects/739356ee8e354bb48283539ced2a99eb/experiments/a6c147c9768b4c0f9de5cef470ad8257/output/log` |
| `tabular_pipeline_template` | `d8d4fe66b7f8499bbe69178a09eaece2` | `http://localhost:8080/projects/739356ee8e354bb48283539ced2a99eb/experiments/d8d4fe66b7f8499bbe69178a09eaece2/output/log` |

## Successful Task Runs

| Model | Task | Task ID | Status |
| --- | --- | --- | --- |
| `ridge` | train | `4fe2add8d23a472fba4523eb8ae22c5b` | completed |
| `ridge` | eval | `1a29f200df3245a092b4382b1324cb9a` | completed |
| `ridge` | infer | `c4c96f962a804b86986c452b1f8385ed` | completed |
| `linear` | train | `de2549c0d3d343f1871b8dcb2b0dafc2` | completed |
| `linear` | eval | `c4910436f6124f58bd2a8573b012ca22` | completed |
| `linear` | infer | `127d36461dfa41ab81a29b0624f7809b` | completed |

## Successful Pipeline Runs

| Model | Pipeline task ID | Status | Step tasks |
| --- | --- | --- | --- |
| `ridge` | `f299a5603b994553b1823a6da3600200` | completed | train `9c70d09592ae4985b8a4116e28a23198`, eval `c374e088276a4b299a2e17c78786fb5a`, infer `6cf6e646c7de457c8a33caaff812f725` |
| `linear` | `29df0b860fd04e37a5c796858cb434c9` | completed | train `2a62fc0c97954f9685f8633707cd2b96`, eval `d204b47e9ff94638a7a6866d665f2ae3`, infer `a36d1c83f5ee415cb0d316bf7d636c26` |

## Metrics Summary

| Model | Context | MAE | RMSE | R2 |
| --- | --- | ---: | ---: | ---: |
| `ridge` | task train | 0.4351933423 | 0.5406374502 | 0.9738583770 |
| `ridge` | task eval | 0.4216107571 | 0.5226283885 | 0.9750445797 |
| `ridge` | pipeline train | 0.4351933300 | 0.5406374335 | 0.9738583565 |
| `ridge` | pipeline eval | 0.4216107428 | 0.5226283669 | 0.9750446081 |
| `linear` | task train | 0.4354112291 | 0.5402973080 | 0.9738912607 |
| `linear` | task eval | 0.4219971587 | 0.5218273825 | 0.9751210169 |
| `linear` | pipeline train | 0.4354112148 | 0.5402973294 | 0.9738912582 |
| `linear` | pipeline eval | 0.4219971597 | 0.5218273997 | 0.9751210213 |

## Issues Found And Fixed

- The first pipeline controller occupied the only dev worker, leaving its step queued. For dev verification, two additional `default` workers were started in the existing Agent container. No task was deleted, aborted, archived, or reset.
- Pipeline step dataset parameters were not applied because `Task.current_task()` was read before `PipelineController` initialized the controller task. Fixed in `clearml/pipelines.py` and pushed as `3773e03`.
- A Docker-network ClearML Dataset was required because a host-created dataset used `localhost` file URLs that were not reachable from the Agent container.

## Product Review

ClearML dev verification is v1-acceptable for the MVP scope:

- train/eval/infer templates work for `ridge` and `linear`.
- pipeline template runs fixed `train -> eval -> infer`.
- eval and infer receive the train model through a ClearML artifact URL.
- metrics and artifacts are visible from task metadata.
- `pkgs` remain ClearML-free.

## Remaining Risks

- The dev Agent image used during verification is an old local image. The repo deploy image should be built and tested separately before production.
- The dev queue needs at least two workers for remote pipeline execution, or a separate controller queue and step queue design must be documented.
- ClearML UI screenshots were not captured by Codex. URLs and SDK metadata are the primary evidence.

## Commit Guidance

Commit candidates:

- sanitized verification markdown under `verification/`

Do not commit:

- raw logs
- screenshots containing secrets
- `outputs/`
- `.venv/`
- credentials or ClearML config

Suggested commit message:

`Record ClearML dev verification`
