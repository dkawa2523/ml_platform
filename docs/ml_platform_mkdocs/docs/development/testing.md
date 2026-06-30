# テストと検証

テストは、ローカルで素早く壊れ方を見つけることを優先します。ClearML サーバー接続が必要な確認は、通常の単体テストには含めません。

## 推奨レイヤー

| レイヤー | 対象 | 例 |
| --- | --- | --- |
| Unit | 小さな関数 | split、feature config、metric、model candidate |
| Smoke | Local pipeline | 小さな CSV で学習・評価・推論が通る |
| Contract light | Artifact 存在 | `leaderboard.csv`、`decision_summary.md`、`predictions.csv` |
| ClearML dry-run | Pipeline plan | テンプレート同期前の plan 確認 |
| Manual ClearML | UI / Queue / Dataset | 実サーバー上の表示と実行確認 |

## 基本コマンド

```powershell
uv run python -m pytest -q
uv run python -m ruff check .
uv run python -m compileall clearml pkgs scripts
```

## ローカル smoke

```powershell
uv run python scripts/make_sample_data.py
uv run python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set "model.candidates=[linear,ridge,lasso,elasticnet,random_forest,extra_trees,gradient_boosting]"
uv run python scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
```

## ClearML dry-run

```powershell
uv run python scripts/clearml_pipeline.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
uv run python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
```

## テストで守ること

| 観点 | 内容 |
| --- | --- |
| split | `random`、`group`、`time`、`fixed` が期待通り分割される |
| data quality | 欠損、重複、リーク疑いが軽量に検出される |
| model suite | `fast`、`interpretable`、`tree`、`custom` の候補が正しい |
| evaluate | `leaderboard` と `decision_summary` が出る |
| inference | schema check と slim な `predictions.csv` が出る |
| ClearML boundary | `pkgs/core` と `pkgs/tabular` が ClearML SDK に依存しない |

## 避けること

- 単体テストで ClearML サーバー接続を必須にする。
- 巨大な golden file を追加する。
- 入力 CSV 全体の snapshot を固定する。
- plot 画像のピクセル比較を行う。
- テストのためだけに本体コードを複雑化する。

## Manual ClearML 確認

実サーバーでは、以下を人手で確認します。

- `template/tabular_train_pipeline` の New Run に Basic 項目が表示される。
- PipelineController が controller queue で動く。
- Stage が stage queue で動く。
- Dataset ID と dataset file が解決できる。
- `evaluate_models/decision_summary.md` が読める。
- `template/tabular_infer` で `schema_check_summary` と `predictions.csv` が出る。
