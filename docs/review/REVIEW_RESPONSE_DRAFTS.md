# Reviewer reply drafts

各レビューIDへの返信案です。初期状態では未対応のため、すべてdraftです。対応後にcommit SHAと検証結果を追記してください。

Prompt 0-B確認: R01〜R27の返信雛形はすべて `draft / not yet applied` のまま維持します。実装修正の完了扱いはまだ行いません。

## Prompt 1-A investigation update

Status: draft / investigation recorded / not yet applied

```text
Phase 1対象のR01/R13/R14/R21/R22/R23/R24/R25について、現repo履歴と現在ファイルを確認しました。
復旧候補として見つかったのは `.github/workflows/ci.yml` のみで、`647bcdf` と `6637119` を確認済みです。
`.pre-commit-config.yaml`, `.gitlint`, `.gitattributes`, `.vscode/*`, `*.code-workspace`, `smoke-test.yml`, `deploy-mkdocs.yml` の元内容は現repo履歴からは確認できませんでした。
現在の `ci.yml` は旧task configを参照しているため、Prompt 1-Bで共通CIと現行task用smoke workflowを分離する予定です。
runner setとMkDocs deploy先はこのrepoだけでは確定できないため、needs_confirmationとして扱います。
```


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

R04 final scope note:

```text
This initial draft is superseded by the final response summary below.
Kubernetes / K8 verification was intentionally excluded from this repository
cleanup. R04 is recorded as not_applicable; no kubectl, kustomize, helm,
cluster verification, rollout check, or Kubernetes manifest change was
performed in this branch.
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

## Prompt 1-B reviewer reply draft update

Status: draft / implementation prepared / pending commit

```text
Phase 1では、R01/R13/R14/R21/R22/R23/R24/R25 を対象に、実装コードのリファクタは行わず、CI・静的解析・pre-commit/gitlint・gitattributes・VS Code共有設定・code-workspace・MkDocs workflow を最小復旧しました。
```

- R01 draft: Ruff, radon, and import-linter were restored and now run locally. `ty` remains unresolved and is kept as `needs_confirmation`. Ruff currently reports existing E402/F841/F401 and format debt; those are not hidden and are routed to later cleanup phases.
- R13 draft: Workflows keep `ubuntu-latest` and include TODO comments because `arc-runner-set-spdml-ml-pipeline` cannot be confirmed from the local repository.
- R14 draft: `ci.yml` is restored as common package CI, and product smoke execution is split into `smoke-test.yml` using only existing `tabular_pipeline.yaml` and `tabular_infer.yaml`.
- R21 draft: `.pre-commit-config.yaml` and `.gitlint` are restored with minimal rules. Basic hooks pass when `.venv` is active; Ruff hooks expose existing code issues.
- R22 draft: `.gitattributes` is restored with conservative text and binary handling.
- R23 draft: MkDocs build/deploy workflow is restored, but GitHub Pages deployment target remains `needs_confirmation`.
- R24 draft: `.vscode` shared settings/extensions are restored without personal paths or secrets.
- R25 draft: `ml_platform.code-workspace` is restored with relative folders for repo root, `pkgs/core`, and `pkgs/tabular`.

## Prompt 2-B reviewer reply draft update

Status: draft / implementation prepared / pending commit

```text
Phase 2では、R02/R08/R16/R17 を対象に、root pyproject.toml を uv workspace の正本へ寄せ、uv.lock を生成しました。requirements.txt / requirements-dev.txt は Docker/ClearML remote と legacy pip setup の互換ファイルとして残しています。
```

- R02 draft: uv workspace, workspace package sources, clearml/gbm extras, dev/docs dependency groups, and `uv.lock` were added. CI, smoke, and MkDocs workflows now use `uv sync --frozen` and `uv run`. `gitlint` remains requirements-only because gitlint 0.19.x pins `sh==1.14.3`, which fails uv lock metadata build on Windows.
- R08 draft: `import_clearml_sdk()` remains for the local `clearml/` operations directory compatibility, but its error handling now distinguishes missing SDK, missing SDK dependencies, and import failures. Official ClearML SDK resolution was confirmed under uv.
- R16 draft: local script bootstrap was removed and Ruff no longer reports E402. ClearML direct-entrypoint files keep documented E402 ignores until the runtime entrypoint boundary moves in R18.
- R17 draft: `scripts/_bootstrap.py` was deleted and local scripts now rely on uv workspace/package-installed imports. `clearml/_entrypoint_bootstrap.py` remains intentionally because synced ClearML templates still execute `clearml/app.py` and `clearml/pipelines.py` directly.

## Prompt 3-B reviewer reply draft update

Status: draft / implementation prepared / pending commit

```text
Phase 3-Bでは、R05/R06/R07/R09/R10/R11/R12/R15/R19/R20/R27 を対象に、大規模config型付き化を避けた小粒修正を行いました。ClearML runtime parameter名への移行は互換wrapperを残して段階対応とし、R26のtyped config設計はPrompt 3-Cへ分けています。
```

- R05 draft: `apply_execution_image()` now accepts a narrow `ClearMLExecutionTask` Protocol instead of `Any`. Wider ClearML artifact/logger/config payload typing remains staged for R26 and later cleanup.
- R06 draft: stable task execution-image calls now use direct API calls with a legacy ClearML SDK fallback. Version-dependent SDK compatibility guards remain intentionally.
- R07 draft: stage values now go through shared `StageName` / `as_stage_name()` validation while preserving the existing serialized stage strings used in ClearML tags and artifacts.
- R09 draft: ClearML runtime availability is checked near entrypoints with `validate_clearml_runtime()`. Dataset existence is now a narrow `clearml_dataset_exists(dataset_id: str)` helper; localhost UI and remote behavior remain manual verification required.
- R10 draft: dataset IDs are narrowed before `Dataset.get()` and the standalone existence helper rejects empty IDs.
- R11 draft: `as_list()` was clarified as `as_str_list()` internally, with the old name kept as a deprecated compatibility wrapper.
- R12 draft: `_ui_value()` was renamed/documented as ClearML parameter transport normalization, preserving serialized parameter values.
- R15 draft: runtime parameter helpers (`default_runtime_params`, `grouped_runtime_params`, `apply_runtime_params`, `pipeline_runtime_params`) are now used internally. UI-named wrappers remain temporarily for compatibility.
- R19 draft: table suffix validation now uses one helper across direct file, preferred file, and recursive directory discovery paths.
- R20 draft: unused non-exported `set_dotted_path` alias was removed after repository-wide reference checks.
- R27 draft: unused `ml_platform_core.registry` was deleted and covered by a smoke test proving no public package surface depends on it.

Verification:
- `uv run python -m compileall clearml pkgs scripts`: passed.
- `uv run python -m pytest`: passed, 97 tests.
- Targeted Ruff check on changed ClearML/core/test files: passed.
- Full Ruff check still reports pre-existing out-of-scope F841/F401 in tabular files; broad format check still reports existing formatting debt.

## Prompt 3-C reviewer reply draft update

Status: draft / implementation prepared / pending commit

```text
R26について、まず外部YAML境界にdataclassベースのtyped config modelを導入しました。`load_run_config()` は既存どおりdictを返しますが、返却前にtyped parserで既知sectionをvalidationします。typed利用へ移るための新入口として `load_typed_run_config()` と `parse_run_config()` を追加し、下流の大規模rewriteは行っていません。
```

- Added `ConfigValidationError` for early, readable config failures.
- Added typed models for runtime, run, data, split, metrics, features, model/ensemble, output, base task, and full run config.
- Unknown keys are preserved as `extras` and round-trip through `RunConfig.to_dict()` so current YAML extension points are not broken.
- Existing dict compatibility is preserved: `load_run_config()` still returns a plain dict and keeps absent sections absent.
- Tests cover valid minimal config, default values, wrong-type failures, unknown-key preservation, override parsing, and `load_run_config()` compatibility.
- Verification: `uv run python -m pytest` passed 102 tests; compileall passed. Full Ruff still reports pre-existing out-of-scope F841/F401 and broad formatting debt.

## Prompt 4-A reviewer reply draft update

Status: draft / scaffold implemented / pending commit

```text
R18について、まず全面rewriteではなく、core contract と tabular manifest/policy の足場を追加しました。`pkgs/core` には runtime-facing な spec/plan 型を置き、`pkgs/tabular` には tabular の task/stage/pipeline manifest、model suite / quality preset policy、ClearML なしで構築できる `DomainPipelinePlan` を追加しています。既存の ClearML runtime 挙動はこの段階では変えず、次のPrompt 4-Bで `clearml/pipelines.py` が manifest/policy を読む方向へ段階接続します。
```

- Added core contracts: `ArtifactSpec`, `ParameterSpec`, `StageSpec`, `PipelineSpec`, `TaskSpec`, `PackageManifest`, `DomainStepPlan`, and `DomainPipelinePlan`.
- Added runtime adapter protocol scaffold in `ml_platform_core.runtime_types`.
- Added tabular-owned manifest and policy modules for tabular task/stage declarations, model suites, quality presets, and a runtime-neutral training graph plan.
- Added tests that validate manifest uniqueness, runner path resolution without ClearML, required artifacts/parameters, contract kind validation, policy preset copy safety, duplicate-key rejection, and `DomainPipelinePlan` construction.
- Verification: `uv run python -m pytest` passed 110 tests; `uv run python -m compileall clearml pkgs scripts` passed. Targeted Ruff/format for new files passed.
- Remaining R18 work: `clearml/pipelines.py` still contains tabular defaults and graph assembly until Prompt 4-B connects the ClearML renderer to the manifest.

## Prompt 4-B reviewer reply draft update

Status: draft / implementation prepared / pending commit

```text
R18について、tabular manifest / domain plan を ClearML runtime が消費する構造へ一段進めました。tabular model suite、quality preset、runtime parameter defaults、candidate/ensemble policy、training graph construction は `ml_platform_tabular.policy` / `ml_platform_tabular.manifest` 側へ移し、`clearml/pipelines.py` は `DomainPipelinePlan` を既存の ClearML `PipelineController` stepへrenderする責務に寄せています。既存のstage名、ClearML parameter key、direct entrypoint互換は維持しています。
```

- Runtimeから移したもの: model suite selection, quality mode preset application, default runtime parameter construction, candidate normalization, ensemble policy, and training graph/domain plan construction.
- Runtimeに残したもの: ClearML SDK access, PipelineController rendering, project/queue/tag wiring, task draft lifecycle, script metadata, artifact reference wiring, and direct `clearml/app.py` / `clearml/pipelines.py` entrypoint compatibility.
- Tests added/updated: domain plan override propagation in `tests/test_runtime_manifest.py`; fake-controller rendering/order check in `tests/test_clearml_mapping.py`.
- Verification: `uv run python -m compileall clearml pkgs scripts` passed; `uv run python -m pytest` passed 112 tests; targeted Ruff/format for changed R18 files passed.
- Remaining verification: ClearML localhost UI, ClearML remote execution, and Kubernetes behavior are manual verification required. Full Ruff still has pre-existing F841/F401 and broad format debt outside this R18 change.

## Prompt 5 TABULAR-SPLIT reviewer reply draft

Status: draft / characterization implemented / pending commit

```text
Before splitting the large tabular modules, I added ClearML-free
characterization coverage for the current training, inference, and plotting
contracts. The tests pin artifact/table/plot/metric key sets, leaderboard and
summary schemas, slim inference prediction columns, manifest/schema summary
fields, and standalone plot writer behavior on tiny seeded data. No production
module split is included in this step.
```

- Tests added: `tests/test_tabular_characterization.py`.
- Fixed contracts: training artifact/table/plot/metric keys; leaderboard,
  candidate prediction, evaluation prediction, decision summary, inference
  prediction, schema summary, prediction summary, source summary, and plot
  writer schemas.
- Remaining out of scope: exact numeric score goldens, optional GBM outputs,
  ClearML server/UI, ClearML remote execution, Kubernetes execution, and the
  actual module split.
- Verification: `uv run python -m pytest` passed 115 tests;
  `uv run python -m compileall clearml pkgs scripts` passed; targeted Ruff for
  the new test passed. Full Ruff still exposes pre-existing F841/F401 and broad
  format debt unrelated to this characterization step.

## Prompt 6 TABULAR-SPLIT plots split reviewer reply draft

Status: draft / plots split implemented / pending commit

```text
I split the tabular plotting implementation into a new `plotting` package with
domain-focused modules for common drawing helpers, feature plots, prediction
diagnostics, candidate comparison plots, leaderboard plots, and prediction
summary outputs. The existing `ml_platform_tabular.plots` module remains as a
compatibility facade, so old imports keep working while internal tabular code
now uses the new responsibility boundaries.
```

- New modules:
  - `ml_platform_tabular.plotting.common`
  - `ml_platform_tabular.plotting.feature`
  - `ml_platform_tabular.plotting.prediction`
  - `ml_platform_tabular.plotting.candidate`
  - `ml_platform_tabular.plotting.leaderboard`
  - `ml_platform_tabular.plotting.summary`
- Compatibility: `ml_platform_tabular.plots` still re-exports the existing
  public functions.
- Verification: characterization and plot tests passed; full pytest passed
  116 tests; `uv run python -m ruff check .` passed.
- Remaining split work: `infer.py` and `pipeline.py` still need staged
  compatibility-preserving splits.
- Known environment issue: prompt-style `python -m ...` still hits the Windows
  Store alias; `uv run python ...` is the verified project execution path.

## Final PR response summary - 2026-06-29, Kubernetes verification excluded

Status: final draft / integration branch `review/pr28-complete-response`

```text
R01-R27 と TABULAR-SPLIT について、Kubernetes / K8 実機検証を除外した
最終検証を行いました。コード基盤整理として対応済みの項目、外部設定のため
確認待ちの項目、今回スコープ外の項目を分けて記録しています。
```

### 対応済み

```text
R02, R05, R06, R07, R09, R10, R11, R12, R14, R19, R20, R21,
R22, R24, R25, R27, TABULAR-SPLIT は対応済みです。
```

- R02: `pyproject.toml` / uv workspace / `uv.lock` を正本にし、requirements
  は Docker/ClearML/legacy pip 互換ファイルとして残しました。
- R05/R06/R07/R09/R10/R11/R12/R15: ClearML adapter の型、命名、stage、
  dataset helper、runtime parameter 語彙を段階的に整理しました。
- R14/R21/R22/R24/R25: CI、smoke workflow、pre-commit/gitlint、
  `.gitattributes`、VS Code settings、workspace を復旧しました。
- R19/R20/R27: table suffix 判定、未使用 alias、未使用 Registry を整理しました。
- TABULAR-SPLIT: 分割前 characterization tests を追加したうえで、
  plotting / inference / training pipeline を責務別 module に分割し、
  `plots.py`, `infer.py`, `pipeline.py` の互換 facade を残しました。

検証:

```text
uv run python -m compileall clearml pkgs scripts
uv run python -m pytest
uv run python -m ruff check .
```

結果:

```text
compileall: passed
pytest: 117 passed
ruff check: passed
```

### 確認待ち / 段階対応

```text
R01, R03, R08, R13, R15, R16, R17, R18, R23, R26 は
追加確認または段階移行として残しています。
```

- R01: Ruff/radon/import-linter/pre-commit/gitlint は復旧済みです。`ty` は
  採用方針未確定のため未導入です。Ruff format debt は別途整理対象です。
- R03: 共通 Python code の thread env 設定を検索し、`clearml/app.py`,
  `scripts/local_run.py`, `scripts/make_sample_data.py` に残存を確認しました。
  実行環境側へ移す作業は今回の cleanup から deferred とします。
- R08/R17: local script bootstrap は削減済みですが、ClearML direct entrypoint
  互換のため `clearml/_entrypoint_bootstrap.py` と SDK shadow guard は残しています。
  ClearML remote template 実行確認後に削除判断します。
- R13: self-hosted runner `arc-runner-set-spdml-ml-pipeline` はローカル repo から
  利用可否を確認できないため、workflow は `ubuntu-latest` のまま TODO を残しました。
- R15: 内部語彙は `runtime_params` / `connected_params` 側へ寄せましたが、
  互換 wrapper と既存 tests には `ui_*` 名を残しています。
- R16: Ruff check は通過しています。ClearML direct-entrypoint files だけは
  bootstrap 互換のため import 順例外を明示しています。
- R18: runtime/package manifest boundary と ClearML renderer 化は実装済みです。
  ClearML localhost UI、remote Agent 実行、実 ClearML server 上の挙動は manual
  verification required です。
- R23: MkDocs build/deploy workflow は復旧済みですが、GitHub Pages 設定と
  deployment target は repository settings の確認が必要です。
- R26: typed config boundary は追加済みです。下流の `dict[str, Any]` 互換は
  段階移行のため残しています。

### R04 / Kubernetes scope

```text
今回のレビュー対応ではKubernetes実機検証は対象外とし、コード基盤整理から除外しました。
```

この cleanup branch では `kubectl`, `kustomize`, `helm`, Kubernetes manifest
変更、cluster rollout 確認、deploy/overlays 配下の実機検証を実行していません。
R04 は `not_applicable` として記録し、Kubernetes / K8 verification is
intentionally out of scope for this repository cleanup と明記しました。

### Known verification failures

```text
python -m compileall clearml pkgs scripts
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m pre_commit run --all-files
```

上記の prompt-style command はこの Windows 環境では PATH `python` が Windows
Store alias のため失敗します。project environment では `uv run python ...` を
使って検証しました。

```text
uv run python -m ruff format --check .
uv run python -m pre_commit run --all-files
```

これらは Ruff format debt により失敗します。対象は既存 16 files の整形差分で、
`ruff check` と pytest は通過しています。

### R18 response text

```text
ご指摘の runtime への tabular 固有知識集中について、core contracts と
tabular manifest / policy を追加し、ClearML runtime は DomainPipelinePlan を
PipelineController に render する責務へ寄せました。tabular model suite,
quality preset, runtime parameter defaults, candidate/ensemble policy,
training graph construction は tabular 側へ移しています。ClearML SDK 操作、
queue/project/tag、task draft lifecycle、script metadata、artifact reference
wiring は runtime 側に残しています。ClearML 実機確認は manual verification
required として残しています。
```

### TABULAR-SPLIT response text

```text
分割前に characterization tests を追加し、artifact/table/plot/metric keys,
leaderboard/summary schema, prediction frame columns, schema summary,
prediction manifest を固定しました。その後、plotting, inference, training
pipeline を責務別 package に分割し、既存 runner/import path を壊さないよう
compatibility facade を残しました。最終検証では 117 tests と Ruff check が
通過しています。
```

## Prompt 6 TABULAR-SPLIT inference split reviewer reply draft

Status: draft / inference split implemented / pending commit

```text
I split tabular inference into a new `inference` package with focused modules
for model resolution, metadata loading, schema checks, prediction frame
construction, prediction writing, and runner orchestration. The existing
`ml_platform_tabular.infer` module remains as a compatibility facade, so
`ml_platform_tabular.infer:run_infer` and current helper imports keep working
while the implementation now has clearer responsibility boundaries.
```

- New modules:
  - `ml_platform_tabular.inference.resolver`
  - `ml_platform_tabular.inference.metadata`
  - `ml_platform_tabular.inference.schema`
  - `ml_platform_tabular.inference.prediction_frame`
  - `ml_platform_tabular.inference.prediction_writer`
  - `ml_platform_tabular.inference.runner`
- Compatibility: `ml_platform_tabular.infer:run_infer` remains the ClearML and
  local runner path. `infer.py` also re-exports the private helpers currently
  used by tests, including `_prediction_frame` and `_schema_check_summary`.
- Preserved contracts: prediction output filename handling, slim prediction
  column order, schema check summary/table behavior, chunked CSV behavior, and
  inference manifest/source summary fields remain covered by characterization
  and smoke tests.
- Verification: targeted inference/characterization/smoke tests passed
  22 tests; full pytest passed 116 tests; `uv run python -m ruff check .`
  passed.
- Remaining split work: `pipeline.py` still needs a staged split after this
  facade-backed inference split.
- Known environment issue: prompt-style `python -m ...` still hits the Windows
  Store alias; `uv run python ...` is the verified project execution path.

## Prompt 6 TABULAR-SPLIT pipeline split reviewer reply draft

Status: draft / pipeline split implemented / pending commit

```text
I split the large tabular pipeline implementation into a new `training`
package with focused modules for preprocessing, candidate training, ensemble
construction, evaluation artifact generation, ranking, summary, and
orchestration. The existing `ml_platform_tabular.pipeline` module remains
as a compatibility facade, so `ml_platform_tabular.pipeline:run_pipeline`,
stage runner imports, and existing tests keep working while the implementation
has clearer boundaries.
```

- New modules:
  - `ml_platform_tabular.training.preprocessing`
  - `ml_platform_tabular.training.candidate_training`
  - `ml_platform_tabular.training.ensemble`
  - `ml_platform_tabular.training.evaluation`
  - `ml_platform_tabular.training.ranking`
  - `ml_platform_tabular.training.summary`
  - `ml_platform_tabular.training.artifacts`
  - `ml_platform_tabular.training.orchestrator`
- New artifact boundary: `EvaluationResult` is the typed/dataclass boundary for
  evaluate-models outputs. `evaluate_model_candidates()` returns it, and both
  pipeline and stage execution consume it directly.
- Compatibility: `ml_platform_tabular.pipeline:run_pipeline` remains the local
  and ClearML runner path. `pipeline.py` re-exports the private helpers still
  used by `stage.py` and current tests.
- Preserved contracts: training artifact/table/plot keys, leaderboard,
  evaluation/candidate predictions, decision summary, and manifest metrics
  remain covered by characterization and smoke tests.
- Verification: targeted decision/characterization/pipeline/stage tests passed
  22 tests; full pytest passed 117 tests; `uv run python -m ruff check .`
  passed.
- Remaining cleanup: compatibility facades and private re-exports can be reduced
  later after external imports and ClearML runner paths are migrated.
- Known environment issue: prompt-style `python -m ...` still hits the Windows
  Store alias; `uv run python ...` is the verified project execution path.
