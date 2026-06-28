# Review fix branch plan

## Branch overview

```text
review/r00-setup-review-tracking
review/r01-tooling-ci
review/r02-dependency-import-runtime
review/r03-types-config-adapter
review/r04-runtime-manifest-boundary
review/r05-tabular-characterization-tests
review/r06-tabular-module-split
review/r07-clearml-k8s-evidence
feature/non-review-improvements
```

## Prompt 0-B phase checklist

- Phase 0: review map, source docs, ADR, baseline
- Phase 1: R13/R14/R01/R21/R22/R23/R24/R25 tooling and CI
- Phase 2: R02/R08/R16/R17 dependency and import normalization
- Phase 3: R05/R06/R07/R09/R10/R11/R12/R15/R19/R20/R26/R27 types and config cleanup
- Phase 4: R18 runtime manifest boundary
- Phase 5: tabular characterization tests
- Phase 6: tabular module split
- Phase 7: R03/R04 ClearML/Kubernetes operational evidence

## Phase 0: review workspace and baseline

Branch: `review/r00-setup-review-tracking`

Scope:

- `docs/review/source/` に元レビュー資料を配置
- `PR28_REVIEW_MAP.md` を作成
- `CODEX_WORK_LOG.md` を作成
- `BASELINE_ENV_REPORT.md` を作成
- `PORTING_GUIDE.md` を作成
- `ADR_0002_RUNTIME_SPEC_AND_PACKAGE_MANIFEST_BOUNDARY.md` を配置
- コード本体は触らない

Suggested commit:

```text
docs: add review response tracking scaffold

Review-Refs: R01-R27
Purpose: prepare traceable review response workflow before implementation
Portability: target-repo-sync
```

## Phase 1: tooling and CI

Branch: `review/r01-tooling-ci`

Review IDs:

- R01, R13, R14, R21, R22, R23, R24, R25

Scope:

- 共通CI復旧
- smoke workflow分離
- runner set復旧
- ruff / ty / radon / import-linter の復旧方針整理
- `.pre-commit-config.yaml`, `.gitlint`, `.gitattributes`, `.vscode`, code-workspace復旧
- MkDocs deploy workflow復旧

## Phase 2: dependency and import normalization

Branch: `review/r02-dependency-import-runtime`

Review IDs:

- R02, R08, R16, R17

Scope:

- uv / pyproject / workspace構成
- official ClearML SDK shadow問題整理
- `_entrypoint_bootstrap.py` を不要にするpackage install方針
- importをファイル先頭へ戻す

## Phase 3: types, config, adapter cleanup

Branch: `review/r03-types-config-adapter`

Review IDs:

- R05, R06, R07, R09, R10, R11, R12, R15, R19, R20, R26, R27

Scope:

- `Any`削減
- `getattr`削減
- stage型付け
- ClearML設定検証とdataset存在確認の分離
- parameter語彙整理
- table suffix判定統一
- typed config境界導入
- unused alias / Registry整理

## Phase 4: runtime manifest boundary

Branch: `review/r04-runtime-manifest-boundary`

Review IDs:

- R18 and additional architecture review notes

Scope:

- core contracts
- tabular manifest
- runtime-neutral DomainPlan
- ClearML renderer
- `ui_*` 語彙を `runtime_params` / `connected_params` へ移行

## Phase 5: tabular characterization tests

Branch: `review/r05-tabular-characterization-tests`

Scope:

- 分割前に `infer.py`, `pipeline.py`, `plots.py` の現在出力を固定
- model resolution, schema validation, prediction frame, artifact names, metrics, plots を確認

## Phase 6: tabular module split

Branch: `review/r06-tabular-module-split`

Scope:

- `plots.py` を種類別に分割
- `infer.py` を resolver / metadata / schema / prediction_frame / writer / runner に分割
- `pipeline.py` を orchestrator / candidate_training / ensemble / evaluation / ranking / summary / recommendation / artifacts に分割
- 互換ファサードを必要最小限残す

## Phase 7: ClearML / Kubernetes evidence

Branch: `review/r07-clearml-k8s-evidence`

Review IDs:

- R03, R04

Scope:

- thread envを実行環境側へ移動
- Kubernetes target cluster検証証跡
- ClearML smoke結果記録
