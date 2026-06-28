# `tabular` パッケージ構成に関するレビューコメント分析

## 1. 画像から確認できるレビュー情報

| 項目 | 内容 |
|---|---|
| PR状態 | Open |
| PRタイトル | `SPDML-pipeline-integration_v1` |
| PR番号 | `#28` |
| PR作成者 | TEL EID Kawahito, Daiki（`daiki-kawahito_tel1111`） |
| コミット数 | 7 commits |
| マージ先 | `main` |
| マージ元 | `feature/alfa_v1.0…` ※右端が画像外のため完全なブランチ名は判読不可 |
| コメント投稿者 | TEL EID Ogawa, Yusuke（`yusuke-ogawa_tel1111`） |
| 投稿日時 | 3 days ago |
| コメントの主題 | `tabular` パッケージのモジュール分割・責務整理 |

画像下端には次の要素が一部見えていますが、内容が切れているため、このレビューコメント以降は文字起こし対象に含めていません。

---

## 2. レビューコメント全文の文字起こし

```text
tabular パッケージ構成の整理

infer.py, plots.py, pipeline.py など、いくつかのモジュールで多量の関数が存在するため、全体把握が困難になっていますが、これはパッケージ構造の再編成で各段に見やすくなる余地があると思います。

infer.py

このファイルは、モデルの場所を探す処理、メタ情報の読み込み、スキーマチェック、予測フレーム生成、出力保存が1つにまとまっています。
これは本質的に1つの問題ではなく、独立した小機能の寄せ集めなので、分割効果が高いです。
たとえば「inference/resolver」「inference/schema」「inference/prediction_writer」
「inference/runner」などに分割すると、かなり読みやすくなりそうです。

pipeline.py

最も構造的な圧縮余地があります。
ここは学習オーケストレーションだけでなく、候補モデルの学習、アンサンブル、評価、
ランキング、summary、recommendation まで抱えています。
これは製品機能として自然な広さではありますが、1ファイルで持つ必要はありません。
本質的に重そうな部分は evaluate_models がたくさんの成果物を作ることですが、それ以外の多くは分割可能です。

plots.py

feature、prediction、candidate、leaderboard、summary が1ファイルに混在しているため、plot 種類ごとに分割すると見通しがよくなりそうです。
```

### 判読上の補足

冒頭の「各段に見やすくなる」は画像上そのように読めますが、文脈上は「**格段に見やすくなる**」の誤記である可能性が高いです。

---

## 3. レビュー全体の意図

このレビューは、アルゴリズム上の不具合や個別関数の実装ミスを指摘しているのではなく、次の設計上の問題を指摘しています。

- 1つのモジュールに異なる責務が集まりすぎている
- 変更箇所を特定するためにファイル全体を把握する必要がある
- モジュール単位の凝集度が低い
- 単体テストや再利用がしにくい
- 将来的に依存関係や循環参照が複雑化する可能性がある

設計用語では、いわゆる「God Module」「低凝集なモジュール」に近い状態です。要求されているのは単純なファイル分割ではなく、**変更理由や責務ごとに境界を設けること**です。

レビューの書き方は「余地がある」「なりそう」と提案調であり、画像だけからはマージを止める必須指摘か、将来対応の推奨事項かまでは判断できません。

---

## 4. `infer.py` に対する指摘

### 4.1 現在まとめられている責務

レビューでは、少なくとも次の5つが1ファイルに集約されていると指摘されています。

1. モデルの場所を探す処理
2. メタ情報の読み込み
3. スキーマチェック
4. 予測フレームの生成
5. 出力の保存

これらは同じ推論処理の一部ではありますが、変更理由が異なります。

例えば、モデル保存先の仕様変更は「モデル解決処理」だけに関係し、出力フォーマットの変更は「保存処理」だけに関係します。現在の構造では、独立しているはずの変更が同じファイルに集中します。

### 4.2 レビューで明示されている分割案

```text
inference/resolver
inference/schema
inference/prediction_writer
inference/runner
```

それぞれの想定責務は次のように解釈できます。

| モジュール | 想定責務 |
|---|---|
| `resolver` | モデル参照、モデルパス、バージョン、保存場所の解決 |
| `schema` | 入力データ、モデル要求列、データ型などの検証 |
| `prediction_writer` | 予測結果の保存、シリアライズ、出力先管理 |
| `runner` | 各処理の呼び出し順序を制御する推論オーケストレーター |

### 4.3 レビュー案だけでは配置が曖昧な責務

レビューが挙げた4モジュールだけでは、次の2つの配置が明確ではありません。

- メタ情報の読み込み
- 予測フレームの生成

責務を明確にするなら、次のように独立させる方が自然です。

```text
tabular/
└── inference/
    ├── __init__.py
    ├── resolver.py
    ├── metadata.py
    ├── schema.py
    ├── prediction_frame.py
    ├── prediction_writer.py
    └── runner.py
```

想定インターフェースは、例えば以下の形です。

```python
resolve_model(model_ref) -> ResolvedModel
load_metadata(model_path) -> ModelMetadata
validate_schema(frame, schema) -> ValidationResult
build_prediction_frame(predictions, input_frame) -> DataFrame
write_predictions(frame, destination) -> WriteResult
run_inference(request) -> InferenceResult
```

`runner.py`には細かな処理を書かず、上記コンポーネントを順番に呼び出す処理だけを置くのが望ましい構成です。

### 4.4 対応に必要なリポジトリ情報

実際に分割する前に、少なくとも以下を確認する必要があります。

- `infer.py`に存在する関数、クラス、定数の一覧
- 各関数を呼んでいるモジュール
- 外部利用されている公開API
- モデル指定がパス、URI、モデル名、バージョンなどのどれに対応しているか
- モデル探索時の優先順位
- メタ情報の保存形式とバージョニング
- スキーマ不一致時にエラーにするか、型変換・列補完するか
- 予測フレームの列、インデックス、データ型
- 出力形式、ファイル名、上書き条件
- ログ出力や例外クラス
- ファイル保存が副作用としてどこで発生しているか

### 4.5 テスト上の必要事項

分割前に、現在の動作を固定する特性テストが必要です。

- 同じモデルが解決されること
- 同じ入力に対して同じスキーマ判定になること
- 予測フレームの列順、型、インデックスが変わらないこと
- 同じ場所・形式で出力されること
- `runner`経由の統合処理が従来と等価であること

---

## 5. `pipeline.py` に対する指摘

### 5.1 レビュー上の重要度

レビューでは、`pipeline.py`について「**最も構造的な圧縮余地があります**」と述べています。

したがって、3ファイルの中では、構造的な問題が最も大きいと評価されています。

### 5.2 現在まとめられている責務

画像から読み取れる責務は次のとおりです。

1. 学習全体のオーケストレーション
2. 候補モデルの学習
3. アンサンブル
4. 評価
5. ランキング
6. サマリー生成
7. レコメンデーション生成

これらは製品としては一連のワークフローですが、単一ファイルに置くべき単一責務ではありません。

特に、オーケストレーションと個別処理は分離する必要があります。

- オーケストレーター：何をどの順番で実行するか
- 個別処理：実際の学習、評価、ランキングなどを行う

### 5.3 `evaluate_models` が中心的な問題

レビューでは、`evaluate_models`が「たくさんの成果物を作る」ことを、本質的に重い部分として挙げています。

これは次のいずれかの状態になっている可能性があります。

- 戻り値のタプルや辞書が非常に大きい
- 多数のファイルを副作用として保存する
- メトリクス、予測値、モデル、ランキングなどを同時生成する
- 後段処理が`evaluate_models`内部の実装詳細に依存している
- 共有状態を更新している
- 評価とレポート生成が混在している

改善時には、成果物を型として明示する方法が有効です。

```python
@dataclass(frozen=True)
class EvaluationResult:
    metrics: ...
    predictions: ...
    model_artifacts: ...
    diagnostics: ...
```

そのうえで、後段処理を分離します。

```python
evaluation_result = evaluate_models(...)
ranking = rank_models(evaluation_result)
summary = build_summary(evaluation_result, ranking)
recommendation = build_recommendation(evaluation_result, ranking)
```

これにより、評価処理がサマリーやレコメンデーションを直接生成する必要がなくなります。

### 5.4 想定される分割構成

```text
tabular/
└── pipeline/
    ├── __init__.py
    ├── orchestrator.py
    ├── candidate_training.py
    ├── ensemble.py
    ├── evaluation.py
    ├── ranking.py
    ├── summary.py
    ├── recommendation.py
    └── artifacts.py
```

| モジュール | 責務 |
|---|---|
| `orchestrator.py` | 全体フロー、実行順序、ステップ間連携 |
| `candidate_training.py` | 候補モデルの構築・学習 |
| `ensemble.py` | アンサンブルモデルの構築 |
| `evaluation.py` | モデル評価と評価結果の生成 |
| `ranking.py` | 評価結果から順位を決定 |
| `summary.py` | 人間向け・機械向けサマリー生成 |
| `recommendation.py` | 推奨モデルや推奨構成の決定 |
| `artifacts.py` | ステップ間で受け渡す成果物の型定義 |

依存方向は、個別処理がオーケストレーターを参照しない形にする必要があります。

```text
artifacts / types
       ↑
training / evaluation / ranking / summary / recommendation
       ↑
orchestrator
```

### 5.5 対応に必要なリポジトリ情報

- パイプラインの実行順序
- 各ステップの入力・出力
- `evaluate_models`が生成する全成果物
- 各成果物を利用する後続処理
- ファイル保存やデータベース登録などの副作用
- 共有されている設定オブジェクト
- 共有可変状態の有無
- 並列実行の有無
- 乱数シードの管理方法
- 途中失敗時のリトライや再開方法
- CLI、API、バッチ処理からの呼び出し経路
- 現在の公開関数と外部利用箇所

### 5.6 特に注意すべき点

単に関数を別ファイルへ移動しただけでは、巨大なコンテキストオブジェクトや辞書を全モジュールで共有する構造になり、問題が改善しない可能性があります。

分割時には、次の境界を明示する必要があります。

- 設定値
- 入力データ
- モデル成果物
- 評価結果
- ランキング結果
- サマリー
- 推奨結果

---

## 6. `plots.py` に対する指摘

### 6.1 現在混在している描画領域

レビューでは以下の5種類が挙げられています。

1. `feature`
2. `prediction`
3. `candidate`
4. `leaderboard`
5. `summary`

描画処理という共通点はありますが、扱うデータと変更理由が異なります。

例えば、特徴量可視化の変更とリーダーボード表示の変更は無関係です。種類ごとに分けることで、対象となる描画処理を探しやすくなります。

### 6.2 想定される分割構成

```text
tabular/
└── plots/
    ├── __init__.py
    ├── feature.py
    ├── prediction.py
    ├── candidate.py
    ├── leaderboard.py
    ├── summary.py
    └── common.py
```

`common.py`には、複数種類で本当に共有される処理だけを配置します。

- 共通ラベル
- 図の保存処理
- 軸や凡例の共通設定
- ファイル名生成
- 入力データの共通整形

すべてを`common.py`へ集約すると再び巨大モジュールになるため、共有処理の抽出は最小限にする必要があります。

### 6.3 対応に必要なリポジトリ情報

- `plots.py`内の関数一覧
- 各関数がどの描画領域に属するか
- 描画ライブラリ
- 戻り値がFigure、Axes、ファイルパス、`None`のどれか
- 関数内で直接保存しているか
- ファイル名や保存先の規則
- 共通テーマやスタイル設定
- グローバルな描画設定を書き換えていないか
- 描画関数を呼び出している箇所
- テストやドキュメントで利用されている公開関数

---

## 7. 推奨される最終パッケージ構成

レビュー内容を責務単位まで具体化すると、次の構成が考えられます。

```text
tabular/
├── inference/
│   ├── __init__.py
│   ├── resolver.py
│   ├── metadata.py
│   ├── schema.py
│   ├── prediction_frame.py
│   ├── prediction_writer.py
│   └── runner.py
│
├── pipeline/
│   ├── __init__.py
│   ├── orchestrator.py
│   ├── candidate_training.py
│   ├── ensemble.py
│   ├── evaluation.py
│   ├── ranking.py
│   ├── summary.py
│   ├── recommendation.py
│   └── artifacts.py
│
└── plots/
    ├── __init__.py
    ├── feature.py
    ├── prediction.py
    ├── candidate.py
    ├── leaderboard.py
    ├── summary.py
    └── common.py
```

ただし、実際の関数数や依存関係が少ない場合は、ここまで細かく分割すると過剰設計になります。まず現在の関数を責務ごとに分類し、各モジュールに十分な凝集性が生まれる範囲でまとめるべきです。

---

## 8. 後方互換性に関する注意点

現在、他のコードが次のようにインポートしている可能性があります。

```python
from tabular.infer import run_inference
from tabular.pipeline import run_pipeline
from tabular.plots import plot_leaderboard
```

パッケージ化後も既存APIを維持する場合は、`__init__.py`や旧モジュールから再公開します。

```python
# tabular/inference/__init__.py
from .runner import run_inference

__all__ = ["run_inference"]
```

`infer.py`を互換ファサードとして一定期間残す方法もあります。

```python
# tabular/infer.py
from .inference.runner import run_inference

__all__ = ["run_inference"]
```

一方、`pipeline.py`と`pipeline/`、`plots.py`と`plots/`のような同名モジュール・同名パッケージの併存は避け、移行時にインポート先を統一する方が安全です。

---

## 9. 優先順位

レビュー内容から判断した構造上の重要度は次の順です。

1. `pipeline.py`
2. `infer.py`
3. `plots.py`

ただし、安全に段階移行する実装順序としては、次の方が低リスクです。

1. 現在動作を固定するテスト追加
2. `plots.py`の分割
3. `infer.py`の分割
4. 成果物の型・契約を定義
5. `pipeline.py`の分割
6. 互換レイヤーや不要な旧APIの整理

`plots.py`は責務境界が明確で副作用範囲も比較的限定されるため、分割方法の妥当性を確認する最初の対象に向いています。`pipeline.py`は影響範囲が大きいため、評価結果や成果物の契約を先に明文化してから着手する必要があります。
