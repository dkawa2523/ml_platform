# clearml

ClearML operational code lives here.

Responsibilities:

- task entrypoint
- ClearML Task, Dataset, StorageManager, and Logger adapter
- UI parameter mapping
- RunResult reporting
- template task sync
- minimal PipelineController definition

Do not put tabular training, evaluation, inference, or preprocessing logic here. That belongs in `pkgs/tabular`.

Files:

```text
app.py        ClearML task entrypoint
adapter.py    Task, Dataset, parameter, artifact path wrapper
reports.py    RunResult to ClearML reporting
templates.py  template task sync
pipelines.py  fixed train -> eval -> infer PipelineController
```
