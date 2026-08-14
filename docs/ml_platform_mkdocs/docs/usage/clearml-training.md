# ClearML 学習

ClearML 学習は、UI から Dataset と設定を選び、Stage-based Pipeline として複数モデル比較を実行する運用モードです。コードを読まない利用者でも、Basic パラメータを中心に設定すれば実行できます。

## 学習 Pipeline の入口

ClearML UI では、Pipeline tab から `template/tabular_train_pipeline` を選び、New Run を作成します。

```mermaid
graph LR
  A[Pipeline tab] --> B[template/tabular_train_pipeline]
  B --> C[New Run]
  C --> D[Basic parameters]
  D --> E[Run on controller queue]
  E --> F[Stage tasks]
```

## 最初に触る Basic パラメータ

| パラメータ | 推奨値 | 説明 |
| --- | --- | --- |
| `Basic/model_suite` | `default` または `fast` | 候補モデルのセットを選ぶ |
| `Basic/quality_mode` | `standard` | 固定パラメータのサイズ感を選ぶ。HPO ではない |
| `Basic/use_ensemble` | `true` | アンサンブル Stage を作るか |
| `Basic/notes` | 任意 | Run の目的やデータ条件をメモする |

`Basic/model_suite=fast` は optional dependency を避けるため、初回確認や worker 環境が不明な場合に適しています。

## データ入力

Remote 実行では、まず `Input/clearml_dataset_id` を設定します。データ形式に
応じて、残りの入力は次のどちらか一方を使います。

| データ形式 | 設定するパラメータ |
| --- | --- |
| 1 ファイルのスカラー目的変数 | `Input/dataset_file` と `Input/target_column` |
| 目的変数ごとに分かれた表 | `Input/source_manifest` |

`Input/source_manifest` は Dataset ルートからの相対パスです。複数表を使う場合、
`Input/dataset_file` と `Input/target_column` は空にします。各表の列名は
manifest で共通の座標名と値に対応付けるため、元ファイル間で同じである必要は
ありません。

`Input/local_path` は Local または Agent 上にマウントされたファイルを使う場合のみ指定します。通常の Remote 実行では空にします。

## 分割設定

| `Split/method` | 必須追加項目 | 使いどころ |
| --- | --- | --- |
| `random` | なし | 一般的なランダム holdout |
| `group` | `Split/group_column` | 同じ設備・顧客・店舗などを train/valid に跨がせたくない場合 |
| `time` | `Split/time_column` | 過去で学習し、最新期間で評価したい場合 |
| `fixed` | `Split/valid_filter_column`, `Split/valid_filter_value` | 既に validation flag がある場合 |

K-fold、外部 validation file、nested CV は現行 UI には出しません。単一 holdout の意味を明確にした上で運用します。

## 詳細パラメータ

Basic で足りない場合は、詳細項目を編集します。

| 領域 | 代表項目 | 注意 |
| --- | --- | --- |
| Features | `Features/drop_columns`, `Features/passthrough_columns` | JSON 配列またはカンマ区切り。列名ミスに注意 |
| Model | `Model/candidates` | `custom` 相当の直接指定。モデル名は対応表を参照 |
| Model params | `Model/model_params_by_name` | 明示した場合は `Basic/quality_mode` より優先 |
| Ensemble | `Model/ensemble_methods`, `Model/ensemble_top_k` | `mean_topk`, `weighted`, `median` を指定可能 |
| Output | `Output/upload_plots` | Plot 画像の ClearML アップロードを抑制したい場合に `false` |

乱数seedは `Run/seed` だけを使用します。モデル別パラメータ内の
`random_state` / `random_seed` はstage生成時に `Run/seed` へ統一されます。

## 実行後に見る場所

| Stage | Project | 最初に見るもの |
| --- | --- | --- |
| `preprocess_features` | `Runs/Tabular/Preprocess` | `data_quality_summary`, `data_quality_warnings` |
| `train_<model>` | `Runs/Tabular/Train` | `metrics`, `validation_predictions` |
| `build_ensemble_<method>` | `Runs/Tabular/Ensemble` | ensemble metrics、members |
| `evaluate_models` | `Runs/Tabular/Evaluate` | `best_model.json`, `leaderboard` |

表の `train_<model>` と `build_ensemble_<method>` は ClearML step label です。実行設定の `Run/stage` は `train_model` または `build_ensemble` を使います。

## 成功判断

学習 Pipeline の成功だけでなく、以下を確認してから推論に進みます。

- `preprocess_features` に重大な data quality warning がない。
- `evaluate_models/best_model.json` で推奨 `source_task_id` と `model_selector` を確認した。
- `evaluate_models/leaderboard` で候補比較が妥当である。
- 推論入力データが、学習時の `feature_spec.json` と整合しそうである。
