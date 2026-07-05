# 用語集

| 用語 | 説明 |
| --- | --- |
| Artifact | 実行結果として保存されるファイル。モデル、JSON、CSV、画像など |
| ClearML Agent | Queue から Task を受け取り実行する worker |
| ClearML Dataset | ClearML 上で管理されるデータセット |
| ClearML Task | ClearML における実行単位 |
| PipelineController | ClearML Pipeline の依存関係と Stage 実行を管理する controller |
| Stage | Pipeline を構成する処理単位。前処理、学習、評価など |
| user-facing template | ClearML UI ユーザーが直接使うテンプレート |
| internal template | PipelineController が内部的に使うテンプレート |
| model_selector | 推論時にどのモデルを使うかを指定する文字列。`best`, `ridge`, `ensemble:median` など |
| feature_spec | 学習時の特徴量仕様を記録した JSON |
| preprocess_bundle | 学習時に fit した前処理 transformer を含む joblib |
| leaderboard | 候補モデルとアンサンブルの比較表 |
| best_model.json | 評価結果から推論設定を判断するための canonical artifact |
| schema_check_summary | 推論入力が学習時特徴量仕様と整合しているかの確認結果 |
| Basic/model_suite | ClearML UI で候補モデル群を選ぶ基本パラメータ |
| Basic/quality_mode | モデルパラメータ preset を選ぶ基本パラメータ。HPO ではない |
| Holdout split | データを train と validation に一度だけ分ける評価方式 |
| Group split | 同じ group が train/validation に跨がらないようにする分割 |
| Time split | 時系列順に並べ、最新側を validation にする分割 |
| Fixed split | 指定列の値により validation 行を決める分割 |
| HPO | Hyperparameter Optimization。現行リリースでは未実装 |
| Model Registry | 承認済みモデル管理。現行リリースでは未実装 |
| Drift Monitoring | 入力分布や予測分布の変化監視。現行リリースでは未実装 |
