# deploy

This directory contains the minimal Kubernetes runtime for ClearML Agent.

- `base/`: environment-neutral Agent Deployment, ConfigMap, PVC, and Secret example
- `overlays/dev`: dev queue and dev image tag
- `overlays/prod`: prod queue, prod image tag, and larger PVC

`secret.example.yaml` is only a template and is intentionally not included by kustomize.
Create the `clearml-credentials` Secret with your cluster secret manager or a local manifest
that is not committed.

## Build Image

```powershell
docker build -f deploy/base/Dockerfile -t registry.example.com/ml-platform/clearml-agent:dev .
docker push registry.example.com/ml-platform/clearml-agent:dev
```

Use the prod tag for production:

```powershell
docker build -f deploy/base/Dockerfile -t registry.example.com/ml-platform/clearml-agent:prod .
docker push registry.example.com/ml-platform/clearml-agent:prod
```

Replace `registry.example.com/ml-platform/clearml-agent` in the profiles and overlays with the real image repository.

This image installs `pkgs/tabular[gbm]` so ClearML New Run defaults can execute
all 10 supported models, including LightGBM, XGBoost, and CatBoost. These
packages remain out of `requirements.txt` and package required dependencies.
Synced templates also list the GBM packages for the Agent-created execution
venv, because ClearML Agent may isolate that venv from image site-packages. Set
`clearml.execution.image` in the selected profile to the pullable image URI used
by the target workers.
The base ConfigMap sets `CLEARML_AGENT_FORCE_SYSTEM_SITE_PACKAGES=true` so the
task venv can import packages installed in that execution image.

If you build a slim/custom execution image without `pkgs/tabular[gbm]`, remove
`lightgbm`, `xgboost`, and `catboost` from `Model/candidates` before running the
training pipeline.

## Create Secret

The Agent needs these values:

- `CLEARML_API_ACCESS_KEY`
- `CLEARML_API_SECRET_KEY`
- `CLEARML_API_HOST`
- `CLEARML_WEB_HOST`
- `CLEARML_FILES_HOST`

Example:

```powershell
kubectl create secret generic clearml-credentials `
  --from-literal=CLEARML_API_ACCESS_KEY=<access-key> `
  --from-literal=CLEARML_API_SECRET_KEY=<secret-key> `
  --from-literal=CLEARML_API_HOST=<api-url> `
  --from-literal=CLEARML_WEB_HOST=<web-url> `
  --from-literal=CLEARML_FILES_HOST=<files-url>
```

## Apply

Before applying, align the matching profile:

- `config/profiles/clearml-dev.yaml` for `deploy/overlays/dev`
- `config/profiles/clearml-prod.yaml` for `deploy/overlays/prod`

Check `repository`, `branch`, `working_dir`, `queue`, `execution.image`, and
`artifact_output_uri`.
The dev and prod overlays render the same Kubernetes resource names by design.
Apply only the overlay for the target environment in a given namespace. If dev
and prod must run in the same cluster, put them in separate namespaces or add an
environment-specific name prefix outside this MVP manifest set.

For ClearML Dataset inputs, make sure Dataset artifact URLs are reachable from
the Agent pod. Host-only `localhost` URLs and host filesystem paths are not valid
inside Kubernetes unless they are explicitly mounted or routed there.

Render first:

```powershell
kubectl kustomize deploy/overlays/dev
kubectl kustomize deploy/overlays/prod
```

Apply when the rendered manifest looks correct:

```powershell
kubectl apply -k deploy/overlays/dev
```

Use `deploy/overlays/prod` instead when applying production.

## Human Checklist Before Cluster Apply

- The profile `clearml.execution.image` repository and tag exist and are
  pullable by the workers.
- `clearml-credentials` exists in the target namespace and contains no placeholder values.
- The deploy queue matches the profile queue and the ClearML UI queue.
- Remote pipeline runs have enough Agent capacity: one worker slot for the controller task and one for step tasks, or separate controller and step queues.
- The profile repository URL has been changed from the placeholder to a real Git repository the Agent can clone.
- `working_dir` points to the repository root that contains `clearml/app.py`.
- `artifact_output_uri` is set if the ClearML server does not provide default artifact storage.
- Dataset artifact storage is reachable from the Agent pod; `artifact_output_uri` is not a substitute for Dataset storage reachability.
- The PVC size and storage class are acceptable for the environment.
- ClearML UI shows the Agent under Workers / Queues after the Deployment starts.
