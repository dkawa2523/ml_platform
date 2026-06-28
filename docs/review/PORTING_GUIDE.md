# Porting guide to target repository

この文書は、現在repoで作ったレビュー対応を、後で別Gitアカウント・別リポジトリのPRレビューへ反映するための手順です。

## 基本方針

- PRコメントを再現するのではなく、レビューIDに対応した小さいコミット列を正本にする。
- 各コミット本文に `Review-Refs: Rxx` を入れる。
- レビュー対応とレビュー外改善を混ぜない。
- 移植先でconflictした場合は、レビューID単位で解消する。
- 移植後、`docs/review/PR28_REVIEW_MAP.md` の `Commit` と `Porting note` を更新する。

## 推奨remote構成

```bash
git remote -v
git remote add target git@github.com:<other-account>/<other-repo>.git
git fetch --all --prune
```

## cherry-pick方式

履歴が近く、ファイル構成も大きく離れていない場合はこちらを使います。

```bash
git remote add target git@github.com:<other-account>/<other-repo>.git
git fetch --all --prune
git switch -c review-sync/pr28 target/feature/alfa_v1.00
git cherry-pick -x <commit-sha>
```

複数commitを順番に適用します。

```bash
git cherry-pick -x <r00-commit>
git cherry-pick -x <r01-commit-1> <r01-commit-2>
```

## patch方式

履歴が遠い、remoteを同一cloneに置きたくない、ファイル移動が多い場合はこちらを使います。

```bash
git format-patch main..review/r01-tooling-ci -o /tmp/review-r01
# target repo側で
git am -3 /tmp/review-r01/*.patch
```

Use `cherry-pick -x` when histories are close enough to preserve commit
identity. Use `format-patch` / `git am -3` when the target repository is a
separate clone, history is distant, or remote access should remain separate.

## ブランチ対応

| Current repo branch | Purpose | Target repo適用方針 |
|---|---|---|
| `review/r00-setup-review-tracking` | docs/review台帳とADR | 最初に適用 |
| `review/r01-tooling-ci` | CI・静的解析・pre-commit等 | 早期適用 |
| `review/r02-dependency-import-runtime` | uv/import/runtime package整理 | conflictが出やすいため単独適用 |
| `review/r03-types-config-adapter` | 型・config・adapter小粒修正 | 小さいcommitで順次適用 |
| `review/r04-runtime-manifest-boundary` | runtime manifest boundary | ADRとtest先行で適用 |
| `review/r05-tabular-characterization-tests` | 分割前の互換性テスト | module split前に必須 |
| `review/r06-tabular-module-split` | tabular分割 | 最後に適用 |
| `review/r07-clearml-k8s-evidence` | ClearML/K8s検証証跡 | 環境依存のためtarget側で再検証 |

## レビュー返信作成

移植先PRの返信には、以下を使います。

```text
Rxx対応:
- 対応内容: ...
- 対応commit: ...
- 検証: ...
- 移植時の差分: ...
```

## conflict時のルール

1. まず対象レビューIDを確認する。
2. そのレビューの意図を `source/pr28_review_consolidated.md` で確認する。
3. コード差分だけでなく、`PR28_REVIEW_MAP.md` の `Porting note` を更新する。
4. 仕様判断が必要なら `needs_confirmation` にして、推測で確定しない。
