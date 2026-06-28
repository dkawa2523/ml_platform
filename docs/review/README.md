# Review response workspace

このディレクトリは、PR #28 相当のレビューコメントを `ml_platform` 上で追跡し、後で別Gitアカウント・別リポジトリへ移植できるようにするための作業台です。

## 配置方法

このzipをリポジトリ直下で展開すると、次のような構成になります。

```text
docs/review/
├── source/
│   ├── repository_review_transcription_current.md
│   ├── pr28_review_consolidated.md
│   └── tabular_package_review_analysis.md
├── README.md
├── PR28_REVIEW_MAP.md
├── CODEX_WORK_LOG.md
├── BASELINE_ENV_REPORT.md
├── PORTING_GUIDE.md
├── REVIEW_FIX_BRANCH_PLAN.md
├── EXTRA_REVIEW_NOTES.md
├── REVIEW_RESPONSE_DRAFTS.md
├── CODEX_PROMPTS.md
├── LOCAL_SETUP_AND_GIT_COMMANDS.md
└── ADR_0002_RUNTIME_SPEC_AND_PACKAGE_MANIFEST_BOUNDARY.md
```

展開例:

```bash
# repo root で実行
unzip ml_platform_review_docs.zip
```

## source と作業文書の違い

`source/` 配下は、レビュー元資料をそのまま保存する場所です。内容の改変は原則しません。

それ以外のMarkdownは、現在repoでレビュー対応を進めるための作業文書です。Codexが作業するたびに、`PR28_REVIEW_MAP.md` と `CODEX_WORK_LOG.md` を更新してください。

## 運用ルール

- レビュー対応とレビュー外改善を混ぜない。
- 1コミット1目的にする。
- コミット本文に `Review-Refs: Rxx` を入れる。
- 後で移植できるよう、`PR28_REVIEW_MAP.md` の `Commit` と `Porting note` を更新する。
- 本体コードの大規模リファクタ前に characterization test を追加する。
- ClearML localhost UI や Kubernetes 実クラスタ検証は、実行できない場合 `manual verification required` と記録する。

## 重要な元資料

- `source/pr28_review_consolidated.md`: R01〜R27のレビューコメント統合記録。
- `source/repository_review_transcription_current.md`: runtime spec / package manifest boundary の提案とADR。
- `source/tabular_package_review_analysis.md`: `infer.py`, `pipeline.py`, `plots.py` の責務分割レビュー。
