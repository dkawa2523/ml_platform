# 成果物一覧

この章では、Stage ごとに生成される主要な成果物を整理します。実際の出力は設定やモデルにより一部変わります。

## preprocess_features

| 種別 | ファイル | 内容 |
| --- | --- | --- |
| Artifact | `preprocess_bundle.joblib` | 前処理 transformer と特徴量情報 |
| Artifact | `feature_spec.json` | 学習時特徴量仕様 |
| Artifact | `target_sources.json` | 複数target入力時の正規化済みsource定義 |
| Artifact | `data_quality_summary.json` | データ品質概要 |
| Table | `missing_rate_by_column.csv` | 欠損率 |
| Table | `data_quality_warnings.csv` | 警告一覧 |
| Table | `processed_train.csv` | 分割後 train raw frame |
| Table | `processed_valid.csv` | 分割後 valid raw frame |
| Plot | `missing_rate_by_column_bar.png` | 欠損率 bar |

## train_<model>

ClearML step label では `train_<model>` と表示しますが、package stage key は `train_model` です。

| 種別 | ファイル | 内容 |
| --- | --- | --- |
| Artifact | `model.joblib` | 学習済み estimator |
| Artifact | `model_info.json` | モデル情報、特徴量、パラメータ |
| Artifact | `metrics.json` | 指標 JSON |
| Table | `metrics_table.csv` | target別と`__macro__`のtidy指標 table |
| Table | `selection_predictions.csv` | model selection holdout 予測 |

## build_ensemble_<method>

ClearML step label では `build_ensemble_<method>` と表示しますが、package stage key は `build_ensemble` です。

| 種別 | ファイル | 内容 |
| --- | --- | --- |
| Artifact | `model_<method>.joblib` | アンサンブル estimator |
| Artifact | `model_info_<method>.json` | モデル情報、構成モデル、重み |
| Artifact | `metrics_<method>.json` | アンサンブル指標 |
| Table | `selection_predictions_<method>.csv` | model selection holdout 予測 |
| Table | `ensemble_members_<method>.csv` | 構成モデルと重み |

## evaluate_models

| 種別 | ファイル | 内容 |
| --- | --- | --- |
| Artifact/Table | `leaderboard.csv` | 全候補比較 |
| Artifact | `best_model.json` | 最良候補と推奨推論設定 |
| Artifact | `best_model.joblib` | 最良モデル実体 |
| Artifact | `model_info.json` | 推論に必要なモデル情報と特徴量契約 |
| Artifact | `metrics.json` | 最良候補の指標 |
| Table | `evaluation_predictions.csv` | 推奨モデルの予測 |
| Artifact | `manifest.json` | 出力一覧 |

## tabular_infer

| 種別 | ファイル | 内容 |
| --- | --- | --- |
| Table | `predictions.csv` | 予測結果。複数targetではtarget・座標・source rowを保持 |
| Artifact/Table | `schema_check_summary.json/csv` | 入力スキーマ検証 |
| Table | `prediction_summary.csv` | 予測値集計 |
| Table | `prediction_preview.csv` | 予測先頭行 |
| Plot | `prediction_distribution.png` | scalar予測分布。単位が異なる複数targetでは生成しない |
| Artifact | `manifest.json` | 出力一覧 |

## manifest の役割

各 RunResult は `manifest.json` を持ち、設定、メトリクス、Artifacts、Tables、Plots をまとめます。Local 実行では成果物の場所を追いやすくし、ClearML 実行では Artifact 一覧の補助になります。
