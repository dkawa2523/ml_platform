# ClearML UI: 入口とプロジェクト

ClearML UI で迷わないように、テンプレート、実行タスク、Project、Tag に規約があります。

## 入口

| 用途 | UI 上の入口 | 備考 |
| --- | --- | --- |
| 学習 | Pipeline tab の `template/tabular_train_pipeline` | ユーザーが最初に使う学習入口 |
| 推論 | Task template の `template/tabular_infer` | 学習済み Task または local path から推論 |
| 内部 Stage | `internal/tabular_stage` | PipelineController が使う。手動実行しない |

## Project レイアウト

開発 profile の標準 Project は次の通りです。

| オブジェクト | Project |
| --- | --- |
| テンプレート | `MLPlatform/Dev/Templates/Tabular` |
| Pipeline controller | `MLPlatform/Dev/Pipelines/Tabular` |
| 前処理 Stage | `MLPlatform/Dev/Runs/Tabular/Preprocess` |
| 学習 Stage | `MLPlatform/Dev/Runs/Tabular/Train` |
| アンサンブル Stage | `MLPlatform/Dev/Runs/Tabular/Ensemble` |
| 評価 Stage | `MLPlatform/Dev/Runs/Tabular/Evaluate` |
| 推論 Task | `MLPlatform/Dev/Runs/Tabular/Infer` |
| 実験・互換 | `MLPlatform/Dev/Experiments/Tabular` |

## 命名規約

| 実行種別 | 形式 |
| --- | --- |
| Pipeline | `pipeline/tabular_train_pipeline/<run_name>` |
| preprocess | `stage/preprocess_features/<run_name>` |
| train | `stage/train_<model>/<run_name>` |
| ensemble | `stage/build_ensemble_<method>/<run_name>` |
| evaluate | `stage/evaluate_models/<run_name>` |
| infer | `task/tabular_infer/<run_name>` |

## Tag 規約

| Tag | 用途 |
| --- | --- |
| `domain:tabular` | テーブルデータ系処理であること |
| `run_type:template` | テンプレート |
| `run_type:pipeline` | Pipeline controller |
| `run_type:stage` | Pipeline 内 Stage |
| `run_type:task` | 独立 Task |
| `user_facing:true` | UI ユーザーが直接使う入口 |
| `internal:true` | Pipeline 内部用 |
| `stage:<stage_name>` | Stage 名 |
| `model:<model_name>` | 学習モデル名 |
| `ensemble:<method>` | アンサンブル方式 |

## なぜ分けるのか

Project と Tag を分けることで、ClearML UI 上で次の確認が容易になります。

- Pipeline 全体の成功/失敗
- どのモデル Stage が失敗したか
- どのアンサンブルが作られたか
- 評価結果だけを一覧したい場合
- 推論 Task だけを運用確認したい場合

ClearML 上の旧 Task はコードから自動削除しません。古いテンプレートや古い clone が残っている場合は、人手で archive してください。
