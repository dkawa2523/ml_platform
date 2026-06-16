# モデルとアンサンブル

この基盤では、テーブルスカラー回帰でよく使うモデルを複数候補として学習し、同一 validation split 上で比較します。

## 対応モデル

| モデル名 | 種類 | 依存 | 特徴 |
| --- | --- | --- | --- |
| `linear` | 線形回帰 | numpy | 軽量。ベースライン向け |
| `ridge` | L2 正則化線形回帰 | numpy | 安定した線形ベースライン |
| `lasso` | L1 正則化線形回帰 | scikit-learn | 特徴量選択効果がある |
| `elasticnet` | L1/L2 正則化 | scikit-learn | Lasso と Ridge の中間 |
| `random_forest` | Bagging tree | scikit-learn | 非線形・相互作用に強い |
| `extra_trees` | Extra Trees | scikit-learn | RandomForest よりランダム性が高い |
| `gradient_boosting` | GBDT | scikit-learn | 中小規模の表形式で扱いやすい |
| `lightgbm` | GBDT | optional | 大規模・高性能な GBM |
| `xgboost` | GBDT | optional | 広く使われる高性能 GBM |
| `catboost` | GBDT | optional | カテゴリに強い GBM。現状は前処理後に利用 |

## model_suite

ClearML UI では、`Basic/model_suite` により候補セットを選べます。

| suite | 候補 |
| --- | --- |
| `default` | 全対応モデル |
| `fast` | optional dependency を含まないモデル |
| `interpretable` | `linear`, `ridge`, `lasso`, `elasticnet` |
| `tree` | `random_forest`, `extra_trees`, `gradient_boosting` |
| `gbm` | `lightgbm`, `xgboost`, `catboost` |
| `custom` | `Model/candidates` を直接使用 |

## quality_mode

`Basic/quality_mode` は、探索ではなく固定パラメータ preset です。

| mode | 説明 |
| --- | --- |
| `fast` | 推定器数を抑え、疎通確認を早くする |
| `standard` | 標準設定。初期比較向け |
| `quality` | 推定器数を少し増やす。HPO ではない |

## アンサンブル方式

| method | 内容 | 有用な場面 |
| --- | --- | --- |
| `mean_topk` | 上位 k モデルの平均 | モデル間のばらつきを平均化したい場合 |
| `weighted` | 指標に応じた重み付き平均 | 良いモデルへ重みを寄せたい場合 |
| `median` | 上位 k モデルの中央値 | 外れた予測を抑えたい場合 |

## Weighted ensemble の考え方

重み付き平均では、各モデルの予測 \(\hat{y}_m\) に重み \(w_m\) をかけて合成します。

$$
\hat{y}_{ens} = \frac{\sum_{m=1}^{M} w_m \hat{y}_m}{\sum_{m=1}^{M} w_m}
$$

選択指標が RMSE や MAE のように小さいほど良い場合、指標値が小さいモデルに大きい重みを与えます。R2 のように大きいほど良い指標では、順位や正規化の扱いに注意します。

## モデル追加時の原則

- まず `models.py` で `SUPPORTED_MODELS` と `build_model` を拡張する。
- 依存が重いモデルは optional dependency として扱う。
- ClearML テンプレートをモデルごとに増やさない。
- `model.candidates` と `model.params` で同じ Pipeline に組み込む。
- feature importance を出せる場合だけ、既存の `plots.py` の仕組みに合わせる。
