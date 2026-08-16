# Quality gates

The repository exposes four stable commands through Nox:

```text
uv run --group quality nox -s quality-fast
uv run --group quality nox -s quality-pr
uv run --group nightly nox -s quality-nightly
uv run --group quality nox -s quality-baseline
```

`runner.py` defines command order, `process.py` executes subprocesses,
`static_analysis.py` invokes static tools, and `gates.py` compares their
findings. `secrets.py` owns secret scanning, while `mutation.py` owns mutmut
result handling and its isolated workspace.

`quality-fast` formats changed Python files, then checks changed-file Ruff
diagnostics, the complete Pyrefly project, and the normal test suite.
`quality-pr` is read-only with respect to tracked baselines and runs all PR
gates. Pure branch coverage may improve without a baseline update, but cannot
fall below the explicitly recorded value. `quality-nightly` adds focused multi-seed property tests, command-line
Pipeline/inference smoke tests, and mutation testing. Mutmut 3 requires fork
support, so nightly must run on Linux or WSL and fails explicitly on native
Windows.

Set `QUALITY_UPDATE_MUTATION=1` when running `quality-baseline` on Linux or
WSL to refresh mutation results. Without it, baseline maintenance preserves
the reviewed mutation snapshot.

Only `quality-baseline` may update `quality/baseline.json` or
`.secrets.baseline`. Every finding should be reviewed before committing a
baseline change. Ruff and Bandit retain only reviewed legacy findings; dependency
vulnerabilities and Vulture candidates always fail instead of being baselined.
