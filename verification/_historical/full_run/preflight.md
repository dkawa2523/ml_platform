# Full Run Preflight

## Run Metadata

- Date: 2026-05-24
- Verified commit after fixes: `0d4b2eb`
- Profile: `config/profiles/local.yaml`
- ClearML dev profile: `config/profiles/clearml-dev.yaml`
- Raw logs: not stored
- Secrets: not stored

## Local Smoke

All commands exited with code 0:

```powershell
.\.venv\Scripts\python.exe scripts\make_sample_data.py
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_train.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_eval.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_infer.yaml --profile config\profiles\local.yaml
.\.venv\Scripts\python.exe scripts\local_run.py --task config\tasks\tabular_pipeline.yaml --profile config\profiles\local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\pytest.exe -q
```

Pytest result:

```text
21 passed
```

## Boundary Checks

- `pkgs` ClearML import check: no matches.
- ClearML SDK references remain under `clearml/`.
- Legacy repo name scan found only policy/documentation references.
- Generated paths such as `.venv/`, `data/`, `outputs/`, caches, and egg-info directories remain ignored.

## ClearML Dev Profile

- Project root: `MLPlatform/Dev`
- Queue: `default`
- Repository: `https://github.com/dkawa2523/ml_platform.git`
- Branch: `main`
- Working directory: `.`
- Dataset project: `datasets-dev`
- `artifact_output_uri`: `null`
- No credentials are stored in the profile.

## Operational Docs

The docs state:

- ClearML Agent Dataset artifact URLs must be reachable from the Agent environment.
- `Input/local_path` is valid on an Agent only when the path exists inside the Agent container or mounted PVC.
- `artifact_output_uri` controls newly produced run artifacts and does not fix Dataset storage reachability.
- Remote pipeline execution needs two worker slots or separate controller and step queues.

## Decision

Preflight passed. Proceeded to full model local and ClearML dev execution.
