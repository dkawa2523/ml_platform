# Legacy Repo Policy

Legacy repos are read-only reference material. This product repo is not a merge of those repos.

Expected workspace shape:

```text
workspace/
  ml_platform/
  _reference_repos/       # or reference_repos/
    Plartform_pipe/
    table_analysis/
```

The reference directory must not be committed into `ml_platform`.

## Allowed

- Read legacy code to understand a feature.
- Reimplement a small feature in the correct product boundary.
- Keep the new repo structure simple.

## Forbidden

- Import from a legacy repo.
- Bulk copy legacy source, tests, docs, or directories.
- Recreate legacy config or helper layering.
- Restore old contract docs or troubleshooting pages.
- Bring back live cleanup scripts or broad diagnostics.

## Placement

- ClearML runtime code: `clearml/`
- Core config, IO, artifacts, result objects: `pkgs/core`
- Tabular analysis logic: `pkgs/tabular`
- Agent runtime: `deploy/`
- Wrapper commands: `scripts/`
- Short current docs: `docs/`

## Selection Process

When using a legacy feature:

1. Identify the product need.
2. Decide whether to keep, defer, or discard the feature.
3. Reimplement only the necessary behavior.
4. Keep tests small and product-facing.
5. Run local smoke and boundary checks.
