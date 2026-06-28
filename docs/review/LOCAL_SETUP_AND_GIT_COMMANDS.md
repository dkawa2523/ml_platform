# Local setup and Git commands

この文書は、VS Codeで開いているrepoに `docs/review` を配置した後に使うGit操作・依存確認・検証コマンド集です。

## 0. 配置直後の確認

```bash
git status --short
git diff --stat
```

## 1. Phase 0ブランチを作る

未コミット変更がない場合:

```bash
git switch main
git pull --ff-only
git switch -c review/r00-setup-review-tracking
```

すでにdocsを配置済みなら:

```bash
git status --short
git add docs/review
git commit -m "docs: add review response tracking scaffold"   -m "Review-Refs: R01-R27"   -m "Purpose: prepare traceable review response workflow before implementation"   -m "Portability: target-repo-sync"
```

## 2. Phase 1ブランチを作る

```bash
git switch main
git pull --ff-only
git switch -c review/r01-tooling-ci
git merge --no-ff review/r00-setup-review-tracking
```

## 3. 依存・ツール確認

```bash
python --version
python -m pip --version
uv --version || true
python -m pytest --version || true
python -m ruff --version || true
python -m pre_commit --version || true
python -m radon --version || true
python -m lint_imports --version || true
```

## 4. 最小検証

```bash
python -m compileall clearml pkgs scripts
python -m pytest
```

## 5. uvがある場合だけ試す

```bash
uv --version
uv sync --all-extras --dev || true
uv run pytest || true
```

`uv sync` が失敗しても、Phase 0では無理に直しません。R02で依存管理を整理します。

## 6. 必要ツールのインストール方針

原則:

- global環境を壊すinstallはしない。
- 既存のvenv / uv環境 / project-local環境を使う。
- `requirements.txt` 直編集はR02まで避ける。
- installしたら `CODEX_WORK_LOG.md` に記録する。

既存venvで最低限確認したい場合:

```bash
python -m pip install -r requirements-dev.txt
python -m pip install pre-commit gitlint ruff radon import-linter
```

uvを導入する場合の候補。実行前にチーム方針を確認してください。

```bash
python -m pip install --user uv
# or
pipx install uv
```

## 7. pre-commit / lint

設定ファイルが存在する場合のみ実行します。

```bash
python -m pre_commit run --all-files || true
python -m ruff check . || true
python -m ruff format --check . || true
```

## 8. 移植用remote

```bash
git remote add target git@github.com:<other-account>/<other-repo>.git
git fetch --all --prune
```

## 9. cherry-pick例

```bash
git switch -c review-sync/pr28 target/feature/alfa_v1.00
git cherry-pick -x <commit-sha>
```
