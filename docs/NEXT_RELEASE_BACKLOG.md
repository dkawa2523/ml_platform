# Next Release Backlog

Keep this list short. Product scope is in `docs/SPEC.md`; future/P2 scope is
in `docs/ROADMAP.md`.

## Required Before Release

1. Archive stale ClearML server tasks manually after the latest templates are
   confirmed.

## Current Evidence

- Current local and dry-run evidence is recorded under `verification/`.
- Record fresh remote task IDs only in verification notes after templates are
  synced from the branch being released.

## Later

- Optional local GBM smoke in an environment with `pkgs/tabular[gbm]`.
- P2 roadmap items stay in `docs/ROADMAP.md` until explicitly promoted.
- Advanced diagnostics only when they have a clear user-facing decision value.
