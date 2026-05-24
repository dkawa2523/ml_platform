# ADR 0001: Legacy repos are reference only

## Decision

`Plartform_pipe` and `table_analysis` are reference repositories. They are not copied into the product repository as source trees.

## Reason

The product repository must keep a small, clear boundary:

- `pkgs` for ClearML-independent logic
- `clearml` for ClearML adapters
- `deploy` for runtime environment
- `config` for task/profile inputs

Copying legacy trees would reintroduce old contracts, duplicated docs, helpers, and mixed responsibilities.

## Consequence

Legacy code is migrated by feature, not by file. Each migrated feature must fit the current boundary and pass local smoke tests.
