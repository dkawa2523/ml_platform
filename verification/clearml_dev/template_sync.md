# ClearML Dev Template Sync Verification

## Run Metadata

- Date: 2026-05-24 15:42 JST
- Commit: `3773e03`
- Profile: `config/profiles/clearml-dev.yaml`
- ClearML project: `MLPlatform/Dev/Templates`
- Queue: `default`
- Repository: `https://github.com/dkawa2523/ml_platform.git`
- Branch: `main`
- Working directory: `.`
- Raw logs: not stored
- Secrets: not stored

## Command

```powershell
python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml
```

## Result

Status: succeeded.

Exactly four templates were registered or updated.

| Template | Task ID | URL | Note |
| --- | --- | --- | --- |
| `tabular_train_template` | `c2ef58062a5347c9b8f3e7ed13945be9` | `http://localhost:8080/projects/739356ee8e354bb48283539ced2a99eb/experiments/c2ef58062a5347c9b8f3e7ed13945be9/output/log` | train clone-run target |
| `tabular_eval_template` | `641a810049c84a6dbeafefb2ae513bcb` | `http://localhost:8080/projects/739356ee8e354bb48283539ced2a99eb/experiments/641a810049c84a6dbeafefb2ae513bcb/output/log` | eval clone-run target |
| `tabular_infer_template` | `a6c147c9768b4c0f9de5cef470ad8257` | `http://localhost:8080/projects/739356ee8e354bb48283539ced2a99eb/experiments/a6c147c9768b4c0f9de5cef470ad8257/output/log` | infer clone-run target |
| `tabular_pipeline_template` | `d8d4fe66b7f8499bbe69178a09eaece2` | `http://localhost:8080/projects/739356ee8e354bb48283539ced2a99eb/experiments/d8d4fe66b7f8499bbe69178a09eaece2/output/log` | PipelineController entrypoint |

## Execution Log Summary

- `tabular_train_template`: synced.
- `tabular_eval_template`: synced.
- `tabular_infer_template`: synced.
- `tabular_pipeline_template`: synced.
- No API key, secret key, token, or password was saved.

## Next Task

The first execution target after sync was `tabular_train_template` with `Model/name=ridge`.
