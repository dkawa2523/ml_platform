# トラブルシューティング

この章では、Local 実行と ClearML 実行でよく起きる問題と確認方法を整理します。

## Local 実行

| 症状 | 主な原因 | 対応 |
| --- | --- | --- |
| `data.local_path is required` | `data.local_path` が空 | task YAML または `--set` で指定する |
| `target_column not found` | 目的変数列名が違う | `data.target_column` を確認する |
| `features.drop_columns not found` | drop 指定列が存在しない | 列名を修正する |
| GBM モデルで import error | optional dependency 未導入 | `pkgs/tabular[gbm]` を入れるか候補から外す |
| 推論で model が見つからない | 学習出力がない/selector違い | `local_model_path` または `model_selector` を確認 |
| 推論で missing feature error | 推論入力に必須列不足 | `schema_check_summary` を確認し入力データを修正 |

## ClearML 実行

| 症状 | 主な原因 | 対応 |
| --- | --- | --- |
| `preprocess_features` が queued のまま | Controller と Stage が同じ少数 Queue | controller queue と stage queue を分ける |
| Dataset が読めない | Dataset ID / file 名違い | `Input/clearml_dataset_id`, `Input/dataset_file` を確認 |
| GBM Stage が失敗 | Agent 環境に依存なし | template sync、Docker image、model_suite を確認 |
| New Run に Basic 項目がない | 古い template clone を使っている | 最新 `template/tabular_train_pipeline` を開く |
| Artifact が保存されない | artifact storage 未設定 | `artifact_output_uri` または ClearML server 設定を確認 |
| 推論 source_task_id が解決できない | 参照 Task が違う | `best_model.json` の推奨設定を確認 |

## schema_check の warning

| warning | 意味 | 対応 |
| --- | --- | --- |
| `extra_columns` | 推論入力に学習で使わない列がある | 通常は継続可。列名を確認 |
| `missing_id_columns` | ID列が入力にない | 業務結合に必要なら入力に追加 |
| `unknown_or_unseen_category_warning` | 学習時にないカテゴリがある | 予測分布を確認。必要なら再学習 |

## 評価結果が悪い場合

1. `data_quality_warnings.csv` を確認する。
2. target 分布と欠損を確認する。
3. split method が問題設定に合っているか確認する。
4. `feature_columns` にリーク列や不要列がないか確認する。
5. `prediction_vs_actual` と残差 Plot を確認する。
6. `model_suite` と `quality_mode` を調整する。
7. 必要なら特徴量設計を見直す。

## 古いテンプレート問題

ClearML では古い Task や clone が残ることがあります。新しい UI 項目が出ない場合は、最新の template を開いているか確認してください。不要な古いテンプレートや失敗 Run は、人手で archive します。
