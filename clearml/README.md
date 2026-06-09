# clearml

ClearML operational code lives here.

Responsibilities:

- task entrypoint
- ClearML Task, Dataset, StorageManager, and Logger adapter
- UI parameter mapping
- RunResult reporting
- template task sync
- stage-based training PipelineController definition

Do not put tabular training, evaluation, inference, or preprocessing logic here. That belongs in `pkgs/tabular`.
Use `docs/SPEC.md` for product scope and `docs/CLEARML_UI_SPEC.md` for
ClearML screen-level expectations.

Files:

```text
app.py        ClearML task entrypoint
adapter.py    Task, Dataset, parameter, artifact path wrapper
reports.py    RunResult to ClearML reporting
templates.py  template task and Pipeline-tab draft sync
pipelines.py  stage-based training pipeline controller
```

`tabular_stage_template` is an internal stage task for PipelineController graphs.
The default sync targets are `tabular_train_pipeline_template`,
`tabular_infer_template`, and `tabular_stage_template`. Deprecated
`tabular_train_template`, `tabular_eval_template`, `tabular_pipeline_template`,
and `tabular_train_full_*` entries are deprecated or sync-excluded; they are not
current user-facing templates.
ClearML display names are `template/tabular_train_pipeline`,
`template/tabular_infer`, and `internal/tabular_stage`.

Profiles define the ClearML project layout:

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

Synced templates and runs use tags such as `domain:tabular`,
`run_type:template`, `run_type:pipeline`, `run_type:stage`, `run_type:task`,
`user_facing:true`, `internal:true`, `stage:<stage_name>`, and
`model:<model_name>`. Ensemble method stages also use `ensemble:<method>`.

Old ClearML tasks and runs may remain visible until manually archived on the
server. Sync creates or updates only the current canonical entries.

For remote training runs, open `template/tabular_train_pipeline` in the Pipeline
tab and set `Input/clearml_dataset_id`, `Input/dataset_file`, and
`Input/target_column`. `Input/local_path` is only valid when the Agent can see
the same path inside its container or mounted volume.
