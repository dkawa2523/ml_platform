# V1.3 ClearML Pipeline Summary

> Historical note: this file records the old fixed `train -> eval -> infer`
> compatibility pipeline. It is not current product readiness evidence for the
> stage-based training pipeline.

Date: 2026-05-25T23:24:46Z
Queue: default

| Pipeline | Status | Notes |
| --- | --- | --- |
| weighted ensemble historical compatibility train -> eval -> infer | pass | controller and all three step tasks completed |

Confirmed:

- Pipeline template count remained unchanged.
- Pipeline graph stayed as the historical compatibility fixed graph:
  `train -> eval -> infer`.
- Train step produced `leaderboard`, `ensemble_predictions`, selected `base_model_*`, and standard `model`.
- Eval and infer consumed the train step model artifact.
- Eval produced metrics and `evaluation_predictions`.
- Infer produced `predictions`.

Release compatibility pipeline gate: pass for that historical phase only.
