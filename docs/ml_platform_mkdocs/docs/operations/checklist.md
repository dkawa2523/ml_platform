# 運用チェックリスト

## 初回セットアップ

- [ ] Python 3.10 以上を用意した。
- [ ] `uv pip install -e pkgs/core -e pkgs/tabular -r requirements-dev.txt` を実行した。
- [ ] `python scripts/make_sample_data.py` が成功した。
- [ ] Local training smoke が成功した。
- [ ] Local inference smoke が成功した。
- [ ] `pytest -q` が通った。

## ClearML テンプレート同期

- [ ] ClearML server に接続できる。
- [ ] `clearml-dev.yaml` の Project 名が環境に合っている。
- [ ] `controller_queue` と `stage_queue` が存在する。
- [ ] Agent image が pull 可能である。
- [ ] Dataset ID と dataset file が存在する。
- [ ] `sync_clearml_templates.py --dry-run` が通る。
- [ ] 実 sync 後、UI に `template/tabular_train_pipeline` がある。
- [ ] New Run に Basic 項目が表示される。

## 学習 Run 実行前

- [ ] `Input/clearml_dataset_id` を確認した。
- [ ] `Input/dataset_file` を確認した。
- [ ] `Input/target_column` を確認した。
- [ ] `Basic/model_suite` を選んだ。
- [ ] GBM を使う場合、依存関係を確認した。
- [ ] split method が問題設定に合っている。
- [ ] ID列と drop columns を確認した。

## 学習 Run 実行後

- [ ] Pipeline が全 Stage 成功した。
- [ ] `data_quality_warnings` に重大問題がない。
- [ ] `leaderboard` を確認した。
- [ ] `decision_summary.md` を確認した。
- [ ] 推論に使う `model_selector` を確認した。
- [ ] 必要な Artifact が出ている。

## 推論 Run 実行後

- [ ] `schema_check_summary.status` が `error` でない。
- [ ] `source_summary` が意図したモデルを示している。
- [ ] `prediction_summary` の分布が妥当。
- [ ] `predictions.csv` に `row_index` または ID列がある。
- [ ] 業務データとの結合キーを確認した。
