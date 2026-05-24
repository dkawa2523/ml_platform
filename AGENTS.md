# Codex / Agent Instructions

This repo is the product repo for `ml_platform`. Legacy repositories are reference material only. Do not reshape this repo to match them.

## Hard Rules

1. Edit product code under `ml_platform/`.
2. Do not import ClearML from `pkgs/core` or `pkgs/tabular`.
3. Keep ClearML SDK usage in `clearml/`.
4. Keep `scripts/` as wrappers only.
5. Keep config on two axes: `config/tasks` and `config/profiles`.
6. Do not add new directories, abstract classes, helper layers, tests, or docs unless the responsibility is clearly independent.
7. Keep ClearML UI parameters under `Input`, `Run`, `Model`, and `Output`.
8. Do not copy legacy repo source, docs, tests, or directory layout.

## Reference Repos

Legacy repos may be present as sibling read-only material, usually under `_reference_repos/` or `reference_repos/`.

- Read them only to understand features.
- Do not import from them.
- Do not bulk copy from them.
- Reimplement only the small feature needed in the current product boundary.

## Required Checks

```powershell
python scripts/make_sample_data.py
python scripts/local_run.py --task config/tasks/tabular_train.yaml --profile config/profiles/local.yaml
python scripts/local_run.py --task config/tasks/tabular_eval.yaml --profile config/profiles/local.yaml
python scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

Boundary checks:

```powershell
rg -n "from clearml|import clearml|PipelineController|StorageManager" pkgs
rg -n "reference_repos|Plartform_pipe|table_analysis" pkgs clearml scripts config tests
```

## Change Style

- Prefer small, product-facing fixes.
- Keep docs short and current.
- Keep tests focused on smoke behavior and boundaries.
- Do not add real ClearML server calls to normal pytest or CI.
- Keep optional dependencies optional.
