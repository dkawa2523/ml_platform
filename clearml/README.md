# clearml

ClearML-specific code lives here. Training, preprocessing, evaluation, ensemble,
and inference logic belongs in `pkgs/tabular`.

Files:

```text
app.py        task entrypoint
adapter.py    ClearML Task, Dataset, StorageManager, Logger wrapper
_entrypoint_bootstrap.py
              local/remote entrypoint import bootstrap
reports.py    RunResult -> ClearML Scalars, Tables, Plots, Artifacts
templates.py  template sync and Pipeline-tab draft sync
pipelines.py  stage-based training PipelineController
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

The training template pre-fills all 10 supported models. Templates reference
`clearml.execution.image` from the selected profile and add GBM packages to the
remote execution venv. Remove GBM names only for slim/custom runs that do not
install those packages.

For remote training, start the PipelineController on `clearml.controller_queue`
and let stage tasks run on `clearml.stage_queue`. Using the same one-worker queue
for both can leave `preprocess_features` queued while the controller occupies
the only worker slot.

Because this operations directory is named `clearml`, code here must import the
official SDK through `adapter.import_clearml_sdk()` or
`adapter.import_clearml_symbol()`. Do not import the SDK directly from new
runtime code.
