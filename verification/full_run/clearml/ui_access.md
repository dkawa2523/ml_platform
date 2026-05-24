# ClearML UI Access

## Access Method

- Direct browser or Computer Use access from this Codex environment: not available.
- Primary evidence source: ClearML task URLs plus SDK metadata for status, parameters, metrics, artifacts, and pipeline steps.
- Screenshots: not generated automatically.

## Screenshot Policy

If humans add screenshots later:

- Store only sanitized images under `verification/full_run/clearml/screenshots/`.
- Do not include API keys, tokens, passwords, credential pages, or private storage credentials.
- Prefer task parameter, scalar, artifact, and pipeline graph views.
- Do not save raw browser dumps.

## Allowed UI Operations

- Dev project and dev queue only.
- Clone template tasks.
- Edit `Input/*`, `Run/*`, `Model/*`, and `Output/*` parameters.
- Enqueue cloned tasks or pipeline controller tasks.

## Forbidden UI Operations

- Delete, archive, abort, reset, cleanup, or live deletion.
- Touch prod project, prod queue, or prod profile.
- Store secrets or raw logs in verification files.

## Decision

UI review proceeded from SDK metadata and task URLs. Manual screenshots remain optional and are not required for the v1 gate.
