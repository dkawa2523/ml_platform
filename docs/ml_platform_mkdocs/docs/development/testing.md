# テストと検証

テストは、処理本体の回帰を防ぎつつ、過度に重くならないことを重視します。ClearML サーバーへの実接続を必要とするテストは、通常の単体テストには含めません。

## 推奨テスト階層

| 階層 | 対象 | 例 |
| --- | --- | --- |
| Unit | 小さな関数 | split、feature config、metric、model candidate |
| Smoke | Local pipeline | 小さい CSV で学習・推論が通ること |
| Contract light | Artifact 存在 | `leaderboard.csv`、`decision_summary.md`、`predictions.csv` |
| ClearML dry-run | Pipeline plan | テンプレート同期前の plan 確認 |
| Manual ClearML | UI/Queue/Dataset | 実サーバー上の動作確認 |

## 実行コマンド

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

Linux / macOS:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q
```

## テストで守るべきこと

| 観点 | 内容 |
| --- | --- |
| split | `random`, `group`, `time`, `fixed` が期待通り分かれる |
| data quality | 欠損、重複、リーク疑いが検出される |
| model suite | `fast`, `interpretable`, `tree`, `custom` の候補が正しい |
| evaluate | `leaderboard` と `decision_summary` が出る |
| inference | schema error/warning と slim predictions が正しい |
| ClearML boundary | `pkgs/core` と `pkgs/tabular` が ClearML SDK に依存しない |

## テストで避けること

- ClearML サーバー接続を必須にする。
- 巨大な golden file を追加する。
- 全 CSV の完全 snapshot を固定する。
- Plot 画像のピクセル比較を行う。
- テストのためだけに本体コードを複雑化する。

## ClearML dry-run

テンプレートや Pipeline の構成を変更した場合は、次を確認します。

```powershell
python clearml/pipelines.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/clearml-dev.yaml --dry-run
python scripts/sync_clearml_templates.py --profile config/profiles/clearml-dev.yaml --dry-run
```

## Manual ClearML 検証

実 ClearML 環境では、次を人手で確認します。

- `template/tabular_train_pipeline` の New Run に Basic 項目が出ている。
- PipelineController が controller queue で動く。
- Stage が stage queue で動く。
- Dataset ID と dataset file が解決できる。
- `evaluate_models/decision_summary.md` が読める。
- `template/tabular_infer` で `schema_check_summary` が出る。
