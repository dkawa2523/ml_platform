# Prohibitions

These rules keep the product small and operable.

## Do Not Import ClearML From `pkgs`

Forbidden in `pkgs/core` and `pkgs/tabular`:

```python
from clearml import Task
import clearml
```

ClearML belongs under `clearml/`.

## Do Not Put ML Logic In `scripts`

`scripts/` is for command wrappers only. Training, preprocessing, evaluation, inference, and pipeline logic belong in packages.

## Do Not Split Config Too Early

Use:

```text
config/tasks
config/profiles
```

Do not add config trees for data, model, trainer, evaluator, logger, or artifacts until the current two-axis layout is no longer enough.

## Do Not Add Abstract Layers Prematurely

Avoid base classes and plugin systems until multiple real implementations need them.

## Do Not Grow Tests Into Contracts

Keep tests focused on:

- local smoke behavior
- config overrides
- ClearML mapping without ClearML server access
- dependency boundaries

Do not add snapshot tests, full-function unit coverage, or real ClearML server tests to normal pytest.

## Do Not Grow Docs For Their Own Sake

Prefer updating the existing docs. Do not add contract docs, repeated troubleshooting pages, or generated docs.

## Do Not Recreate Legacy Repos

Legacy repos are reference material. Reimplement selected features in the current boundary. Do not copy directories, helpers, docs, or tests wholesale.

## Do Not Add Live Cleanup Operations

Avoid production cleanup, delete, or prune operations in this repo unless there is a clear operator workflow and explicit approval.
