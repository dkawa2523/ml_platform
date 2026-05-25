# V1.1 Model Extension

Run date: 2026-05-25 00:22:45 +09:00
Git commit: 0756d3b

## Scope

V1.1 adds lightweight sklearn single-model regression options while keeping the existing execution surface:

- `Model/name`
- `Model/params`
- the four task-type ClearML templates
- no model-specific YAML files
- no model-specific ClearML adapter logic

## Added Models

| Model | Default params | Notes |
| --- | --- | --- |
| `lasso` | `alpha=0.01`, `max_iter=5000` | Small regularized linear baseline. |
| `elasticnet` | `alpha=0.01`, `l1_ratio=0.5`, `max_iter=5000`, `random_state=42` | Mixed L1/L2 linear baseline. |
| `extra_trees` | `n_estimators=50`, `random_state=42`, `n_jobs=1` | Lightweight tree ensemble. |
| `knn` | `n_neighbors=5`, `weights=distance` | Distance-based baseline. |
| `svr` | `kernel=rbf`, `C=1.0`, `epsilon=0.1`, `gamma=scale` | Small-kernel regression baseline. |
| `mlp` | `hidden_layer_sizes=[32]`, `solver=lbfgs`, `max_iter=500`, `random_state=42` | Small neural baseline for small tabular data. |

User-provided `Model/params` values override these defaults.

## Excluded From V1.1

- `gaussian_process`: deferred because runtime and memory behavior need a separate stability gate.
- LightGBM, XGBoost, CatBoost, TabPFN: deferred to V2+ because they add heavier dependencies.
- ensemble, stacking, weighted ensemble, and train_ensemble_full: deferred; V1.1 is single-model expansion only.

## Files Changed

- `pkgs/tabular/src/ml_platform_tabular/models.py`
- `tests/test_tabular_smoke.py`
- `README.md`
- `docs/SPEC.md`
- `docs/CODEX_HANDOFF.md`
- `docs/PRODUCTIZATION_PHASES.md`

## Verification Summary

- Local train/eval/infer/pipeline passed for all V1.1 models.
- Pytest passed: `28 passed`.
- ClearML template dry-run passed with the same four templates.
- `pkgs` ClearML boundary check found no ClearML imports.

MLP emitted a sklearn convergence warning during one run, but the task exited successfully and produced artifacts. This is acceptable for the V1.1 small smoke default; large-data tuning remains future work.

## ClearML Compatibility

V1.1 models use the existing ClearML parameter surface:

- single model: `Model/name` and `Model/params`
- comparison mode: `Model/candidates` and `Model/selection_metric`

No template was added. No ClearML code contains model-specific branches.

Real ClearML dev task and pipeline execution remains the next verification step for these V1.1 models.
