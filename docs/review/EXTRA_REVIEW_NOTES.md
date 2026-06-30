## A11. TABULAR-SPLIT characterization before module split

Before splitting `pkgs/tabular/src/ml_platform_tabular/pipeline.py`,
`infer.py`, and `plots.py`, keep ClearML-free characterization tests that
pin the current output contracts:

- training artifact/table/plot/metric key sets
- leaderboard, evaluation predictions, candidate predictions, and decision
  summary schema
- inference slim prediction frame columns and manifest/schema summary fields
- standalone plot writer table and plot key behavior

Phase 6 should split in small steps: `plots.py` first, `infer.py` second,
typed result/artifact helper boundaries third, then `pipeline.py` orchestration.
Exact numeric model scores, optional GBM behavior, ClearML UI, ClearML remote,
and Kubernetes execution remain separate verification items.

## A12. TABULAR-SPLIT implementation notes after Phase 6

Phase 6 now keeps compatibility facades for the old public module paths:

- `ml_platform_tabular.plots`
- `ml_platform_tabular.infer`
- `ml_platform_tabular.pipeline`

The implementation has moved behind those facades:

- plotting behavior: `ml_platform_tabular.plotting.*`
- inference behavior: `ml_platform_tabular.inference.*`
- training behavior: `ml_platform_tabular.training.*`

`EvaluationResult` is the explicit typed boundary for evaluate-models outputs.
`evaluate_model_candidates()` returns this dataclass, and both full-pipeline and
stage execution now consume that boundary directly.

Future cleanup should migrate internal imports from private facade helpers to
public package functions, then remove private re-exports only after ClearML
runner paths and external import users are confirmed.

# Extra reviewer notes

この文書は、R01〜R27の公式レビューとは別に、現在repoをレビューワー視点で見たときに追加で検討したい改善点です。

## A01. runtime層のtabular固有知識が `pipelines.py` 以外にも散っている

`adapter.py`, `templates.py`, `app.py` にも project名、template名、tag、stage metadata などが散っている可能性があります。R18対応では `pipelines.py` だけでなく runtime層全体を確認してください。

## A02. PipelinePlan / StageStep / artifact and result contracts を型で表す

ClearML描画前のruntime-neutral planを `PipelinePlan`, `StageStep`,
`ArtifactSpec`, `ParameterSpec`, `RunResult` などの型で固定すると、
ClearMLなしのcontract testが書きやすくなります。

## A03. ClearML parameter schema の正本化

default値、parameter key、型変換、choices、説明文、config反映先が分散している場合、`ParameterSpec` を正本にして template生成・connect・apply・docsを同じschemaから生成します。

## A04. remote実行の再現性

ClearML task / pipeline templateには、少なくとも以下をmetadataまたはartifactとして残したいです。

- repo URL
- branch
- commit SHA
- dirty diff hash
- package versions
- lockfile hash
- artifact schema version

## A05. dependencyの正本統一

`pyproject.toml`, `uv.lock`, package extras, `requirements*.txt`, ClearML remote packages が別々の依存グラフにならないよう、R02で整理します。

## A06. artifact schema version

`model_info.json`, `feature_spec.json`, `preprocess_bundle`, `prediction_summary`, `decision_summary`, `manifest` に `schema_version` とrequired fieldsを持たせ、推論時に互換性を検証します。

## A07. pickle/joblib artifactの信頼境界

pickle系artifactを読み込む場合、信頼できないartifactをloadしないことをdocsと例外メッセージに明記します。関数名と実体がずれている場合は命名も見直します。

## A08. data leakage / split / feature schema test

target列混入、split leakage、train fit情報のvalid/test流出、inference schema mismatchをtest fixtureで固定します。

## A09. local / CI / ClearML remote entrypoint統一

local scripts と ClearML remote entrypoint の実行経路が違うと import / cwd / config resolution がずれます。将来的には console script または `python -m ...` に寄せます。

## A10. ClearMLなしのruntime adapter contract test

Fake PipelineController等で、manifestからClearML step定義が生成されることをテストします。E2E smokeは最小限にします。
