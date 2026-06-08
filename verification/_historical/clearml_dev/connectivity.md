# ClearML Dev Connectivity Check

## Run Metadata

- Date: 2026-05-24 15:47 JST
- Commit: `3773e03`
- ClearML config path: `C:\Users\user\clearml.conf`
- Secrets: not stored

## Configured Endpoints

| Endpoint | Value |
| --- | --- |
| Web server | `http://localhost:8080` |
| API server | `http://localhost:8008` |
| Files server | `http://localhost:8081` |

## Result

ClearML dev server became reachable after Docker Desktop and the existing ClearML server containers were running.

Observed containers:

- `clearml-webserver`
- `clearml-apiserver`
- `clearml-fileserver`
- `clearml-redis`
- `clearml-elastic`
- `clearml-mongo`
- `clearml-default`
- `clearml-controller`
- `clearml-heavy-model`

## Agent Notes

- The active dev queue was `default`.
- The existing `clearml-default` Agent could execute train/eval/infer tasks.
- Remote pipeline execution required more than one worker on the queue because the pipeline controller occupies one worker while step tasks need another worker.
- For this dev verification, additional `default` workers were started in the existing Agent container. No task was deleted, aborted, archived, or reset.

## Dataset Reachability

A host-created ClearML Dataset stored `localhost` file URLs and was not reachable from inside the Agent container. The successful verification used a Docker-network dataset whose artifact URLs resolve from the Agent environment.

## Decision

Connectivity was sufficient for:

- template sync
- train/eval/infer task clone-run
- ridge and linear pipeline execution

For production-like deployment, verify the Agent image, queue capacity, and artifact storage from the actual cluster network.
