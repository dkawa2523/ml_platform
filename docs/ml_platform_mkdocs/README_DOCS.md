# ml_platform MkDocs ドキュメント一式

このディレクトリは、`dkawa2523/ml_platform` に追加できる MkDocs 形式のドキュメント一式です。

## 配置方法

リポジトリルートへ以下を配置してください。

```text
mkdocs.yml
requirements-docs.txt
docs/
```

既存 `docs/` をそのまま上書きせず、必要に応じて既存ファイルを退避または統合してください。

## プレビュー

```powershell
uv pip install -r requirements-docs.txt
mkdocs serve
```

## HTML ビルド

```powershell
mkdocs build --strict
```

## 注意

- Mermaid 図は MkDocs Material の `pymdownx.superfences` 設定を前提にしています。
- 数式は MathJax を利用します。外部 CDN が使えない環境では、`docs/javascripts/mathjax.js` と `mkdocs.yml` の `extra_javascript` を社内配布の MathJax に差し替えてください。
- 既存の `docs/SPEC.md`、`docs/CLEARML_UI_SPEC.md`、`docs/ROADMAP.md` の内容と整合するように構成していますが、実リポジトリへ適用する際は既存 docs との重複整理を行ってください。
