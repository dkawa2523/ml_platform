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

## Final integration branch porting plan - 2026-06-29

Source branch:

```bash
review/pr28-complete-response
```

Kubernetes / K8 verification is intentionally out of scope for this repository
cleanup. Do not port R04 as part of this cleanup. Do not run or add `kubectl`,
`kustomize`, `helm`, rollout checks, cluster verification, or Kubernetes
manifest changes when applying this review-response branch.

### Recommended cherry-pick order

Use this order when histories are close enough for direct cherry-pick:

```bash
git cherry-pick -x 9faea03   # docs: initialize review response workspace
git cherry-pick -x 1728f08   # chore: restore review safety and developer tooling
git cherry-pick -x 86cbb1a   # build: normalize dependency and runtime import setup
git cherry-pick -x ba51813   # refactor: tighten adapter and core utility contracts
git cherry-pick -x f4fe03a   # feat: add runtime contracts and tabular manifest scaffold
git cherry-pick -x 0301d0e   # test: characterize tabular outputs before module split
git cherry-pick -x b96f622   # refactor: split tabular plotting responsibilities
git cherry-pick -x e5eda0a   # refactor: split tabular inference responsibilities
git cherry-pick -x 50c607a   # refactor: split tabular pipeline responsibilities
git cherry-pick -x f65ec99   # docs: finalize review response evidence without k8 scope
```

The final integration docs commit is:

```text
f65ec99 docs: finalize review response evidence without k8 scope
```

Do not cherry-pick a `review/r07-clearml-k8s-evidence` branch from this repo:
that branch was not available in the local or fetched branch set during final
integration.

### Commit range confirmation commands

Run these before porting so the target operator can see exactly what each
source branch contains. These ranges include merge commits because each review
branch was built on top of earlier review branches; for a clean linear port,
prefer the cherry-pick order above.

```bash
git log --oneline main..review/r00-setup-review-tracking
git log --oneline main..review/r01-tooling-ci
git log --oneline main..review/r02-dependency-import-runtime
git log --oneline main..review/r03-types-config-adapter
git log --oneline main..review/r04-runtime-manifest-boundary
git log --oneline main..review/r05-tabular-characterization-tests
git log --oneline main..review/r06-tabular-module-split
git log --oneline main..review/pr28-complete-response
```

Expected implementation commits from this source repo:

```text
9faea03 docs: initialize review response workspace
1728f08 chore: restore review safety and developer tooling
86cbb1a build: normalize dependency and runtime import setup
ba51813 refactor: tighten adapter and core utility contracts
f4fe03a feat: add runtime contracts and tabular manifest scaffold
0301d0e test: characterize tabular outputs before module split
b96f622 refactor: split tabular plotting responsibilities
e5eda0a refactor: split tabular inference responsibilities
50c607a refactor: split tabular pipeline responsibilities
f65ec99 docs: finalize review response evidence without k8 scope
```

### Cherry-pick command template

Do not run these commands in this source repo unless you are intentionally
working in the target clone. The `target` remote is shown only as a template.

```bash
git remote add target git@github.com:<other-account>/<other-repo>.git
git fetch --all --prune
git switch -c review-sync/pr28 target/feature/alfa_v1.00

git cherry-pick -x 9faea03
git cherry-pick -x 1728f08
git cherry-pick -x 86cbb1a
git cherry-pick -x ba51813
git cherry-pick -x f4fe03a
git cherry-pick -x 0301d0e
git cherry-pick -x b96f622
git cherry-pick -x e5eda0a
git cherry-pick -x 50c607a
git cherry-pick -x f65ec99
```

Do not cherry-pick:

```text
review/r07-clearml-k8s-evidence
Kubernetes / K8 verification docs
kubectl / kustomize / cluster evidence
R04 real-cluster verification work
```

### Conflict resolution order

Resolve conflicts in this order:

1. Review docs and ADR scaffolding.
2. Tooling and CI files.
3. `pyproject.toml`, `uv.lock`, and requirements compatibility notes.
4. ClearML adapter/import/runtime entrypoint files.
5. Core config models, contracts, stage and IO helpers.
6. Tabular manifest/policy.
7. Tabular characterization tests.
8. Tabular plotting, inference, and training module split.
9. Final review docs.

Keep review-external improvements out of this sequence. If target-only changes
are needed, make them in a separate commit after the review-response commits.

### Format-patch option

Use this when histories are distant or when the target repo is maintained in a
separate clone:

```bash
mkdir -p /tmp/ml-platform-review-patches
git format-patch main..review/r00-setup-review-tracking -o /tmp/ml-platform-review-patches/r00
git format-patch main..review/r01-tooling-ci -o /tmp/ml-platform-review-patches/r01
git format-patch main..review/r02-dependency-import-runtime -o /tmp/ml-platform-review-patches/r02
git format-patch main..review/r03-types-config-adapter -o /tmp/ml-platform-review-patches/r03
git format-patch main..review/r04-runtime-manifest-boundary -o /tmp/ml-platform-review-patches/r04
git format-patch main..review/r05-tabular-characterization-tests -o /tmp/ml-platform-review-patches/r05
git format-patch main..review/r06-tabular-module-split -o /tmp/ml-platform-review-patches/r06
git format-patch main..review/pr28-complete-response -o /tmp/ml-platform-review-patches/final

# In the target repo:
git am --3way /tmp/ml-platform-review-patches/r00/*.patch
git am --3way /tmp/ml-platform-review-patches/r01/*.patch
git am --3way /tmp/ml-platform-review-patches/r02/*.patch
git am --3way /tmp/ml-platform-review-patches/r03/*.patch
git am --3way /tmp/ml-platform-review-patches/r04/*.patch
git am --3way /tmp/ml-platform-review-patches/r05/*.patch
git am --3way /tmp/ml-platform-review-patches/r06/*.patch
git am --3way /tmp/ml-platform-review-patches/final/*.patch
```

If a patch conflicts, stop and resolve by review ID, not by broad file area.
Update the target repo's `docs/review/PR28_REVIEW_MAP.md` porting note if a
behavior differs.

Do not create patch directories for r07, k8, kubernetes, cluster evidence, or
R04 real-cluster verification. R04 is represented only by the final docs note
that Kubernetes verification is excluded.

### Conflict-prone files

Expect conflicts around these files first:

```text
pyproject.toml
uv.lock
requirements.txt
requirements-dev.txt
.github/workflows/ci.yml
.github/workflows/smoke-test.yml
.github/workflows/deploy-mkdocs.yml
clearml/adapter.py
clearml/app.py
clearml/pipelines.py
clearml/templates.py
pkgs/core/src/ml_platform_core/config.py
pkgs/core/src/ml_platform_core/config_models.py
pkgs/core/src/ml_platform_core/contracts.py
pkgs/core/src/ml_platform_core/io.py
pkgs/core/src/ml_platform_core/stages.py
pkgs/tabular/src/ml_platform_tabular/manifest.py
pkgs/tabular/src/ml_platform_tabular/policy.py
pkgs/tabular/src/ml_platform_tabular/plotting/*
pkgs/tabular/src/ml_platform_tabular/inference/*
pkgs/tabular/src/ml_platform_tabular/training/*
tests/test_clearml_mapping.py
tests/test_runtime_manifest.py
tests/test_tabular_characterization.py
docs/review/*
docs/adr/0002-runtime-spec-and-package-manifest-boundary.md
```

Resolve code conflicts before final docs conflicts. The final docs commit
should describe the target repo's actual status after any conflict-specific
adjustments.

### Target repo first checks

Before relying on the ported branch, check:

- `AGENTS.md`, `docs/SPEC.md`, `docs/CLEARML_UI_SPEC.md`, and
  `docs/ROADMAP.md` for product-boundary differences.
- Existing dependency source of truth: `pyproject.toml`, `uv.lock`,
  `requirements*.txt`, package pyprojects, and Docker/ClearML install commands.
- Existing GitHub workflows and required checks before replacing CI files.
- PATH `python` behavior. This source environment needs `uv run python ...`
  because `python` is the Windows Store alias.
- Active docs now use `uv sync --group dev`, `uv sync --group docs`, and
  `uv run python ...`. Keep `requirements*.txt` files only as compatibility
  inputs unless the target Docker/ClearML/docs setup has also migrated away
  from them.
- `uv --version` and lock resolution on the target OS.
- GitHub runner availability. `arc-runner-set-spdml-ml-pipeline` is still
  `needs_confirmation`.
- GitHub Pages settings/environment for MkDocs deploy. This is still
  `needs_confirmation`.
- ClearML SDK version, template entrypoint paths, and remote Agent working
  directory before deleting `clearml/_entrypoint_bootstrap.py`.
- ClearML localhost UI and remote execution for the R18 renderer boundary.
- External imports of `ml_platform_core.registry` or `set_dotted_path`; if the
  target repo has them, add a deprecation shim instead of deleting immediately.
- External imports of `ml_platform_tabular.plots`, `ml_platform_tabular.infer`,
  and `ml_platform_tabular.pipeline`; migrate them before deleting the old
  modules in a target repo.
- Repo-internal imports and runner paths should target
  `ml_platform_tabular.plotting`, `ml_platform_tabular.inference`, and
  `ml_platform_tabular.training`.

### PR response text reference

Use `docs/review/REVIEW_RESPONSE_DRAFTS.md`, section
`Final PR response summary - 2026-06-29, Kubernetes verification excluded`, as
the target PR reply base. For per-review evidence, use
`docs/review/PR28_REVIEW_MAP.md`, section
`Final validation status override - 2026-06-29, no K8 scope`.

### Exclusions

R04 is excluded from this cleanup and from target-repo porting. Record it as
`not_applicable` or handle it in a separate operational/Kubernetes evidence
branch owned by the deployment environment.

## Lean cleanup porting plan - 2026-06-29

Source branch:

```bash
cleanup/s00-lean-codebase-audit
```

Port the Lean cleanup after the PR review-response commits. These commits are
not Kubernetes / K8 work and should not be mixed with cluster verification.

Recommended cherry-pick order:

```bash
git cherry-pick -x 562fecc   # docs: add lean codebase simplification audit
git cherry-pick -x f37b856   # chore: remove confirmed unused code and stale compatibility
git cherry-pick -x b73cd7c   # refactor: simplify runtime contract surface
git cherry-pick -x 38c95de   # refactor: simplify diagnostics and error handling
git cherry-pick -x de61cdb   # refactor: simplify module facades and file responsibilities
git cherry-pick -x 8d3b726   # docs: prune obsolete setup and architecture notes
git cherry-pick -x <final-lean-completion-commit>
```

Lean cleanup conflict order:

1. `docs/review/SIMPLIFICATION_*` and `docs/adr/0003-lean-codebase-guidelines.md`.
2. Confirmed stale wrapper removals in `clearml/adapter.py`,
   `clearml/pipelines.py`, and `clearml/templates.py`.
3. Runtime contract simplification in `pkgs/core/src/ml_platform_core/contracts.py`
   and `pkgs/tabular/src/ml_platform_tabular/manifest.py`.
4. Diagnostics cleanup in `clearml/adapter.py` and `clearml/reports.py`.
5. Tabular runner path migration and facade deletion, plus related
   `plotting`, `inference`, `training`, and test imports.
6. Active docs setup and architecture notes.
7. Final Lean completion docs.

Target repo checks before deleting more code:

- Before porting tabular facade deletion, search for external or target-only
  imports of `ml_platform_tabular.plots`, `ml_platform_tabular.infer`, and
  `ml_platform_tabular.pipeline`, then migrate them to `plotting`,
  `inference`, or `training`.
- Verify ClearML remote Agent execution before deleting
  `clearml/_entrypoint_bootstrap.py` or renaming the `clearml/` directory.
- Verify Docker, ClearML remote setup, docs setup, and legacy pip usage before
  deleting `requirements*.txt` compatibility files.
- Run or temporarily install `vulture` before broad unused-code deletion.
- Run or temporarily install `deptry` before dependency pruning.
- Keep ruff formatting-only changes in a separate commit from behavior cleanup.

Do not port as part of Lean cleanup:

```text
Kubernetes / K8 verification
kubectl / kustomize / helm output
cluster rollout evidence
docs/review/source rewrites or deletions
```

## Second review response porting plan - 2026-06-30

Source branch:

```bash
cleanup/s00-lean-codebase-audit
```

Port the additional reviewer response after the PR28 response and Lean cleanup
commits. These are tracked separately as `SR01` through `SR10` and should not be
mixed back into the original `R01` through `R27` map.

Recommended cherry-pick order, once the commits exist:

```bash
git cherry-pick -x <second-review-map-commit>       # docs: add second review response map
git cherry-pick -x <sr01-params-commit>             # refactor: extract clearml parameter transport mapping
git cherry-pick -x <sr02-evaluation-writers-commit> # refactor: split tabular evaluation artifact writers
git cherry-pick -x <sr03-reporting-commit>          # refactor: report existing tabular plot artifacts in clearml runtime
git cherry-pick -x <sr05-config-compat-commit>      # refactor: move legacy config serialization out of RunConfig
git cherry-pick -x <sr06-optional-deps-commit>      # fix: narrow optional dependency import exceptions
git cherry-pick -x <second-review-final-commit>     # docs: finalize second review response evidence
```

If these changes are squashed before porting, preserve the order above inside
the squashed patch review: parameter transport first, evaluation writers second,
ClearML reporting after plot artifacts exist, config compatibility after typed
config is present, optional dependency exception narrowing independently, and
final docs last.

Second review conflict order:

1. `docs/review/SECOND_REVIEW_*` tracking files.
2. `clearml/params.py`, `clearml/adapter.py`, `clearml/pipelines.py`, and
   `tests/test_clearml_mapping.py` for SR01.
3. `pkgs/tabular/src/ml_platform_tabular/training/evaluation.py` plus
   `leaderboard_artifacts.py`, `prediction_artifacts.py`,
   `best_model_artifacts.py`, `decision_artifacts.py`, and
   `tests/test_evaluation_artifact_writers.py` for SR02.
4. `clearml/reports.py` and ClearML reporting tests for SR03.
5. `pkgs/core/src/ml_platform_core/config_models.py`,
   `pkgs/core/src/ml_platform_core/config_compat.py`, and
   `tests/test_config_models.py` for SR05.
6. `pkgs/tabular/src/ml_platform_tabular/models.py` and
   `tests/test_tabular_smoke.py` for SR06.
7. ADR and final response evidence docs.

Second review deferred items:

- SR04: do not delete `clearml/_entrypoint_bootstrap.py` until ClearML Remote
  Agent training and inference templates run successfully without direct
  entrypoint path injection.
- SR07: port tabular import and runner path migration before deleting
  `ml_platform_tabular.plots`, `ml_platform_tabular.infer`, and
  `ml_platform_tabular.pipeline` in a target repo.
- SR08: do not delete `requirements.txt` or `requirements-dev.txt` until Docker,
  ClearML remote setup, docs setup, CI, and onboarding paths are confirmed
  uv/pyproject-only.
- SR10: do not perform broad unused-code or dependency deletion until
  vulture/deptry have been run and false positives are recorded.

Second review validation baseline:

```powershell
uv run python -m compileall clearml pkgs scripts
uv run python -m pytest
uv run python -m ruff check .
uv run python -m ruff format --check .
uv run python -m pre_commit run --all-files
```

In this source environment, bare `python` resolves to the Windows Store alias.
Use `uv run python ...` as the canonical validation command unless the target
repo confirms a working `python` executable on PATH.
