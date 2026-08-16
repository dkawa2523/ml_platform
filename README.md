# ml_platform

ClearML UI から扱いやすい、tabular scalar regression 向けの学習・評価・推論基盤です。

目的は、モデル比較と推論運用に必要な情報を ClearML 上で見やすく出しつつ、core/tabular パッケージは ClearML に依存しない状態を保つことです。

## 製品フロー

学習は stage-based pipeline です。

```text
preprocess_features -> train_<model>* -> build_ensemble_<method>* -> evaluate_models
```

Package stage 名は `preprocess_features`、`train_model`、`build_ensemble`、`evaluate_models` です。ClearML Pipeline 上では見分けやすさのため、step label と task name に `train_<model>` や `build_ensemble_<method>` の suffix を付けます。

`preprocess_features` では、欠損、重複、ID重複、高カーディナリティ列、リーク疑いの列名などを軽量に確認できます。警告は失敗扱いにせず、致命的な入力不備だけをエラーにします。

学習後は `evaluate_models/best_model.json` と `evaluate_models/leaderboard.csv` を確認してください。推論タスクに設定する `Model/source_type`、`Model/source_task_id`、`Model/model_selector` は `best_model.json` に集約されています。

推論は学習 Pipeline とは別の user-facing task です。

```text
tabular_infer_template -> predictions.csv
```

推論では schema check を行い、`predictions.csv` は `row_index`、存在する ID 列、`prediction` を中心にした slim な出力にします。入力特徴量を丸ごとコピーしません。

主要なタスク設定は以下です。

- `config/tasks/tabular_pipeline.yaml`
- `config/tasks/tabular_stage.yaml`
- `config/tasks/tabular_infer.yaml`

現在の製品面では、互換専用の `tabular_train` / `tabular_eval` タスクや将来用 1D output タスクは持ちません。

## 対応モデル

対応モデル名:

```text
linear
ridge
lasso
elasticnet
random_forest
extra_trees
gradient_boosting
lightgbm
xgboost
catboost
```

`lightgbm`、`xgboost`、`catboost` は optional dependency です。ローカルの軽量環境では標準インストールに含めず、ClearML remote template は profile の `clearml.execution.requirements_file` が示す固定 lock から Agent 側の実行 venv を作ります。Server、Queue、image、lock、model-source policy は環境 profile ごとに差し替えられます。

ローカルで 10 モデルすべてを動かす場合は、事前に `pkgs/tabular[gbm]` 相当の依存を入れてください。軽量に試す場合は `Model/candidates` や `Basic/model_suite=fast` で GBM 系を外します。

対象外:

```text
knn
svr
mlp
gaussian_process
tabpfn
```

## ローカル実行

軽量な開発環境を作ります。

```powershell
uv venv .venv
.\.venv\Scripts\activate
uv sync --group dev
```

サンプルデータを作成し、GBM 系を外した軽量候補で学習します。

```powershell
uv run python scripts/make_sample_data.py
uv run python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set "model.candidates=[linear,ridge,lasso,elasticnet,random_forest,extra_trees,gradient_boosting]"
```

直近の学習結果を使ってローカル推論します。

```powershell
uv run python scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
```

テスト:

```powershell
uv run --group quality nox -s quality-fast
```

## ClearML 実行

テンプレートの dry-run:

```powershell
uv run python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
```

ClearML 上のテンプレート更新:

```powershell
uv run python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml
```

ユーザー向けテンプレート:

- `template/tabular_train_pipeline`
- `template/tabular_infer`

内部テンプレート:

- `internal/tabular_stage`

ClearML Pipeline tab から最初に使うのは `template/tabular_train_pipeline` です。`internal/tabular_stage` は PipelineController が各 stage で使う内部用なので、通常ユーザーが直接 clone しません。

初回実行では、主に以下を設定します。

- `Input/clearml_dataset_id`
- `Input/dataset_file`
- `Input/target_column`
- `Basic/model_suite=default|fast|interpretable|tree|gbm|custom`
- `Basic/quality_mode=fast|standard|quality`
- `Basic/use_ensemble=true|false`

`Basic/model_suite` は JSON を編集せずに候補モデルを切り替えるための入口です。

- `default`: 全 10 モデル
- `fast`: optional GBM 系を外す
- `interpretable`: 線形系のみ
- `tree`: sklearn tree ensemble 系のみ
- `gbm`: LightGBM / XGBoost / CatBoost
- `custom`: `Model/candidates` を直接使う

`Basic/quality_mode` は HPO ではありません。固定プリセットとして tree/GBM 系の estimator 数を少し変えるだけです。

詳細制御用の JSON パラメータは残しています。

- `Model/candidates`
- `Model/model_params_by_name`
- `Features/drop_columns`
- `Features/passthrough_columns`
- `Model/ensemble_enabled`

`Model/ensemble_enabled` を明示した場合は、`Basic/use_ensemble` より優先されます。

Pipeline dry-run:

```powershell
uv run python scripts/clearml_pipeline.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
```

## MkDocs ドキュメント

MkDocs 版のドキュメントは以下にあります。

```text
docs/ml_platform_mkdocs/
```

docs 用依存をインストールします。

```powershell
uv sync --group docs
```

ローカルでプレビュー起動します。

```powershell
uv run --group docs python -m mkdocs serve --config-file docs\ml_platform_mkdocs\mkdocs.yml
```

起動後、ブラウザで以下を開きます。

```text
http://127.0.0.1:8000/
```

HTML をビルドする場合:

```powershell
uv run --group docs python -m mkdocs build --config-file docs\ml_platform_mkdocs\mkdocs.yml --strict
```

生成された HTML は `docs/ml_platform_mkdocs/site/` に出力されます。`site/` は生成物なので、通常はコミットしません。

## 境界と方針

- `pkgs/core` と `pkgs/tabular` は ClearML SDK に依存しません。
- ClearML SDK を使う処理は `clearml/` 配下に閉じます。
- ローカル運用者は `scripts/` 経由の entrypoint を使います。
- remote ClearML template は互換性のため `clearml/app.py` と `clearml/pipelines.py` を直接実行します。
- モデル別、データセット別、アンサンブル別のテンプレートは増やしません。
- legacy repo tree はこのリポジトリにコピーしません。
- HPO、Model Registry、drift monitoring、Task Registry、external valid file、kfold は future 扱いです。

## 関連ドキュメント

- `AGENTS.md`: 開発方針
- `docs/SPEC.md`: 現在の製品仕様
- `docs/CLEARML_UI_SPEC.md`: ClearML UI の仕様
- `docs/ROADMAP.md`: 現在範囲と future 範囲
- `docs/CODEX_HANDOFF.md`: 運用引き継ぎ
- `docs/ml_platform_mkdocs/README_DOCS.md`: MkDocs ドキュメントの補足
- `verification/README.md`: 検証記録
