# リポジトリ構成

この章では、主要ディレクトリとファイルの役割を整理します。

## ルート構成

```text
ml_platform/
  clearml/
  config/
  deploy/
  docs/
  pkgs/
    core/
    tabular/
  scripts/
  tests/
  verification/
  README.md
  pyproject.toml
  requirements.txt
  requirements-dev.txt
```

| パス | 役割 |
| --- | --- |
| `clearml/` | ClearML SDK と接続する運用層 |
| `config/tasks/` | task 単位の設定 |
| `config/profiles/` | 実行環境 profile |
| `pkgs/core/` | 汎用設定、IO、Artifact、Result |
| `pkgs/tabular/` | テーブル回帰のドメイン処理 |
| `scripts/` | Local 実行やテンプレート同期のラッパー |
| `tests/` | 回帰テスト |
| `docs/` | 現行仕様、ClearML UI 仕様、ロードマップ |
| `verification/` | 検証証跡、確認結果 |

## `pkgs/core`

| ファイル | 役割 |
| --- | --- |
| `config.py` | YAML 読み込み、profile/task 合成、override 適用 |
| `io.py` | table/json/joblib などの入出力 |
| `artifacts.py` | run directory、manifest、latest link 管理 |
| `result.py` | `RunResult` データ構造 |
| `registry.py` | 必要に応じた軽量 registry 機能 |

`pkgs/core` は特定のタスク種別に依存しない処理だけを持ちます。

## `pkgs/tabular`

| ファイル | 役割 |
| --- | --- |
| `data.py` | データ読み込み、特徴量選択、holdout split |
| `data_quality.py` | 軽量データ品質レポート |
| `features.py` | 欠損補完、カテゴリ処理、スケーリング |
| `models.py` | モデル候補、モデル構築、Estimator/Ensemble |
| `metrics.py` | 回帰指標、prediction frame |
| `ensemble.py` | アンサンブル設定、重み計算 |
| `pipeline.py` | 学習 Pipeline の本体 |
| `stage.py` | ClearML Pipeline stage 単位の実行 |
| `infer.py` | 推論処理、スキーマチェック、予測出力 |
| `plots.py` | 表・画像・Plot 用補助 |
| `model_artifact.py` | モデル情報 JSON の出力 |
| `runners.py` | task 種別に応じた実行入口 |

## `clearml`

| ファイル | 役割 |
| --- | --- |
| `app.py` | ClearML Task entrypoint |
| `pipelines.py` | PipelineController plan とテンプレート構築 |
| `adapter.py` | ClearML SDK の薄い adapter |
| `reports.py` | RunResult を ClearML Scalars/Tables/Plots/Artifacts に変換 |
| `_entrypoint_bootstrap.py` | ClearML entrypoint の import path 調整 |

## `config/tasks`

| ファイル | 役割 |
| --- | --- |
| `tabular_pipeline.yaml` | user-facing 学習 Pipeline 設定 |
| `tabular_stage.yaml` | internal stage template 設定 |
| `tabular_infer.yaml` | user-facing 推論 Task 設定 |

その他の互換・将来用 task config が残る場合でも、ClearML user-facing entrypoint ではありません。

## `scripts`

| スクリプト | 用途 |
| --- | --- |
| `make_sample_data.py` | サンプル train/infer データ作成 |
| `local_run.py` | Local task 実行 |
| `sync_clearml_templates.py` | ClearML テンプレート同期 |

## 設計レビュー時の観点

- ClearML SDK import が `pkgs/core` や `pkgs/tabular` に混ざっていないか。
- 新しいモデルのためにテンプレートが増えていないか。
- Artifact 名や table 名が既存の規約と一致しているか。
- UI 向け Basic 項目と詳細項目の優先順位が明確か。
- docs/SPEC.md と実装がずれていないか。
