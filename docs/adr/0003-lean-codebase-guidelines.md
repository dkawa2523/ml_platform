# ADR 0003: Lean codebase guidelines

## Status

Accepted

## Context

After the PR review response work, the repository has better tests, typed
boundaries, runtime manifests, and module splits. It also has more compatibility
layers and new contracts that were added to preserve behavior during migration.

Future cleanup should make the codebase smaller and easier to read without
undoing product behavior or ClearML template compatibility.

## Decision

- Do not keep unused code.
- Do not add abstractions only because they may be useful later.
- Remove one-implementation Protocols, Registries, or Providers unless they
  protect a real runtime or package boundary.
- Do not keep contract fields that are only explanatory. If no runtime,
  manifest validation, artifact schema, or test consumes the field, remove it
  or move the explanation to docs.
- Prefer confirming actual repository usage and ClearML template compatibility
  before preserving public API compatibility for internal-only helpers.
- If an API is already externally published, record the compatibility impact
  before deletion.
- Keep diagnostics actionable. If a warning does not tell the user what to do,
  remove it or rewrite it.
- Keep facades only for a defined migration period. After internal callers,
  tests, and target repositories migrate, remove stale private re-exports.
- Keep formatting-only changes separate from behavior or cleanup changes.
- Keep Kubernetes / K8 verification separate from this repository cleanup unless
  a future task explicitly scopes it in.

## Consequences

- Deletion commits should cite the confirmation method: static analysis, grep,
  tests, entrypoint checks, or ClearML manual verification.
- Large files are not automatically bad, but files with mixed product policy,
  runtime rendering, compatibility, and reporting should be simplified first.
- Compatibility wrappers should have tests while they exist and a documented
  removal condition.
