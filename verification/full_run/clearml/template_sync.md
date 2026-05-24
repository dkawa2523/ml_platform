# ClearML Template Sync

## Run Metadata

- Date: 2026-05-24
- Profile: `config/profiles/clearml-dev.yaml`
- Project: `MLPlatform/Dev/Templates`
- Queue: `default`
- Repository: `https://github.com/dkawa2523/ml_platform.git`
- Branch: `main`
- Working directory: `.`
- Verified commit for following runs: `0d4b2eb`
- Raw logs: not stored
- Secrets: not stored

## Command

```powershell
.\.venv\Scripts\python.exe scripts\sync_clearml_templates.py --profile config\profiles\clearml-dev.yaml
```

## Result

| Template | Task ID | URL | Status |
| --- | --- | --- | --- |
| `tabular_train_template` | `c2ef58062a5347c9b8f3e7ed13945be9` | `http://localhost:8080/projects/739356ee8e354bb48283539ced2a99eb/experiments/c2ef58062a5347c9b8f3e7ed13945be9/output/log` | synced |
| `tabular_eval_template` | `641a810049c84a6dbeafefb2ae513bcb` | `http://localhost:8080/projects/739356ee8e354bb48283539ced2a99eb/experiments/641a810049c84a6dbeafefb2ae513bcb/output/log` | synced |
| `tabular_infer_template` | `a6c147c9768b4c0f9de5cef470ad8257` | `http://localhost:8080/projects/739356ee8e354bb48283539ced2a99eb/experiments/a6c147c9768b4c0f9de5cef470ad8257/output/log` | synced |
| `tabular_pipeline_template` | `d8d4fe66b7f8499bbe69178a09eaece2` | `http://localhost:8080/projects/739356ee8e354bb48283539ced2a99eb/experiments/d8d4fe66b7f8499bbe69178a09eaece2/output/log` | synced |

## Decision

Template sync passed. The train and pipeline templates expose `Model/params` as a JSON string, with no stale nested `Model/params/*` keys.
ClearML task and pipeline full model execution proceeded with these four templates.
