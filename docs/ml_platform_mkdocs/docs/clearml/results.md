# ClearML UI: タスク結果と成果物

ClearML では、Scalars、Artifacts、Plots、Tables を使って結果を確認します。本基盤では Stage ごとに見るべき成果物を揃えています。

## Stage 別成果物

| Stage | Scalars | Tables | Artifacts | Plots |
| --- | --- | --- | --- | --- |
| preprocess | feature counts | feature summary, data quality, missing rate, type counts | `preprocess_bundle`, `feature_spec` | missing-rate bar |
| train | `rmse`, `mae`, `r2` | metrics, validation predictions, feature importance | `model.joblib`, `model_info.json` | prediction/residual plots |
| ensemble | ensemble metrics | predictions, members, weights | ensemble model/info | method plots |
| evaluate | best metrics | leaderboard, evaluation predictions | best model, best model json | leaderboard metric panel |
| infer | prediction summary | predictions, schema check, source summary | manifest | prediction distribution |

## ClearML 上の確認順

1. Pipeline Graph で失敗 Stage を確認する。
2. `preprocess_features` の data quality を見る。
3. `evaluate_models` の `best_model.json` を見る。
4. 必要に応じて `leaderboard.csv` と `evaluation_predictions.csv` を確認する。
5. 推論 Task の `schema_check_summary` と `predictions.csv` を確認する。

## よく見るタブ

| ClearML タブ | 用途 |
| --- | --- |
| Configuration | 実行パラメータ確認 |
| Scalars | メトリクス確認 |
| Plots | 予測 vs 実測、残差、leaderboard 表示 |
| Artifacts | CSV、JSON、joblib、画像の取得 |
| Console | エラー原因、依存関係、Dataset 解決の確認 |

## Artifact の扱い

`model.joblib` や `best_model.joblib` は推論に使う実体です。`model_info.json`、`feature_spec.json` とセットで扱うことで、推論時に特徴量仕様を再現できます。

| Artifact | 単独利用 | セットで必要なもの |
| --- | --- | --- |
| `model.joblib` | 予測実体 | `model_info.json`, `feature_spec.json` |
| `best_model.joblib` | 推奨推論モデル | `best_model.json`, `feature_spec.json` |
| `preprocess_bundle.joblib` | 前処理器 | `feature_spec.json` |
| `best_model.json` | 推論判断 | `leaderboard.csv` |
| `schema_check_summary.json` | 推論検証 | `source_summary.csv` |

## 古い Task が残る場合

テンプレート同期は既存の古い Task を削除しません。ClearML UI 上で似た名前の古い template や clone が残る場合、以下を確認してください。

- `user_facing:true` が付いているか。
- 最新の `template/tabular_train_pipeline` か。
- New Run に `Basic/model_suite` が表示されているか。
- Pipeline graph が現在の公式フローになっているか。
