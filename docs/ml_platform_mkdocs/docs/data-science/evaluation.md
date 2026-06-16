# 評価とモデル選択

評価 Stage は、候補モデルとアンサンブルを比較し、推論に使うモデルを選ぶための中心です。

## 評価の基本単位

各モデルは同一 validation split 上で評価されます。

$$
\text{candidate} = (\text{model name}, \text{parameters}, \text{validation predictions}, \text{metrics})
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
| Pareto RMSE/R2 | 精度指標間のトレードオフ |

## decision_summary.md

`decision_summary.md` は、評価結果を運用判断へ翻訳するファイルです。データサイエンティストは、この内容を見て、推論に使う selector と注意事項を確認します。

| 項目 | 内容 |
| --- | --- |
| best model | 最良候補 |
| artifact kind | model / ensemble |
| metrics | best の指標 |
| ensemble comparison | 単体 best との比較 |
| recommended selector | 推論 Task の `Model/model_selector` |
| recommended source | `source_task_id` の指定例 |

## 評価の限界

現行評価は単一 holdout です。データ量が少ない場合、分割によるぶれがあります。重要な運用判断では、将来的に外部 validation、group k-fold、time-series validation などを検討してください。現行リリースでは未実装であり、ロードマップに残しています。
