# ADR 0002: Package manifest boundary

## Status

Accepted

## Decision

- `pkgs/core` owns the small runtime-neutral records shared across packages.
- `pkgs/tabular` owns tabular parameters, stage outputs, policy, and domain plans.
- `clearml/` translates those records to ClearML SDK calls and owns template lifecycle.
- Configuration remains one merged dictionary validated at the external boundary.
- ClearML SDK objects never enter `pkgs/core` or `pkgs/tabular`.

The manifest records only values consumed at runtime: task/stage keys,
parameters, output artifact names, and the package version. Runner resolution
stays in `ml_platform_tabular.runners`; pipeline execution order stays in the
domain plan. Descriptive metadata and migration-only validation do not belong
in the contract.

## Consequences

- ClearML parameter names and artifact names remain stable public surfaces.
- Internal file layout and helper types may change without expanding the manifest.
- Remote ClearML Agent compatibility must be verified before changing script entrypoints.
