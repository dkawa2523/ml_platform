# Codex prompts

このファイルは、VS Codeで開いている `ml_platform` リポジトリのCodexへ貼るためのプロンプト集です。各Promptは、見出し直下の fenced block を丸ごとコピーしてCodexへ貼ってください。

---

## Prompt 0: Phase 0 review workspace setup

````text
あなたは、VS Codeで開いているこのリポジトリ `ml_platform` のレビュー対応支援エージェントです。

今回の目的:
- PR #28相当のレビューコメント R01〜R27 への対応を、このリポジトリ内で追跡できる状態にする。
- すでに配置された `docs/review` 配下のMarkdownを読み、現在repoの状態に合わせて内容を更新する。
- レビュー対応とレビュー外改善を混ぜない運用ルールを作る。
- 後で別Gitアカウント・別リポジトリへ cherry-pick / format-patch で移植しやすい状態にする。
- 初回では、大きなコード修正やリファクタは行わない。
- 初回では、Gitブランチ、レビュー対応表、作業ログ、環境ベースライン、ADR、移植手順、開発環境準備まで行う。

重要:
- 絶対に `git push` しない。
- secret, credential, ClearML API key, `.env` の中身は表示・作成・コミットしない。
- ClearML localhost UI はこの作業では検証しない。必要なら manual verification required と記録する。
- 本体コードの大規模変更、`clearml/pipelines.py`、`clearml/adapter.py`、`pkgs/tabular/...` のリファクタは初回では行わない。
- 依存インストールはプロジェクト環境に限定する。OS全体やグローバル環境を壊す操作はしない。
- 変更は小さく、あとで別repoに移植しやすくする。
- すべての作業結果はMarkdownに残す。

まず確認する:

```bash
git status --short
git branch --show-current
git remote -v
git log --oneline -n 20
```

未コミット変更がなければ、次を実行する:

```bash
git switch -c review/r00-setup-review-tracking
```

未コミット変更がある場合:
- 勝手にstashやcommitをしない。
- `docs/review/BASELINE_ENV_REPORT.md` に未コミット変更があることを記録する。
- 変更対象ファイル一覧を記録する。
- 作業は `docs/review` の更新に限定して続行してよい。

次の文書を読む:
- `docs/review/README.md`
- `docs/review/PR28_REVIEW_MAP.md`
- `docs/review/REVIEW_FIX_BRANCH_PLAN.md`
- `docs/review/LOCAL_SETUP_AND_GIT_COMMANDS.md`
- `docs/review/source/pr28_review_consolidated.md`
- `docs/review/source/repository_review_transcription_current.md`
- `docs/review/source/tabular_package_review_analysis.md`

環境確認コマンド:

```bash
python --version
python -m pip --version
uv --version || true
git ls-files .github .vscode docs pkgs clearml scripts pyproject.toml requirements.txt requirements-dev.txt uv.lock .pre-commit-config.yaml .gitlint .gitattributes '*.code-workspace'
find .github -maxdepth 3 -type f -print | sort || true
find .vscode -maxdepth 2 -type f -print | sort || true
python -m pytest --version || true
python -m ruff --version || true
python -m mypy --version || true
python -m pre_commit --version || true
python -m radon --version || true
python -m lint_imports --version || true
```

初回の検証コマンド:

```bash
python -m compileall clearml pkgs scripts
python -m pytest
```

pytestやlintが失敗した場合:
- 失敗内容を `BASELINE_ENV_REPORT.md` に要約する。
- 依存不足なら不足依存を記録する。
- 勝手に多数のライブラリを入れて修復しない。
- 次のPhaseで解決するTODOにする。

最後に必ず更新する:
- `docs/review/BASELINE_ENV_REPORT.md`
- `docs/review/CODEX_WORK_LOG.md`
- `docs/review/PR28_REVIEW_MAP.md`

最後に出力する:
1. 作成・更新したファイル一覧
2. 実行したコマンド
3. 成功したコマンド
4. 失敗したコマンド
5. 未確認事項
6. 次に実行すべきPhase 1の内容
7. 推奨commit message

推奨commit message:

```text
docs: add review response tracking scaffold

Review-Refs: R01-R27
Purpose: prepare traceable review response workflow before implementation
Portability: target-repo-sync
```
````

---

## Prompt 1: Phase 1 tooling and CI

````text
前回作成・更新した以下を読んでください。

- `docs/review/README.md`
- `docs/review/PR28_REVIEW_MAP.md`
- `docs/review/CODEX_WORK_LOG.md`
- `docs/review/BASELINE_ENV_REPORT.md`
- `docs/review/REVIEW_FIX_BRANCH_PLAN.md`
- `docs/review/source/pr28_review_consolidated.md`

今回の目的:
- Phase 1として、R01/R13/R14/R21/R22/R23/R24/R25 に対応する。
- 既存の品質ゲート、CI、pre-commit、gitlint、gitattributes、MkDocs workflow、VS Code設定、workspaceを復旧する。
- 本体コードの大規模リファクタはしない。
- uv移行、import再設計、ClearML runtime分離は次Phaseに回す。
- 変更内容はレビュー対応として `PR28_REVIEW_MAP.md` と `CODEX_WORK_LOG.md` に記録する。

対象レビュー:
- R01: ruff / ty / radon / import-linter など静的解析の復旧
- R13: GitHub Actions runner set を正しいものへ戻す
- R14: 共通CIを復旧し smoke workflow を分離
- R21: `.gitlint` / `.pre-commit-config.yaml` を復旧
- R22: `.gitattributes` を復旧
- R23: MkDocs deploy workflow を復旧
- R24: `.vscode/*` 共有設定を復旧
- R25: code-workspace を復旧

作業ルール:
1. pushしない。
2. secretを扱わない。
3. 変更前の設定がgit historyにある場合はそれを優先する。
4. 過去内容が見つからない場合は、現repoに合う最小構成を作り、`needs_confirmation` として記録する。
5. `ci.yml` と smoke workflow は役割を混ぜない。
6. runner set名は、レビュー元では `arc-runner-set-spdml-ml-pipeline` とされているが、このrepoで同じ名前が使えるか確認できない場合は TODO / needs_confirmation にする。
7. package共通CIとsmoke testを分離する。
8. pre-commitはRuff/format/基本チェックを最小構成で復旧する。
9. uv移行はR02なので今回は行わない。ただしR02で必要なTODOを残す。
10. 変更後に検証コマンドを実行し、結果を記録する。

まず実行する調査:

```bash
git status --short
git branch --show-current
git log --all --oneline -- .github/workflows .pre-commit-config.yaml .gitlint .gitattributes .vscode '*.code-workspace' pyproject.toml requirements-dev.txt
git ls-files .github .vscode docs .pre-commit-config.yaml .gitlint .gitattributes '*.code-workspace'
find .github -maxdepth 3 -type f -print | sort || true
find .vscode -maxdepth 2 -type f -print | sort || true
```

削除前ファイルを探す:

```bash
git log --all --name-status -- .github/workflows/ci.yml
git log --all --name-status -- .github/workflows/deploy-mkdocs.yml
git log --all --name-status -- .pre-commit-config.yaml
git log --all --name-status -- .gitlint
git log --all --name-status -- .gitattributes
git log --all --name-status -- .vscode
git log --all --name-status -- '*.code-workspace'
```

依存インストール方針:
- 既に必要ツールが入っていればそれを使う。
- 足りないdev toolsがある場合、今回は最小限のみプロジェクト環境へ入れる。
- requirements直編集ではなく、現状の依存管理方式に合わせる。
- uv移行はR02なので、ここでは無理にuv化しない。
- pre-commitを実行するために必要なら、現在の開発環境へ以下を入れてよい。ただし実行前に `CODEX_WORK_LOG.md` に記録する。

```bash
python -m pip install -r requirements-dev.txt
python -m pip install pre-commit gitlint ruff radon import-linter
```

検証:

```bash
python -m compileall clearml pkgs scripts
python -m pytest
python -m ruff check . || true
python -m ruff format --check . || true
python -m pre_commit run --all-files || true
```

最後に必ず更新:
- `docs/review/PR28_REVIEW_MAP.md`
- `docs/review/CODEX_WORK_LOG.md`
- `docs/review/BASELINE_ENV_REPORT.md`
- `docs/review/REVIEW_RESPONSE_DRAFTS.md`

推奨commit message:

```text
chore: restore review safety and developer tooling

Review-Refs: R01,R13,R14,R21,R22,R23,R24,R25
Portability: target-repo-sync
```
````

---

## Prompt 2: Phase 2 dependency/import/runtime package normalization

````text
Phase 2として、R02/R08/R16/R17に対応します。

目的:
- uv / pyproject / workspace で依存管理の正本を整理する。
- local `clearml` directory と official ClearML SDK のshadow問題を調査し、通常importへ寄せる。
- `_entrypoint_bootstrap.py` の手動 `sys.path` 操作を不要にする移行案を作る。
- importがファイル先頭に戻せる構成にする。

作業ルール:
- pushしない。
- secretを扱わない。
- 大規模renameはADRと互換方針を先に書く。
- `clearml/` をすぐrenameすると既存templateが壊れる可能性があるため、移行パスを明記する。
- 依存追加は `pyproject.toml` / uv方針へ寄せる。
- 変更後は `PR28_REVIEW_MAP.md` と `CODEX_WORK_LOG.md` を更新する。

調査:

```bash
git status --short
find . -maxdepth 3 -name 'pyproject.toml' -o -name 'uv.lock' -o -name 'requirements*.txt'
grep -R "sys.path\|_entrypoint_bootstrap\|import_clearml_sdk\|importlib.import_module(\"clearml\"" -n clearml pkgs scripts tests 2>/dev/null || true
grep -R "from adapter\|from pipelines\|import adapter\|import pipelines" -n clearml pkgs scripts tests 2>/dev/null || true
```

検証:

```bash
python -m compileall clearml pkgs scripts
python -m pytest
python -m ruff check . || true
```

推奨commit message例:

```text
build: prepare workspace dependency and import normalization

Review-Refs: R02,R08,R16,R17
Portability: target-repo-sync
```
````

---

## Prompt 3: Phase 3 types/config/adapter cleanup

````text
Phase 3として、R05/R06/R07/R09/R10/R11/R12/R15/R19/R20/R26/R27に対応します。

目的:
- ClearML adapterの型契約を明確化する。
- `Any`, 不要な `getattr`, 不要Optional, stage自由文字列を減らす。
- `UI`語彙を `runtime_params` / `connected_params` / `default_params` に整理する。
- table suffix判定、未使用alias、未使用Registryを整理する。
- typed config境界への段階移行計画を作る。

作業ルール:
- 1コミット1論点に分ける。
- 公開APIを変える場合は互換方針を明記する。
- R26は巨大なので、最初はschema調査と小さなtyped boundaryから始める。
- 変更後はテストと作業ログを更新する。

調査:

```bash
grep -R "Any\|getattr(\|ui_params\|ui_value\|default_ui_params\|as_list\|dataset_id: str | None\|Registry\|set_dotted_path\|TABLE_SUFFIXES" -n clearml pkgs scripts tests 2>/dev/null || true
python -m compileall clearml pkgs scripts
python -m pytest
```

推奨commit message例:

```text
refactor: tighten clearml adapter type contracts

Review-Refs: R05,R06,R07,R09,R10,R11,R12,R15
Portability: target-repo-sync
```
````

---

## Prompt 4: Phase 4 runtime manifest boundary

````text
Phase 4として、R18とADR 0002に対応します。

目的:
- runtime層からtabular固有policyを段階的に抽出する。
- core contracts, tabular manifest, runtime-neutral DomainPlan, ClearML renderer の境界を作る。
- 最初は既存挙動を変えず、contractとmanifestの雛形・validation testから着手する。

参照:
- `docs/review/ADR_0002_RUNTIME_SPEC_AND_PACKAGE_MANIFEST_BOUNDARY.md`
- `docs/review/source/repository_review_transcription_current.md`
- `docs/review/EXTRA_REVIEW_NOTES.md`

作業ルール:
- いきなり全面rewriteしない。
- `clearml/pipelines.py` の動作を壊さない。
- runtime側に残すものとtabular側へ移すものを表で記録する。
- ClearMLなしでmanifest validation testを先に書く。

推奨commit message例:

```text
feat: add runtime contracts and tabular manifest scaffold

Review-Refs: R18
Portability: target-repo-sync
```
````
