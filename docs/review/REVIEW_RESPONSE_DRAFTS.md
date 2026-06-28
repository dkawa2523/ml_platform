# Reviewer reply drafts

各レビューIDへの返信案です。初期状態では未対応のため、すべてdraftです。対応後にcommit SHAと検証結果を追記してください。

Prompt 0-B確認: R01〜R27の返信雛形はすべて `draft / not yet applied` のまま維持します。実装修正の完了扱いはまだ行いません。


## R01 - ruff / ty / radon / import-linter 等の静的解析を復旧

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。ruff / ty / radon / import-linter 等の静的解析を復旧 の方針で対応します。
現在repoでは `review/r01-tooling-ci` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
pyproject.toml, requirements-dev.txt, .pre-commit-config.yaml, .github/workflows/*
```


## R02 - requirements中心から uv / pyproject / lock 管理へ移行

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。requirements中心から uv / pyproject / lock 管理へ移行 の方針で対応します。
現在repoでは `review/r02-dependency-import-runtime` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
pyproject.toml, uv.lock, requirements*.txt, package pyproject
```


## R03 - BLAS/OpenMP thread env を共通Pythonコードではなく実行環境側へ移動

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。BLAS/OpenMP thread env を共通Pythonコードではなく実行環境側へ移動 の方針で対応します。
現在repoでは `review/r07-clearml-k8s-evidence` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
clearml/app.py, .github/workflows/*, deploy/*
```


## R04 - 対象クラスタでの構成変更検証証跡を残す

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。対象クラスタでの構成変更検証証跡を残す の方針で対応します。
現在repoでは `review/r07-clearml-k8s-evidence` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
deploy/**, docs/review/*
```


## R05 - 明確な入力型の Any を Task または Protocol へ狭める

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。明確な入力型の Any を Task または Protocol へ狭める の方針で対応します。
現在repoでは `review/r03-types-config-adapter` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
clearml/adapter.py
```


## R06 - 予測可能APIへの getattr を通常属性アクセスへ変更

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。予測可能APIへの getattr を通常属性アクセスへ変更 の方針で対応します。
現在repoでは `review/r03-types-config-adapter` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
clearml/adapter.py
```


## R07 - stage自由文字列を Literal / StrEnum などで型付け

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。stage自由文字列を Literal / StrEnum などで型付け の方針で対応します。
現在repoでは `review/r03-types-config-adapter` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
clearml/adapter.py, core/runtime types
```


## R08 - ClearML SDK dynamic import / local clearml shadow 問題を整理

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。ClearML SDK dynamic import / local clearml shadow 問題を整理 の方針で対応します。
現在repoでは `review/r02-dependency-import-runtime` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
clearml/adapter.py, clearml/_entrypoint_bootstrap.py, pyproject.toml
```


## R09 - ClearML設定確認を下位関数からentrypoint近傍へ移動

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。ClearML設定確認を下位関数からentrypoint近傍へ移動 の方針で対応します。
現在repoでは `review/r03-types-config-adapter` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
clearml/adapter.py, clearml/app.py, clearml/templates.py
```


## R10 - None除外済み dataset_id は str に狭める

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。None除外済み dataset_id は str に狭める の方針で対応します。
現在repoでは `review/r03-types-config-adapter` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
clearml/adapter.py
```


## R11 - as_list を as_str_list 等へ改名

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。as_list を as_str_list 等へ改名 の方針で対応します。
現在repoでは `review/r03-types-config-adapter` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
clearml/adapter.py
```


## R12 - _ui_value の用途を名称/docstringで明確化

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。_ui_value の用途を名称/docstringで明確化 の方針で対応します。
現在repoでは `review/r03-types-config-adapter` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
clearml/adapter.py
```


## R13 - GitHub Actions runner set を正しいものへ戻す

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。GitHub Actions runner set を正しいものへ戻す の方針で対応します。
現在repoでは `review/r01-tooling-ci` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
.github/workflows/ci.yml
```


## R14 - 共通CIを復旧し smoke workflow を分離

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。共通CIを復旧し smoke workflow を分離 の方針で対応します。
現在repoでは `review/r01-tooling-ci` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
.github/workflows/ci.yml, .github/workflows/smoke-test.yml
```


## R15 - UI語彙を runtime_params / connected_params / default_params へ整理

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。UI語彙を runtime_params / connected_params / default_params へ整理 の方針で対応します。
現在repoでは `review/r03-types-config-adapter` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
clearml/adapter.py, clearml/pipelines.py, clearml/templates.py
```


## R16 - import をファイル先頭へ戻し Ruff 等で検査

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。import をファイル先頭へ戻し Ruff 等で検査 の方針で対応します。
現在repoでは `review/r02-dependency-import-runtime` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
clearml/templates.py
```


## R17 - 手動 sys.path 操作を package install / uv workspace で解消

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。手動 sys.path 操作を package install / uv workspace で解消 の方針で対応します。
現在repoでは `review/r02-dependency-import-runtime` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
clearml/_entrypoint_bootstrap.py, pyproject.toml
```


## R18 - 中央runtimeへ全packageが合流する構造を避けmanifest/provider境界へ

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。中央runtimeへ全packageが合流する構造を避けmanifest/provider境界へ の方針で対応します。
現在repoでは `review/r04-runtime-manifest-boundary` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
clearml/pipelines.py, pkgs/core, pkgs/tabular/manifest.py
```


## R19 - TABLE_SUFFIXES を直接指定・探索・glob の全経路で適用

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。TABLE_SUFFIXES を直接指定・探索・glob の全経路で適用 の方針で対応します。
現在repoでは `review/r03-types-config-adapter` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
pkgs/core/src/ml_platform_core/io.py
```


## R20 - 未使用の後方互換aliasを確認後削除

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。未使用の後方互換aliasを確認後削除 の方針で対応します。
現在repoでは `review/r03-types-config-adapter` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
pkgs/core/src/ml_platform_core/config.py
```


## R21 - .gitlint と .pre-commit-config.yaml を復旧

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。.gitlint と .pre-commit-config.yaml を復旧 の方針で対応します。
現在repoでは `review/r01-tooling-ci` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
.gitlint, .pre-commit-config.yaml
```


## R22 - .gitattributes を復旧

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。.gitattributes を復旧 の方針で対応します。
現在repoでは `review/r01-tooling-ci` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
.gitattributes
```


## R23 - MkDocs deploy workflow を復旧

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。MkDocs deploy workflow を復旧 の方針で対応します。
現在repoでは `review/r01-tooling-ci` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
.github/workflows/deploy-mkdocs.yml, mkdocs.yml
```


## R24 - VS Code共有設定を復旧

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。VS Code共有設定を復旧 の方針で対応します。
現在repoでは `review/r01-tooling-ci` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
.vscode/extensions.json, .vscode/settings.json
```


## R25 - package開発用 code-workspace を復旧

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。package開発用 code-workspace を復旧 の方針で対応します。
現在repoでは `review/r01-tooling-ci` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
*.code-workspace
```


## R26 - 巨大 dict[str, Any] config を dataclass / Pydantic 等の型付きモデルへ

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。巨大 dict[str, Any] config を dataclass / Pydantic 等の型付きモデルへ の方針で対応します。
現在repoでは `review/r03-types-config-adapter` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
pkgs/core/src/ml_platform_core/config.py, config consumers
```


## R27 - 未使用 Registry を削除、または実利用とテストを追加

Status: draft / not yet applied

返信案:

```text
ご指摘ありがとうございます。未使用 Registry を削除、または実利用とテストを追加 の方針で対応します。
現在repoでは `review/r03-types-config-adapter` で対応し、対応commit・検証結果・移植先での差分を `docs/review/PR28_REVIEW_MAP.md` に記録します。
完了後、実施内容と検証コマンドを追記して返信します。
```

Planned files:

```text
pkgs/core/src/ml_platform_core/registry.py
```
