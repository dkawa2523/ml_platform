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

Replace `registry.example.com/ml-platform/clearml-agent` in the overlays with the real image repository.

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

Check `repository`, `branch`, `working_dir`, `queue`, and `artifact_output_uri`.
The dev and prod overlays render the same Kubernetes resource names by design.
Apply only the overlay for the target environment in a given namespace. If dev
and prod must run in the same cluster, put them in separate namespaces or add an
environment-specific name prefix outside this MVP manifest set.

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

- The image repository and tag exist and are pullable by the cluster.
- `clearml-credentials` exists in the target namespace and contains no placeholder values.
- The deploy queue matches the profile queue and the ClearML UI queue.
- The profile repository URL has been changed from the placeholder to a real Git repository the Agent can clone.
- `working_dir` points to the repository root that contains `clearml/app.py`.
- `artifact_output_uri` is set if the ClearML server does not provide default artifact storage.
- The PVC size and storage class are acceptable for the environment.
- ClearML UI shows the Agent under Workers / Queues after the Deployment starts.
