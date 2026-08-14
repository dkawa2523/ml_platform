# clearml

ClearML-specific code lives here. Training, preprocessing, evaluation, ensemble,
and inference logic belongs in `pkgs/tabular`.

Files:

```text
app.py                  task entrypoint
adapter.py              ClearML Task, Dataset, StorageManager, and Logger wrapper
execution.py            immutable repository revision, image, and Python runtime
support.py              shared ClearML task/logger helpers
param_bindings.py       manifest ParameterSpec -> config binding
param_defaults.py       config -> ClearML runtime parameter defaults
param_transport.py      ClearML parameter serialization/coercion
param_apply.py          ClearML runtime parameters -> nested config
source_resolution.py    inference source task and artifact resolution
reports.py              RunResult reporting orchestration
reporting_scalars.py    scalar extraction from metrics artifacts and tables
reporting_targets.py    table/plot report names and duplicate suppression
pipeline_params.py      Pipeline New Run defaults and parameter normalization
pipeline_steps.py       Domain plan artifact wiring and ClearML step rendering
pipeline_plan.py        Training plan orchestration and dry-run presentation
pipeline_controller.py  PipelineController draft sync and run orchestration
pipelines.py            direct pipeline entrypoint
templates.py            template sync
_entrypoint_bootstrap.py
                        local/remote entrypoint import bootstrap
```

Current sync targets:

- `template/tabular_train_pipeline`
- `template/tabular_infer`
- `internal/tabular_stage`

The stage template is internal and reused for every pipeline step. Do not create
model-specific, ensemble-specific, or dataset-specific templates.

Profile-managed project layout:

```text
templates    MLPlatform/<Env>/Templates/Tabular
pipelines    MLPlatform/<Env>/Pipelines/Tabular
preprocess   MLPlatform/<Env>/Runs/Tabular/Preprocess
train        MLPlatform/<Env>/Runs/Tabular/Train
ensemble     MLPlatform/<Env>/Runs/Tabular/Ensemble
evaluate     MLPlatform/<Env>/Runs/Tabular/Evaluate
infer        MLPlatform/<Env>/Runs/Tabular/Infer
experiments  MLPlatform/<Env>/Experiments/Tabular
```

Tags include `domain:tabular`, `run_type:*`, `user_facing:true`,
`internal:true`, `stage:<stage_name>`, `model:<model_name>`, and
`ensemble:<method>`.

The training template pre-fills all 10 supported models. Template sync resolves
`clearml.execution.revision` once and pins the same commit, image, and Python
binary on the PipelineController, every stage template, and inference template.
GBM packages are installed in the task venv; the Agent image does not contain a
second copy of this repository.

For remote training, start the PipelineController on `clearml.controller_queue`
and let stage tasks run on `clearml.stage_queue`. Using the same one-worker queue
for both can leave `preprocess_features` queued while the controller occupies
the only worker slot.

Because this operations directory is named `clearml`, code here must import the
official SDK through `adapter.import_clearml_sdk()` or
`adapter.import_clearml_symbol()`. Do not import the SDK directly from new
runtime code.

Runtime parameter keys are declared in `ml_platform_tabular.manifest` as
`ParameterSpec`s. Keep defaults, coercion, config application, and pipeline
overrides derived through `param_bindings.py` rather than adding parallel key
lists.

Shared ClearML Task and Logger mechanics belong in `support.py`; entrypoints
and sync code should keep only product-specific decisions. Avoid adding thin
re-export modules or one-class files unless they remove substantial complexity.
