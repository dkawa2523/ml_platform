# 評価とモデル選択

評価 Stage は、候補モデルとアンサンブルを比較し、推論に使うモデルを選ぶための中心です。

## 評価の基本単位

各モデルは training partition 内の同一 selection holdout 上で順位付けされます。選択後の最終指標は、モデル選択で未使用の test holdout 上で一度だけ算出します。

$$
\text{candidate} = (\text{model name}, \text{parameters}, \text{selection predictions}, \text{selection metrics})
$$

候補は `selection_metric` に基づいて順位付けされます。

## leaderboard

`leaderboard.csv` は評価結果の中心です。

| 観点 | 確認内容 |
| --- | --- |
| 順位 | `rank` が 1 の候補 |
| 指標 | `rmse`, `mae`, `r2` のバランス |
| 種別 | 単体モデルかアンサンブルか |
| 安定性 | 残差図や prediction plot と合わせて確認 |
| 運用性 | optional dependency や推論速度も考慮 |

## アンサンブル採用判断

アンサンブルは必ず採用するものではありません。以下の観点で判断します。

| 条件 | 判断 |
| --- | --- |
| 単体 best より RMSE/MAE が改善 | 採用候補 |
| 改善が微小 | モデル複雑性と比較して判断 |
| アンサンブルが重すぎる | 単体モデルを優先する場合あり |
| 解釈性が必要 | 線形/Tree 単体を優先する場合あり |

## 可視化

| Plot | 見ること |
| --- | --- |
| prediction vs actual | 全体的な当たり具合、外れ値 |
| residual histogram | 残差の偏り、裾の重さ |
| residual vs predicted | 予測値帯による誤差傾向 |
| leaderboard table | 上位候補の比較 |

## best_model.json

`best_model.json` は、評価結果を運用判断へ翻訳する canonical artifact です。データサイエンティストは、この内容を見て、推論に使う selector と参照 Task を確認します。

| 項目 | 内容 |
| --- | --- |
| best model | 最良候補 |
| artifact kind | model / ensemble |
| selection_metrics | candidate / ensemble の順位付け指標 |
| metrics | 未使用 test holdout 上の最終指標 |
| recommended selector | 推論 Task の `Model/model_selector` |
| recommended source | 推論 Task の `Model/source_task_id` |

## 評価の限界

現行評価は selection/test の二段 holdout です。データ量が少ない場合は両分割によるぶれがあります。重要な運用判断では、外部 test、group k-fold、time-series validation なども検討してください。
