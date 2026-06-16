# 環境構築

この章では、Local 実行と ClearML 実行に必要な環境を整理します。Local 実行だけを試す場合、ClearML サーバーは不要です。

## Python と依存関係

本リポジトリは Python 3.10 以上を対象にしています。最小構成では、`pkgs/core` と `pkgs/tabular` を editable install し、開発用依存を入れます。

```powershell
uv venv .venv
.\.venv\Scripts\activate
uv pip install -e pkgs/core -e pkgs/tabular -r requirements-dev.txt
```

`requirements.txt` には、主に以下の実行時依存が含まれます。

| パッケージ | 主な用途 |
| --- | --- |
| `pandas` | CSV/Parquet などのテーブル処理 |
| `numpy` | 数値計算、分割、線形モデル実装 |
| `pyyaml` | YAML 設定の読み込み |
| `scikit-learn` | Lasso、ElasticNet、RandomForest、ExtraTrees、GradientBoosting など |
| `pillow` | 一部プロット画像出力 |
| `clearml` | ClearML Task、Dataset、Pipeline、Artifact 連携 |

## GBM 系モデルを使う場合

`lightgbm`、`xgboost`、`catboost` は optional dependency として扱われます。Local で全モデル候補を使う場合は、追加で GBM 依存を入れてください。

```powershell
uv pip install -e "pkgs/tabular[gbm]"
```

軽量確認では、GBM 系を外した候補で実行できます。

```powershell
python scripts/local_run.py --task config/tasks/tabular_pipeline.yaml --profile config/profiles/local.yaml --set "model.candidates=[linear,ridge,lasso,elasticnet,random_forest,extra_trees,gradient_boosting]"
```

## Local 実行用 profile

`config/profiles/local.yaml` は Local 実行の標準 profile です。

```yaml
profile: local

runtime:
  output_dir: outputs
  use_clearml: false

data:
  base_dir: .

logging:
  level: INFO
```

| 項目 | 意味 |
| --- | --- |
| `runtime.output_dir` | 成果物の出力先。Local では `outputs` |
| `runtime.use_clearml` | ClearML SDK を使うか。Local では `false` |
| `data.base_dir` | 相対パス解決の基準 |
| `logging.level` | ログレベル |

## ClearML 実行用 profile

`config/profiles/clearml-dev.yaml` は ClearML 上でテンプレート、Pipeline、Stage、推論 Task をどの Project に配置するかを定義します。

| 項目 | 例 | 説明 |
| --- | --- | --- |
| `runtime.output_dir` | `/mnt/clearml/outputs` | Agent コンテナ内の成果物出力先 |
| `runtime.use_clearml` | `true` | ClearML SDK を使用する |
| `clearml.projects.templates` | `MLPlatform/Dev/Templates/Tabular` | テンプレート配置先 |
| `clearml.projects.pipelines` | `MLPlatform/Dev/Pipelines/Tabular` | Pipeline controller 配置先 |
| `clearml.projects.preprocess` | `MLPlatform/Dev/Runs/Tabular/Preprocess` | 前処理 Stage 配置先 |
| `clearml.projects.train` | `MLPlatform/Dev/Runs/Tabular/Train` | 学習 Stage 配置先 |
| `clearml.projects.ensemble` | `MLPlatform/Dev/Runs/Tabular/Ensemble` | アンサンブル Stage 配置先 |
| `clearml.projects.evaluate` | `MLPlatform/Dev/Runs/Tabular/Evaluate` | 評価 Stage 配置先 |
| `clearml.projects.infer` | `MLPlatform/Dev/Runs/Tabular/Infer` | 推論 Task 配置先 |
| `clearml.controller_queue` | `controller` | PipelineController を実行する Queue |
| `clearml.stage_queue` | `default` | Stage Task を実行する Queue |
| `clearml.execution.image` | `registry.example.com/...` | ClearML Agent が使う Docker image |
| `clearml.default_dataset_id` | Dataset ID | Pipeline New Run の初期 Dataset |
| `clearml.default_dataset_file` | `sample_train.csv` | Dataset 内の対象ファイル |

## ドキュメントサイトのビルド

このドキュメント一式を配置したあと、次のコマンドで確認できます。

```powershell
uv pip install -r requirements-docs.txt
mkdocs serve
```

静的 HTML を生成する場合は次を実行します。

```powershell
mkdocs build --strict
```

!!! note
    Mermaid と数式表示は MkDocs Material と PyMdown Extensions を前提にしています。社内環境で外部 CDN を使えない場合は、MathJax をローカル配布に切り替えてください。
