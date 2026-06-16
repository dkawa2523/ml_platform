# Local 実行

Local 実行は、ClearML に依存せず、手元のデータと設定だけで処理の全体像を確認するための入口です。モデル追加や前処理改修の検証にも使います。

## サンプルデータ作成

```powershell
python scripts/make_sample_data.py
```

標準では次のようなサンプルファイルが作成されます。

| ファイル | 用途 |
| --- | --- |
| `data/sample_train.csv` | 学習用データ |
| `data/sample_infer.csv` | 推論用データ |

## 学習 Pipeline を実行する

GBM 系 optional dependency を入れていない環境では、依存不要モデルだけで実行します。

```powershell
python scripts/local_run.py \
  --task config/tasks/tabular_pipeline.yaml \
  --profile config/profiles/local.yaml \
  --set "model.candidates=[linear,ridge,lasso,elasticnet,random_forest,extra_trees,gradient_boosting]"
```

PowerShell では 1 行で実行しても構いません。

```powershell
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set "model.candidates=[linear,ridge,lasso,elasticnet,random_forest,extra_trees,gradient_boosting]"
```

## 推論を実行する

学習後、標準設定の推論 Task を Local で実行できます。

```powershell
python scripts/local_run.py --task config/tasks/tabular_infer.yaml --profile config/profiles/local.yaml
```

`tabular_infer.yaml` の `model.source_type` が `local_path` の場合、明示的な `local_model_path` がなければ `outputs/latest_training_pipeline` などの最新学習成果物からモデル解決を試みます。

## 出力先

Local では `outputs` 配下に実行結果が保存されます。典型的には次のような構成になります。

```text
outputs/
  tabular_training_pipeline_.../
    preprocess_features/
    train_ridge/
    train_random_forest/
    build_ensemble_mean_topk/
    evaluate_models/
  latest_training_pipeline -> tabular_training_pipeline_...
  latest -> ...
```

## 実行時 override

`--set` は YAML 設定を一時的に上書きします。

| 例 | 意味 |
| --- | --- |
| `--set "data.local_path=data/my_train.csv"` | 学習データを変更する |
| `--set "data.target_column=price"` | 目的変数を `price` にする |
| `--set "split.method=time"` | 時系列 holdout に変更する |
| `--set "split.time_column=date"` | 時系列分割に使う列を指定する |
| `--set "features.categorical_encoder=drop"` | カテゴリ列を使わない |
| `--set "model.selection_metric=mae"` | モデル選択指標を MAE にする |

## Local 実行の確認ポイント

| 確認対象 | 見るファイル |
| --- | --- |
| データ品質 | `preprocess_features/data_quality_summary.json`、`data_quality_warnings.csv` |
| 前処理内容 | `preprocess_features/feature_spec.json` |
| 各モデル指標 | `train_<model>/metrics.json`、`metrics_table.csv` |
| 評価結果 | `evaluate_models/leaderboard.csv` |
| 推論すべきモデル | `evaluate_models/decision_summary.md` |
| 推論結果 | `predictions.csv` |
| 推論スキーマ | `schema_check_summary.csv/json` |

## テスト

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

CI や Linux shell では次のように実行します。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q
```
