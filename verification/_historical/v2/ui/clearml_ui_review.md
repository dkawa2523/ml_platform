# V2 ClearML UI Usability Review

> Historical note: this file reviews the old four-template compatibility UI and
> fixed `train -> eval -> infer` pipeline. It is not current product readiness
> evidence for the official stage-based training or optimization pipelines.

Date: 2026-05-28 JST

## Review Basis

This review used local template dry-run output, pipeline dry-run output, generic
ClearML reporting code, and existing V1.3 remote verification evidence. No
delete, archive, reset, cleanup, prod access, raw secret logging, or screenshot
capture was performed.

Commands:

```powershell
.\.venv\Scripts\python.exe scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
.\.venv\Scripts\python.exe clearml/pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
```

## Template And Parameter Surface

| Template | Parameter count | UI assessment |
| --- | ---: | --- |
| `tabular_train_template` | 21 | Usable, but Model group is dense because it now covers single, comparison, ensemble, and search. |
| `tabular_eval_template` | 10 | Simple. `Model/artifact_path` is the main control. |
| `tabular_infer_template` | 12 | Simple enough. `Output/chunk_size` is understandable as optional batch inference control. |
| `tabular_pipeline_template` | 19 | Usable for operators, but users need docs for mode combinations and worker requirements. |

Templates remain task-type based and fixed to four:

- `tabular_train_template`
- `tabular_eval_template`
- `tabular_infer_template`
- `tabular_pipeline_template`

No model-specific, ensemble-specific, optimization-specific, leaderboard-specific,
or dataset-specific template was added.

## Good UX Points

- `Input`, `Run`, `Model`, and `Output` grouping is preserved.
- Single model mode is clear: set `Model/name` and `Model/params`.
- Eval and infer are clear: set `Model/artifact_path` when not using pipeline handoff.
- Comparison and ensemble reuse the same train template and artifacts, avoiding template sprawl.
- Optimization is visible in the same train template through `Model/search_*` without child tasks or a separate optimize template.
- Generic reporting uploads metrics, artifacts, and tables, so `leaderboard`, `optimization_trials`, `optimization_summary`, `best_params`, `ensemble_predictions`, `evaluation_predictions`, and `predictions` are visible as ClearML artifacts/tables.
- Historical compatibility pipeline graph remains fixed and understandable:
  `train -> eval -> infer`.
- Pipeline handoff is clear in dry-run: eval and infer receive `Model/artifact_path=${train.artifacts.model.url}`.

## Confusing Points

- Train `Model` parameters are dense. Users must understand precedence:
  - `Model/candidates` non-empty means comparison mode.
  - `Model/ensemble_enabled=true` requires comparison mode.
  - `Model/search_enabled=true` is HPO mode and currently should not be combined with ensemble.
  - `Model/name` is single-mode fallback when `Model/candidates` is empty.
- `Model/params`, `Model/candidates`, and `Model/search_space` are JSON strings in ClearML UI. This is powerful but error-prone for non-coding users.
- `Output/chunk_size` can be misunderstood as streaming input. It only chunks prediction/write after the table is loaded.
- Parent pipeline task does not aggregate all step artifacts; users must inspect step details.
- Pipeline remote execution still requires enough worker slots for controller plus step tasks.

## Docs Fixes

Docs are mostly sufficient, but should stay explicit about:

- mode precedence for `Model/name`, `Model/candidates`, `Model/ensemble_*`, and `Model/search_*`
- JSON examples for candidates, params, and search space
- `Output/chunk_size` is not streaming input
- pipeline artifacts live on step tasks, not necessarily on the parent controller task
- remote pipeline needs controller plus step worker capacity
- Dataset artifact URLs must be reachable from the Agent

No additional troubleshooting document is recommended.

## Code Fixes

No immediate code fix is required for UI usability.

Potential future code improvements:

- Add concise fail-fast errors for invalid mode combinations if users combine search and ensemble.
- Consider a single `Model/search` JSON parameter only if the flat `Model/search_*` surface becomes too noisy in real operator feedback.
- Consider a UI-friendly example config snippet artifact or docs link, not a new template.

## Parameter Reduction Candidates

Do not remove parameters before more remote UI feedback. If simplification is needed later:

- Combine `Model/search_enabled`, `Model/search_method`, `Model/search_space`, and `Model/max_trials` into one `Model/search` JSON parameter.
- Combine `Model/ensemble_enabled`, `Model/ensemble_method`, and `Model/ensemble_top_k` into one `Model/ensemble` JSON parameter.
- Keep `Model/name`, `Model/params`, `Model/candidates`, and `Model/selection_metric` as separate controls because they are the main model-selection surface.

Current flat parameters are acceptable for V2 because they are discoverable in
ClearML UI and stay within the four groups.

## Artifact Naming Improvement Candidates

Current names are understandable:

- `model`
- `model_info`
- `metrics`
- `leaderboard`
- `optimization_trials`
- `optimization_summary`
- `best_params`
- `ensemble_predictions`
- `evaluation_predictions`
- `predictions`

Potential future polish:

- Keep the `predictions` artifact key stable, but include schema version in manifest, as V2.2 now does.
- Avoid renaming `model`; downstream eval/infer/pipeline handoff depends on it as the standard artifact.

## V2 UI Readiness

V2 UI status: partially ready for that historical compatibility surface.

- Ready by design/dry-run: template count, parameter grouping, artifact upload path, and fixed pipeline graph.
- Ready by existing remote evidence: V1.3 comparison, weighted ensemble, eval, infer, and weighted pipeline task execution.
- Pending before full V2 UI release: real ClearML dev runs for V2.1 optimization artifacts and V2.2 `Output/chunk_size` inference artifact review.
