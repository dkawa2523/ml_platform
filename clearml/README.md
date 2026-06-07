# clearml

ClearML operational code lives here.

Responsibilities:

- task entrypoint
- ClearML Task, Dataset, StorageManager, and Logger adapter
- UI parameter mapping
- RunResult reporting
- template task sync
- stage-based training and optimization PipelineController definition

Do not put tabular training, evaluation, inference, or preprocessing logic here. That belongs in `pkgs/tabular`.

Files:

```text
app.py        ClearML task entrypoint
adapter.py    Task, Dataset, parameter, artifact path wrapper
reports.py    RunResult to ClearML reporting
templates.py  template task and Pipeline-tab draft sync
pipelines.py  stage-based training and optimization pipeline controller
```

`tabular_stage_template` is an internal stage task for PipelineController graphs.
Deprecated `tabular_train_template`, `tabular_eval_template`, and
`tabular_pipeline_template` are legacy compatibility entries, not the current
user-facing training pipeline.
