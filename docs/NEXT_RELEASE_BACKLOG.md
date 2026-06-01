# Next Release Backlog

This backlog is planning material, not current product scope. The current
supported, experimental, future, and discarded scope remains defined in
`docs/SPEC.md`.

Do not implement multiple backlog items in one pass. Each item must preserve the
current V2 boundary: three ClearML task templates plus one Pipeline-tab draft,
`config/tasks` plus `config/profiles`, ClearML SDK under `clearml/`, and
ClearML-free `pkgs`.

## Priority

| priority | bucket | title | reason |
| --- | --- | --- | --- |
| P0 | V2 patch | Document pipeline dataset-file UI parameters | Known docs gap; no runtime behavior change needed. |
| P1 | V2 patch | Verification scope index | Prevents accidental promotion of experimental features. |
| P2 | V2.1 | Remote verification for experimental sklearn models | Smallest path to promote selected models to supported. |
| P3 | V2.1 | Evaluation table improvement | Useful product artifact without changing templates. |
| P4 | V2.1 | Inference id column and manifest polish | Improves operational use of predictions. |
| P5 | V3 | Heavy model optional extras | Valuable, but dependency and runtime risk are higher. |
| P6 | V3 | Advanced optimization and child tasks | Requires a larger ClearML design decision. |
| P7 | V3 | Analysis modes and advanced plots | Useful later, but outside the scalar regression core. |

If implementing one item next, start with P0.

## V2 Patch

### P0: Document Pipeline Dataset-File UI Parameters

- title: Document pipeline dataset-file UI parameters.
- purpose: Make the existing pipeline-only dataset file controls visible to
  operators and future maintainers.
- scope: Document `Input/train_dataset_file`, `Input/eval_dataset_file`, and
  `Input/infer_dataset_file` as pipeline controller parameters that map to each
  step's `Input/dataset_file`.
- affected files: `README.md`, `docs/SPEC.md`, `docs/CODEX_HANDOFF.md`,
  optionally `verification/v2_remote/parameter_sets.md`.
- ClearML impact: Documentation only. No launch target count change and no new
  task type.
- complexity risk: Low.
- acceptance criteria: Docs explain when to use pipeline-specific dataset file
  parameters; dry-run still shows the same train -> eval -> infer graph; no new
  ClearML parameters outside `Input`, `Run`, `Model`, and `Output`.
- do-not-do: Do not add dataset-specific templates, dataset registration, or a
  new config axis.

### P1: Verification Scope Index

- title: Add a compact verification scope index.
- purpose: Make it clear which evidence supports supported features and which
  evidence only supports experimental features.
- scope: Add a short table to the existing verification summary or docs that
  maps feature/model groups to local, ClearML task, and ClearML pipeline
  evidence.
- affected files: `docs/SPEC.md`, `docs/CODEX_HANDOFF.md`, existing
  `verification/*/summary.md` files if needed.
- ClearML impact: None.
- complexity risk: Low.
- acceptance criteria: Official supported models have explicit local/task/pipeline
  evidence; experimental sklearn models are not described as fully supported
  unless evidence exists; no new verification directory is required.
- do-not-do: Do not generate a large matrix for every historical run, and do not
  require real ClearML server tests in pytest.

### P2: ClearML UI Parameter Polish

- title: Reduce ClearML UI parameter ambiguity without changing the product
  surface.
- purpose: Keep clone-run operation understandable for non-code users.
- scope: Review parameter names and defaults for noisy or confusing entries,
  especially model params inherited from a base template. Prefer documentation
  or template default cleanup over new parameters.
- affected files: `clearml/templates.py`, `clearml/adapter.py`,
  `docs/SPEC.md`, `verification/v2_remote/ui_review.md`.
- ClearML impact: Potentially changes template defaults only. Existing
  `Model/*`, `Input/*`, `Run/*`, and `Output/*` keys must remain compatible.
- complexity risk: Low to medium.
- acceptance criteria: Template sync dry-run still reports exactly four
  templates; existing parameter overrides still work; no model-specific branch
  is added.
- do-not-do: Do not rename public parameters without a compatibility path, and
  do not add UI groups beyond `Input`, `Run`, `Model`, and `Output`.

### P3: Artifact Naming Consistency Review

- title: Review artifact naming before adding new artifacts.
- purpose: Keep ClearML artifact tabs readable as evaluation and inference
  outputs grow.
- scope: Document current names such as `validation_predictions`,
  `evaluation_predictions`, `predictions`, `leaderboard`,
  `optimization_trials`, and pipeline-prefixed variants.
- affected files: `docs/SPEC.md`, `docs/CODEX_HANDOFF.md`, tests only if a
  naming bug is found.
- ClearML impact: Documentation first; code change only if a clear naming bug is
  found.
- complexity risk: Low.
- acceptance criteria: Current artifact names are documented; no artifact rename
  breaks existing verification; future artifact additions have a naming rule.
- do-not-do: Do not rename stable artifacts just for aesthetics, and do not add
  a separate runtime leaderboard task.

## V2.1

### P4: Remote Verification For Experimental Sklearn Models

- title: Verify selected experimental sklearn models remotely.
- purpose: Promote only models with local and ClearML remote evidence to
  supported.
- scope: Run small ClearML task verification for `elasticnet`, `extra_trees`,
  `knn`, `svr`, and `mlp`; keep `lasso` evidence as a reference. Add pipeline
  verification only for models intended to become supported.
- affected files: `verification/*`, `docs/SPEC.md`, `docs/CODEX_HANDOFF.md`.
- ClearML impact: Uses existing train/eval/infer task templates and Pipeline-tab
  draft. No new template or task YAML.
- complexity risk: Medium because runtime behavior differs by model.
- acceptance criteria: Each promoted model has local train/eval/infer/pipeline
  evidence and ClearML task/pipeline evidence; runtime caveats such as `mlp`
  convergence warnings are documented; unverified models remain experimental.
- do-not-do: Do not promote all implemented models at once, and do not add
  optional heavy dependencies.

### P5: Evaluation Table Improvement

- title: Add minimal evaluation error columns.
- purpose: Make `evaluation_predictions` more useful for data scientists without
  introducing advanced plots.
- scope: Add columns such as `prediction`, `residual`, and `abs_error` to eval
  output using the existing eval task and artifact path.
- affected files: `pkgs/tabular/src/ml_platform_tabular/evaluate.py`,
  `tests/test_tabular_smoke.py`, `docs/SPEC.md`,
  `verification/*` after manual checks.
- ClearML impact: Same `evaluation_predictions` artifact, richer table content.
- complexity risk: Low to medium.
- acceptance criteria: Eval artifact remains named `evaluation_predictions`;
  metrics are unchanged; local smoke tests cover the columns; ClearML upload path
  remains generic through `clearml/reports.py`.
- do-not-do: Do not add plot generation, diagnostics packages, or separate eval
  templates in this item.

### P6: Inference Id Column And Manifest Polish

- title: Make `id_columns` behavior explicit in inference outputs.
- purpose: Help operators join predictions back to source records.
- scope: Document and, if needed, record `id_columns` in the inference manifest;
  preserve the current rule that input columns stay in `predictions.csv`.
- affected files: `pkgs/tabular/src/ml_platform_tabular/infer.py`,
  `tests/test_tabular_smoke.py`, `docs/SPEC.md`.
- ClearML impact: Same `predictions` artifact and same `Output/*` parameters.
- complexity risk: Low.
- acceptance criteria: `predictions.csv` still preserves input columns; manifest
  identifies configured id columns; reserved output column checks still pass.
- do-not-do: Do not add a new output schema version unless columns actually
  change, and do not drop source columns from predictions.

### P7: ClearML UI Operator Examples

- title: Add compact operator examples for common ClearML runs.
- purpose: Reduce clone-run mistakes without expanding the UI parameter surface.
- scope: Add short examples for single model, comparison, ensemble, search,
  chunked infer, and pipeline dataset-file usage.
- affected files: `README.md`, `docs/SPEC.md`, or `docs/CODEX_HANDOFF.md`.
- ClearML impact: Documentation only.
- complexity risk: Low.
- acceptance criteria: Examples use existing parameters only; README remains
  brief; detailed examples live in existing docs.
- do-not-do: Do not create tutorial pages, issue templates, or repeated
  troubleshooting docs.

## V3

### P8: Optional Heavy Model Extras

- title: Add LightGBM, XGBoost, and CatBoost as optional model families.
- purpose: Expand model coverage while keeping the default runtime small.
- scope: Add one model family per implementation pass with optional dependency
  handling, local smoke tests, and ClearML remote verification.
- affected files: `pkgs/tabular/src/ml_platform_tabular/models.py`,
  dependency files, tests, docs, verification.
- ClearML impact: Same `Model/name` and `Model/params`; no model-specific
  template.
- complexity risk: High due to dependencies, install time, native libraries, and
  runtime variance.
- acceptance criteria: Optional dependency failure messages are clear; default
  install remains usable; each promoted model has local and remote evidence.
- do-not-do: Do not add TabPFN or GPU assumptions in the same pass, and do not
  make heavy dependencies required by default.

### P9: Stacking Ensemble

- title: Add stacking as a new ensemble method only after a clear policy.
- purpose: Provide a stronger ensemble option for tabular regression.
- scope: Design stacking around the existing comparison mode and standard
  `model.joblib` artifact.
- affected files: `pkgs/tabular/src/ml_platform_tabular/train.py`,
  `models.py`, tests, docs, verification.
- ClearML impact: Reuses `Model/ensemble_*`; may need documented method value
  `stacking`.
- complexity risk: High because leakage control and validation policy matter.
- acceptance criteria: No target leakage; eval/infer consume one standard model
  artifact; comparison and existing ensembles still work.
- do-not-do: Do not recreate legacy `train_ensemble_full`, task artifact query,
  or ensemble-specific templates.

### P10: Advanced Optimization

- title: Add Optuna or Ray Tune only after choosing one orchestration model.
- purpose: Support richer hyperparameter search for expensive models.
- scope: Decide between in-task optimization and per-trial ClearML child tasks
  before implementation.
- affected files: `pkgs/tabular`, `clearml`, `config/tasks`, tests, docs,
  verification.
- ClearML impact: Potentially large. Per-trial child tasks would change run
  topology and operator expectations.
- complexity risk: High.
- acceptance criteria: Chosen design preserves existing `grid` and `random`
  search; trial tables are visible; failure behavior is understandable in
  ClearML.
- do-not-do: Do not add Optuna, Ray Tune, child tasks, and an optimize template
  in one pass.

### P11: Advanced Plots And Reporting

- title: Add selected plots after table artifacts are stable.
- purpose: Improve model review without reintroducing broad diagnostics.
- scope: Consider residual histogram, true-vs-predicted scatter, and feature
  importance for eligible models.
- affected files: `pkgs/tabular`, `clearml/reports.py`, tests, docs,
  verification.
- ClearML impact: Adds plot reporting through the existing generic plot path.
- complexity risk: Medium.
- acceptance criteria: Plots are optional, deterministic enough for smoke tests,
  and useful in ClearML UI.
- do-not-do: Do not add a diagnostics framework, drift reports, or generated
  report pages.

### P12: Large Dataset Inference

- title: Support larger inference datasets deliberately.
- purpose: Move beyond eager CSV reads when there is a real operational need.
- scope: Design streaming or partitioned inference with explicit IO constraints.
- affected files: `pkgs/tabular/src/ml_platform_tabular/infer.py`, tests, docs,
  verification, possibly dependency files.
- ClearML impact: Same infer template if possible; may change artifact size and
  storage expectations.
- complexity risk: High.
- acceptance criteria: Memory behavior is measured; output schema remains
  compatible; chunking semantics are documented.
- do-not-do: Do not promise online serving or distributed inference as part of
  this item.

### P13: 1D, 2D, And Distribution Mode Productization

- title: Productize non-regression tabular analysis modes only after a second
  clear user workflow exists.
- purpose: Keep the current scalar regression product from absorbing unrelated
  analysis responsibilities too early.
- scope: Define separate task behavior for 1D, 2D, and distribution mode
  decomposition before adding ClearML remote support.
- affected files: `pkgs/tabular`, `config/tasks`, `clearml`, tests, docs,
  verification.
- ClearML impact: May need new task behavior, but must not create dataset- or
  model-specific templates.
- complexity risk: High due to product scope ambiguity.
- acceptance criteria: Each mode has a clear user story, stable outputs, local
  tests, and explicit ClearML UI parameters.
- do-not-do: Do not copy legacy analysis trees or add broad plotting/diagnostic
  frameworks.

## Discard

### D1: Legacy Template Expansion

- title: Discard model-, dataset-, leaderboard-, ensemble-, and optimization-
  specific templates.
- purpose: Preserve the product's simple ClearML operation model.
- scope: Keep exactly three task templates plus one Pipeline-tab draft unless a
  future product review explicitly changes this boundary.
- affected files: `clearml/templates.py`, `docs/SPEC.md`,
  `docs/CODEX_HANDOFF.md`.
- ClearML impact: Prevents UI sprawl and clone-run confusion.
- complexity risk: Low.
- acceptance criteria: Template sync dry-run reports three task templates and
  one Pipeline-tab draft.
- do-not-do: Do not import legacy template YAML or recreate legacy task trees.

### D2: Legacy Contracts, Checklists, Diagnostics, And Helpers

- title: Discard broad legacy support scaffolding.
- purpose: Avoid turning the product repo into a process framework.
- scope: Reject old contract docs, checklist pages, troubleshooting trees,
  diagnostics helpers, abstract plugin systems, and excessive tests.
- affected files: `docs/*`, `tests/*`, `pkgs/*`, `clearml/*`.
- ClearML impact: Keeps ClearML behavior focused on current product workflows.
- complexity risk: Low if enforced during review.
- acceptance criteria: New docs remain short and current; tests remain smoke and
  boundary oriented.
- do-not-do: Do not bulk copy old files, and do not add snapshot-style contract
  tests without a concrete product bug.

### D3: Old Adapter Split And Live Cleanup

- title: Discard old adapter layering and live cleanup operations.
- purpose: Keep runtime behavior understandable and avoid destructive operator
  actions.
- scope: Do not reintroduce legacy adapter splits, cleanup scripts, delete/prune
  flows, or environment-wide maintenance tasks.
- affected files: `clearml/*`, `scripts/*`, `deploy/*`.
- ClearML impact: Avoids destructive ClearML side effects and storage surprises.
- complexity risk: Low.
- acceptance criteria: Operator commands remain run/sync/deploy oriented.
- do-not-do: Do not add cleanup commands without a separately reviewed operator
  workflow and explicit approval.
