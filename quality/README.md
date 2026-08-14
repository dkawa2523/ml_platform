# Quality gates

The repository exposes four stable commands through Nox:

```text
uv run --group quality nox -s quality-fast
uv run --group quality nox -s quality-pr
uv run --group nightly nox -s quality-nightly
uv run --group quality nox -s quality-baseline
```

`quality-fast` formats changed Python files, then checks changed-file Ruff
diagnostics, the complete Pyrefly project, and the normal test suite.
`quality-pr` is read-only with respect to tracked baselines and runs all PR
gates. `quality-nightly` adds three Hypothesis seeds, the synthetic load check,
and mutation testing. Mutmut 3 requires fork support, so nightly must run on
Linux or WSL and fails explicitly on native Windows.

Set `QUALITY_UPDATE_MUTATION=1` when running `quality-baseline` on Linux or
WSL to refresh mutation results. Without it, baseline maintenance preserves
the reviewed mutation snapshot.

Only `quality-baseline` may update `quality/baseline.json`,
`quality/pyrefly-baseline.json`, or `.secrets.baseline`. Every finding should be
reviewed before committing a baseline change. Existing findings may improve
without regenerating the baseline; new fingerprints, larger counts, and higher
complexity fail the gate.
