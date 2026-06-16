# 特徴量・メトリクス追加ガイド

特徴量処理や評価指標は、モデル精度と運用判断に直結します。追加時は、学習時と推論時の再現性、ClearML 表示、ドキュメント整合性を確認してください。

## 特徴量処理の追加

主な編集先は `features.py` と `pipeline.py` です。

### 追加手順

1. `normalize_feature_config` に設定値を追加する。
2. `FeatureTransformer.fit` で学習時の統計量やカテゴリ情報を保存する。
3. `FeatureTransformer.transform` で推論時も同じ変換を適用する。
4. `feature_spec.json` に設定を記録する。
5. 必要なら `data_quality_summary` に診断項目を追加する。
6. docs と tests を更新する。

### 注意点

- fit 時だけ分かる情報は必ず transformer に保存する。
- 推論時に入力データから再推定しない。
- 欠損、未知カテゴリ、型変換の扱いを明確にする。
- `passthrough_columns` との衝突を検証する。

## メトリクス追加

主な編集先は `metrics.py`、`pipeline.py`、`clearml/reports.py` です。

### 追加手順

1. `regression_metrics` に指標計算を追加する。
2. `metrics.names` で指定できるようにする。
3. `selection_metric` として使う場合、良い方向を定義する。
4. `leaderboard.csv` と ClearML scalar に出ることを確認する。
5. docs の数式と説明を更新する。

### 良い方向の扱い

| 指標例 | 良い方向 |
| --- | --- |
| `rmse` | 小さい |
| `mae` | 小さい |
| `r2` | 大きい |

新しい指標を `selection_metric` にする場合、順位付けの方向を `pipeline.py` の選択ロジックに反映してください。

## レポート追加

新しい table や artifact を出す場合は、`clearml/reports.py` で ClearML UI に表示するか検討します。

| 追加対象 | 推奨 |
| --- | --- |
| 人が見る CSV | table として report |
| 構造化 JSON | artifact として upload |
| 大量行の予測 | artifact 中心。Plot は top-k に絞る |
| 重要な判断 | markdown と json の両方を出す |
