# Next Release Backlog

This backlog is planning material, not current product scope. The current
supported, experimental, future, and discarded scope remains defined in
`docs/SPEC.md`.

Do not implement multiple backlog items in one pass. Phase A-F replace the
compatibility full-run product role with the stage-based training and inference
scope defined in `docs/SPEC.md`, while keeping historical
verification evidence indexed instead of deleted.

## Priority

| priority | bucket | title | reason |
| --- | --- | --- | --- |
| P1 | V2 patch | Remote verification for the primary ClearML training pipeline | Promotes or blocks the primary Pipeline-tab draft with evidence. |
| P2 | V2 patch | Remote verification for inference model source resolution | Confirms `task_id` best/ensemble inference from ClearML UI. |
| P3 | V2.1 | Remote verification for experimental sklearn models | Smallest path to promote selected models to supported. |
| P4 | V2.1 | Evaluation table improvement | Useful product artifact without changing templates. |
| P5 | V2.1 | Inference id column and manifest polish | Improves operational use of predictions. |
| P6 | V2.1 | ClearML UI operator examples | Helps operators use existing task templates without adding parameters. |
| P8 | V3 | Heavy model optional extras | Valuable, but dependency and runtime risk are higher. |
| P9 | V3 | Stacking ensemble | Requires leakage policy and verification before implementation. |
| P10 | V3 | Advanced optimization and child tasks | Requires a larger ClearML design decision. |
| P11 | V3 | Advanced plots and reporting | Useful only after table artifacts are stable. |
| P12 | V3 | Large dataset inference | Requires explicit memory and IO design. |
| P13 | V3 | Analysis modes | Useful later, but outside the scalar regression core. |

Phase B-F implementation and docs cleanup are present. If implementing one item
next, start with P1 remote verification.

## V2 Patch

### Completed: Local Training Pipeline Graph

- title: Implement the local stage-based training pipeline.
- purpose: Replace the misleading local compatibility full-run with the intended
  training flow: preprocess, multiple model training, optional ensemble, and
  evaluation.
- scope: Add local orchestration for
  `preprocess_features -> train_<model>* -> build_ensemble optional -> evaluate_models`.
  Reuse existing train/evaluate/ensemble/search functions where possible.
- affected files: `pkgs/tabular`, `config/tasks`, focused tests, and existing
  docs.
- ClearML impact: None in this phase. ClearML was added in Phase C.
- complexity risk: Medium because artifact handoff must be made explicit without
  adding a framework.
- acceptance criteria: Local graph outputs `preprocess_bundle`,
  `feature_spec.json`, per-model model artifacts, `leaderboard.csv`, optional
  `ensemble_info.json`, optional ensemble artifact, `validation_predictions.csv`
  per model, `evaluation_report.json`, `metrics.json`, and `manifest.json`.
- do-not-do: Do not create ClearML templates, copy legacy repo code, add a
  dynamic DAG framework, or mix inference into the training pipeline.

### Completed: ClearML Stage-Based Training Pipeline Graph

- title: Implement the ClearML training pipeline graph with a generic internal
  stage template.
- purpose: Make the training pipeline readable from the ClearML Pipeline tab.
- scope: Add user-facing training pipeline templates and one internal
  `tabular_stage_template` so PipelineController can show preprocess,
  per-model train, optional ensemble, and evaluate stages.
- affected files: `clearml`, `config/tasks`, `docs/SPEC.md`, focused tests, and
  verification.
- ClearML impact: Replaces the deprecated `tabular_pipeline_template` product
  role with stage-based training pipeline templates. Existing task templates
  remain compatible.
- complexity risk: Medium to high because task artifact references and Pipeline
  UI parameters must remain understandable.
- acceptance criteria: Pipeline graph shows `preprocess_features`,
  `train_<model>*`, optional `build_ensemble`, and `evaluate_models`; no
  model-specific templates are created.
- do-not-do: Do not create one template per model, one template per ensemble, or
  per-trial ClearML child tasks in this phase.

### Future / Experimental Evidence: Stage-Based Optimization Pipeline

- title: Implement local and dry-run ClearML optimization graph.
- purpose: Treat optimization as
  `preprocess_features -> search_trials -> retrain_best -> evaluate_best`
  instead of hiding it as a train-internal-only option.
- scope: Add shared grid/random search helpers, local optimization stages,
  ClearML dry-run graph generation, and verification.
- affected files: `pkgs/tabular`, `clearml/pipelines.py`, focused tests,
  docs, and `verification/optimization/optimization_pipeline.md`.
- ClearML impact: Uses the existing `tabular_stage_template`; no
  optimize-specific template or per-trial child task was added.
- complexity risk: Medium because optimization and ensemble remain mutually
  exclusive and remote execution is still pending.
- acceptance criteria: Local optimization run and ClearML dry-run produce
  `search_trials`, `retrain_best`, and `evaluate_best` artifacts.
- product status: Not primary product scope. Keep out of default ClearML UI
  entrypoints until a separate promotion decision is made.
- do-not-do: Do not add Optuna, Ray Tune, Bayesian search, or trial child tasks
  before remote verification.

### P1: Remote Verification For Primary ClearML Training Pipeline

- title: Verify `tabular_train_pipeline_template` on the dev ClearML server.
- purpose: Decide whether the primary Pipeline-tab draft is ready for supported
  scope or remain experimental.
- scope: Sync templates, run the primary pipeline draft from the Pipeline tab, and
  record graph, parameters, artifacts, and failure logs.
- affected files: `verification/training_pipeline/clearml_training_pipeline.md`
  and optionally small docs corrections.
- ClearML impact: No template or code changes unless verification exposes a
  concrete bug.
- complexity risk: Medium because worker capacity and artifact URL reachability
  are environment-dependent.
- acceptance criteria: Pipeline graph and artifacts match `docs/SPEC.md`, or
  blockers are documented without calling the feature supported.
- do-not-do: Do not change prod, clean up old tasks, add templates, or store
  secrets/screenshots/raw logs in the repo.

### Completed: Inference Model Reference Implementation

- title: Implement explicit inference model source resolution.
- purpose: Keep inference separate from training pipeline execution while making
  best-model and ensemble inference usable from ClearML UI.
- scope: Keep primary `tabular_infer_template` handling focused on
  `source_task_id + model_selector` and `local_model_path`. Keep
  `model_artifact_url` and `clearml_model_id` as explicit-only
  future/experimental compatibility paths, not primary UI parameters.
- affected files: `clearml/adapter.py`, `clearml/app.py`,
  `config/tasks/tabular_infer.yaml`, `pkgs/tabular` inference validation, docs,
  and focused tests.
- ClearML impact: Resolves task artifacts before passing a local
  `model.artifact_path` into ClearML-free inference code; future sources remain
  outside the primary UI.
- complexity risk: Medium because selector resolution depends on training
  pipeline artifact contracts.
- acceptance criteria: `source_type=task_id` with `model_selector=best` and
  `model_selector=ensemble` works; local path flow remains compatible; no
  inference pipeline is introduced.
- do-not-do: Do not add online serving, a streaming reader, or ClearML imports
  under `pkgs`.

### P2: Remote Verification For Inference Model Source Resolution

- title: Verify `tabular_infer_template` source resolution on the dev ClearML
  server.
- purpose: Confirm that ClearML UI users can run inference from a training
  pipeline controller task id with `model_selector=best` and `ensemble`.
- scope: Run `tabular_infer_template` from the UI with `source_type=task_id`,
  record artifact resolution, predictions, manifest, and any blockers.
- affected files: `verification/inference/infer_task_reference.md` and
  optionally small docs corrections.
- ClearML impact: No code changes unless task-id resolution fails in dev.
- complexity risk: Medium because prior training pipeline artifacts and
  Dataset artifact URL reachability are environment-dependent.
- acceptance criteria: Best and ensemble selectors either pass remotely or
  blockers are documented without calling the feature supported.
- do-not-do: Do not add an inference pipeline, online serving, or extra source
  types during verification.

### Completed: Verification Scope Index

- title: Add a compact verification scope index.
- purpose: Make it clear which evidence supports supported features and which
  evidence only supports experimental features.
- scope: Add `verification/README.md` and historical banners to high-risk old
  release summaries.
- affected files: `verification/README.md`, selected historical verification
  summaries, `docs/SPEC.md`, and `docs/CODEX_HANDOFF.md`.
- ClearML impact: None.
- complexity risk: Low.
- acceptance criteria: Current product evidence, experimental evidence, and
  historical compatibility evidence are visibly separated.
- do-not-do: Do not generate a large matrix for every historical run, and do not
  require real ClearML server tests in pytest.

### Additional: ClearML UI Parameter Polish

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
- acceptance criteria: Template sync dry-run reports the current default targets
  from `docs/SPEC.md`; existing parameter overrides still work; no
  model-specific branch is added.
- do-not-do: Do not rename public parameters without a compatibility path, and
  do not add UI groups beyond `Input`, `Run`, `Model`, and `Output`.

### Additional: Artifact Naming Consistency Review

- title: Review artifact naming before adding new artifacts.
- purpose: Keep ClearML artifact tabs readable as evaluation and inference
  outputs grow.
- scope: Document current names such as `validation_predictions`,
  `evaluation_predictions`, `predictions`, `leaderboard`, and
  pipeline-prefixed variants. Keep optimization artifact names in a future /
  experimental note only.
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

### P3: Remote Verification For Experimental Sklearn Models

- title: Verify selected experimental sklearn models remotely.
- purpose: Promote only models with local and ClearML remote evidence to
  supported.
- scope: Run small ClearML task verification for `elasticnet`, `extra_trees`,
  `knn`, `svr`, and `mlp`; keep `lasso` evidence as a reference. Add
  compatibility full-run or stage-based training pipeline verification only for
  models intended to become supported.
- affected files: `verification/*`, `docs/SPEC.md`, `docs/CODEX_HANDOFF.md`.
- ClearML impact: Uses existing train/eval/infer task templates and the current
  approved full-run or training pipeline entrypoint for the active phase.
- complexity risk: Medium because runtime behavior differs by model.
- acceptance criteria: Each promoted model has local train/eval/infer evidence,
  appropriate full-run or stage-pipeline evidence, and ClearML task evidence;
  runtime caveats such as `mlp` convergence warnings are documented; unverified
  models remain experimental.
- do-not-do: Do not promote all implemented models at once, and do not add
  optional heavy dependencies.

### P4: Evaluation Table Improvement

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

### P5: Inference Id Column And Manifest Polish

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

### P6: ClearML UI Operator Examples

- title: Add compact operator examples for common ClearML runs.
- purpose: Reduce clone-run mistakes without expanding the UI parameter surface.
- scope: Add short examples for the primary training pipeline, candidates,
  ensemble, inference source selection, chunked infer, and pipeline dataset-file
  usage.
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
- purpose: Preserve a small, understandable ClearML operation model.
- scope: Do not recreate legacy template sprawl. The approved user-facing
  training pipeline templates plus one internal `tabular_stage_template` are the
  exception; still avoid model-, dataset-, ensemble-, and optimization-specific
  templates.
- affected files: `clearml/templates.py`, `docs/SPEC.md`,
  `docs/CODEX_HANDOFF.md`.
- ClearML impact: Prevents UI sprawl and clone-run confusion.
- complexity risk: Low.
- acceptance criteria: Template sync dry-run reports only the current approved
  task/pipeline templates for the active phase.
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
