# ClearML entrypoints

This directory contains only the direct file paths already stored in synced
ClearML templates:

- `app.py`: stage and inference entrypoint
- `pipelines.py`: training pipeline entrypoint
- `templates.py`: template-sync compatibility import
- `_entrypoint_bootstrap.py`: exposes the three workspace package source roots

The implementation lives in `pkgs/clearml/src/ml_platform_clearml`. Training,
preprocessing, evaluation, ensemble, and inference behavior remains in
`pkgs/tabular`.

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
Task dependencies come from the exact lock selected by
`clearml.execution.requirements_file`; the Agent image does not contain a second
copy of this repository.

Agent topology is environment configuration, not application code. To deploy to
another server or worker pool, copy a profile and change `projects`, queues,
`execution.repository`, `revision`, `image`, `python_binary`,
`requirements_file`, and Dataset defaults. `clearml.model_source` independently
controls which statuses, tags, run types, and project keys inference may trust.
Regenerate the task lock deliberately with:

```text
uv export --frozen --no-dev --extra clearml --extra gbm --no-emit-project --no-emit-workspace --no-hashes --output-file config/requirements/clearml-agent.lock
```

For remote training, start the PipelineController on `clearml.controller_queue`
and let stage tasks run on `clearml.stage_queue`. Using the same one-worker queue
for both can leave `preprocess_features` queued while the controller occupies
the only worker slot.

Runtime parameter keys are declared in `ml_platform_tabular.manifest` as
`ParameterSpec`s. Defaults come from task/profile configuration; do not duplicate
them in the manifest.

New ClearML runtime behavior belongs in the `ml_platform_clearml` package, not
in these wrappers.
