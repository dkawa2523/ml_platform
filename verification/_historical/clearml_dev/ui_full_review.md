# ClearML UI Review

## Scope

Codex did not have direct browser control for the ClearML UI. Review evidence is based on ClearML task URLs and SDK metadata. No screenshots were stored.

## Findings

- Template count is fixed at four: train, eval, infer, pipeline.
- UI parameter groups stay within `Input`, `Run`, `Model`, and `Output`.
- `Run/queue` is not exposed as a UI parameter. Queue remains profile and Agent configuration.
- Train and eval metrics are reported under `metrics`.
- Train artifacts include `model`, `model_info`, `metrics`, `manifest`, and `validation_predictions`.
- Eval artifacts include `metrics`, `manifest`, and `evaluation_predictions`.
- Infer artifacts include `predictions` and `manifest`.
- Pipeline step names are simple: `train`, `eval`, `infer`.
- Pipeline eval and infer steps show the train model artifact URL in `Model/artifact_path`.

## UI Issues

- A remote pipeline needs at least two workers on the execution queue, because the controller occupies one worker while steps need another. This is an operations note, not a code blocker.
- When switching a train template from `ridge` to `linear`, ClearML may still display a nested residual parameter such as `Model/params/alpha` from the base template. The runner uses `Model/params` and the run succeeds, but the UI can look slightly noisy.
- A ClearML Dataset created from the host can store `localhost` file URLs that are not reachable from an Agent container. The dev verification used a dataset created from the Docker network so artifact URLs resolve inside the Agent.

## Product Evaluation

v1-ready for the MVP ClearML flow, with two operational notes:

- Run the controller and steps with enough Agent capacity.
- Create or register datasets using URLs reachable by the Agent environment.
