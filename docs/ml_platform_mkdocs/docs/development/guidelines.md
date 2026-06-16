# 開発ガイドライン

この章では、第三者が安全に改修・拡張するための基本方針をまとめます。

## 基本原則

| 原則 | 内容 |
| --- | --- |
| ClearML 境界を守る | `pkgs/core` と `pkgs/tabular` に ClearML SDK を入れない |
| テンプレートを増やしすぎない | モデル別・データセット別・アンサンブル別 template は作らない |
| Artifact 名を安定させる | UI と推論が参照するため、名前変更は慎重に行う |
| Basic UI を複雑にしない | 初回ユーザー向け設定は少なく保つ |
| future を半実装しない | 未実装機能は `docs/ROADMAP.md` に置く |
| Local で検証できるようにする | ClearML 接続なしで処理本体をテストする |

## 変更前に見るファイル

| 目的 | 見るファイル |
| --- | --- |
| 製品範囲確認 | `docs/SPEC.md` |
| UI 仕様確認 | `docs/CLEARML_UI_SPEC.md` |
| 将来項目確認 | `docs/ROADMAP.md` |
| 設定確認 | `config/tasks/*.yaml`, `config/profiles/*.yaml` |
| 処理本体 | `pkgs/tabular/src/ml_platform_tabular/*.py` |
| ClearML 境界 | `clearml/*.py` |
| テスト | `tests/` |

## 変更の分類

| 変更種別 | 主な編集先 | 注意 |
| --- | --- | --- |
| モデル追加 | `models.py`, config, docs, tests | optional dependency の扱い |
| 特徴量追加 | `features.py`, `pipeline.py`, docs | fit/transform 一貫性 |
| メトリクス追加 | `metrics.py`, evaluation, reports | selection direction |
| UI 項目追加 | `clearml/pipelines.py`, docs | Basic を増やしすぎない |
| Artifact 追加 | `pipeline.py`/`infer.py`, `reports.py` | ClearML table/artifact 表示 |
| 推論変更 | `infer.py`, docs, tests | schema_check と predictions の互換性 |

## 実装レビュー観点

- コードが既存の小さな関数構成に沿っているか。
- 新しい抽象クラスや manager が本当に必要か。
- Local 実行と ClearML 実行の両方で意味があるか。
- 既存 Artifact を壊していないか。
- `decision_summary.md` や `schema_check_summary` など、利用者が見る出力に反映されているか。
- README / SPEC / UI SPEC が実装と一致しているか。

## コードスタイル

- 処理の意図が分かる関数名を使う。
- UI 文字列変換と処理本体を混ぜない。
- エラーは利用者が設定を直せる内容にする。
- 巨大な設定分岐は辞書や小さな helper にまとめる。
- 互換 alias は必要最小限にする。

## Pull Request で確認すること

1. Local smoke が通る。
2. `pytest -q` が通る。
3. ClearML template dry-run が通る。
4. 主要 Artifact が出る。
5. docs が更新されている。
6. 古い説明や矛盾したコメントが残っていない。
