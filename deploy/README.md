# deploy

ClearML Agentの起動定義です。`controller`はPipelineControllerだけを、
`worker`は学習・評価・推論ステップを実行します。両者を分けることで、
controllerが唯一のworker枠を占有する待ち状態を避けます。

## 実行イメージ

```powershell
docker build -f deploy/base/Dockerfile -t ml-platform-clearml-agent:dev .
```

このイメージにはAgentとシステムライブラリだけを入れます。リポジトリは
template同期時に固定されたcommitから各Taskが取得し、Python依存はTaskの
venvへ導入します。

## ローカルDocker

`deploy/local/.env.example`を`deploy/local/.env`へコピーし、ClearMLの認証情報を
設定します。`.env`はGit管理対象外です。

```powershell
docker compose --env-file deploy/local/.env -f deploy/local/compose.yaml up -d --force-recreate
```

Agent homeをvolume化していないため、`--force-recreate`で古いvenv/cacheも破棄
されます。既存の手動起動Agentがある場合は、同じqueueを重複監視しないよう、
切替時間を決めてから置き換えてください。

## Kubernetes

`base/`にはcontroller、worker、出力PVCがあります。overlayは次を選びます。

- `overlays/dev`: worker queue `default`、dev image
- `overlays/prod`: worker queue `cpu`、prod image、100 GiB PVC

Secretはリポジトリに保存せず、`base/secret.example.yaml`と同じ5項目を
`clearml-credentials`として作成します。適用前にrender結果を確認します。

```powershell
kubectl kustomize deploy/overlays/dev
kubectl apply -k deploy/overlays/dev
```

productionでは、registryへpushした不変digestを同じ値で2か所に設定します。

1. `ML_PLATFORM_CLEARML_IMAGE`（`clearml-prod.yaml`のtemplate同期用）
2. `deploy/overlays/prod/kustomization.yaml`のimage（Agent Deployment用）

また、profileのrepository/revisionがworkerから取得でき、ClearMLのAPI・Web・
Files各URLがworkerから到達できることを確認してください。
