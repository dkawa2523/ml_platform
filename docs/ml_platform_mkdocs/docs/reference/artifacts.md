# 成果物一覧

この章では、Stage ごとに生成される主要な成果物を整理します。実際の出力は設定やモデルにより一部変わります。

## preprocess_features

| 種別 | ファイル | 内容 |
| --- | --- | --- |
| Artifact | `preprocess_bundle.joblib` | 前処理 transformer と特徴量情報 |
| Artifact | `feature_spec.json` | 学習時特徴量仕様 |
| Artifact | `feature_summary.json` | 前処理概要 |
| Artifact | `data_quality_summary.json` | データ品質概要 |
| Table | `feature_summary_table.csv` | 特徴量概要 table |
| Table | `missing_rate_by_column.csv` | 欠損率 |
| Table | `feature_type_counts.csv` | 型別カウント |
| Table | `data_quality_summary_table.csv` | データ品質 table |
| Table | `data_quality_warnings.csv` | 警告一覧 |
| Table | `processed_train.csv` | 分割後 train raw frame |
| Table | `processed_valid.csv` | 分割後 valid raw frame |
| Table | `train_features.csv` | 変換後 train features |
| Table | `valid_features.csv` | 変換後 valid features |
| Plot | `missing_rate_by_column_bar.png` | 欠損率 bar |

## train_<model>

| 種別 | ファイル | 内容 |
| --- | --- | --- |
| Artifact | `model.joblib` | 学習済み estimator |
| Artifact | `model_info.json` | モデル情報、特徴量、パラメータ |
| Artifact | `metrics.json` | 指標 JSON |
| Table | `metrics_table.csv` | 指標 table |
| Table | `validation_predictions.csv` | validation 予測 |
| Table | `feature_importance.csv` | 対応モデルのみ |
| Plot | `validation_prediction_vs_actual.png` | 予測 vs 実測 |
| Plot | `validation_residual_histogram.png` | 残差ヒストグラム |
| Plot | `validation_residual_vs_predicted.png` | 予測値 vs 残差 |

## build_ensemble_<method>

| 種別 | ファイル | 内容 |
| --- | --- | --- |
| Artifact | `model_<method>.joblib` | アンサンブル estimator |
| Artifact | `model_info_<method>.json` | アンサンブルモデル情報 |
| Artifact | `ensemble_info_<method>.json` | 構成モデルと重み |
| Artifact | `metrics_<method>.json` | アンサンブル指標 |
| Table | `ensemble_predictions_<method>.csv` | validation 予測 |
| Table | `ensemble_members_<method>.csv` | 構成モデル |
| Table | `ensemble_weights_<method>.csv` | 重み |

## evaluate_models

| 種別 | ファイル | 内容 |
| --- | --- | --- |
| Artifact/Table | `leaderboard.csv` | 全候補比較 |
| Table | `leaderboard_topk.csv` | 上位候補 |
| Table | `leaderboard_decision_summary.csv` | UI 表示用判断 summary |
| Table | `best_vs_ensemble_summary.csv` | best 単体 vs ensemble |
| Artifact | `metrics_by_candidate.json` | 候補別指標 |
| Table | `metrics_by_candidate.csv` | 候補別指標 table |
| Artifact | `best_model.json` | 最良候補情報 |
| Artifact | `best_model.joblib` | 最良モデル実体 |
| Artifact | `evaluation_report.json` | 評価 report |
| Table | `evaluation_predictions.csv` | 推奨モデルの予測 |
| Table | `candidate_predictions.csv` | 候補別予測 |
| Artifact | `decision_summary.md` | 人間向け判断メモ |
| Artifact | `decision_summary.json` | 構造化判断メモ |
| Artifact | `recommendation.json` | 互換用推奨情報 |
| Artifact | `manifest.json` | 出力一覧 |

## tabular_infer

| 種別 | ファイル | 内容 |
| --- | --- | --- |
| Table | `predictions.csv` | 予測結果 |
| Artifact/Table | `schema_check_summary.json/csv` | 入力スキーマ検証 |
| Table | `prediction_summary.csv` | 予測値集計 |
| Table | `prediction_preview.csv` | 予測先頭行 |
| Table | `source_summary.csv` | モデル取得元情報 |
| Plot | `prediction_distribution_histogram.png` | 予測分布 |
| Artifact | `manifest.json` | 出力一覧 |

## manifest の役割

各 RunResult は `manifest.json` を持ち、設定、メトリクス、Artifacts、Tables、Plots をまとめます。Local 実行では成果物の場所を追いやすくし、ClearML 実行では Artifact 一覧の補助になります。
