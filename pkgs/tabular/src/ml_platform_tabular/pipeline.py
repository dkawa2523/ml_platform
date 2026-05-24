from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from ml_platform_core.artifacts import prepare_run_dir, update_latest, write_config_snapshot, write_manifest
from ml_platform_core.config import deep_merge, load_yaml
from ml_platform_core.io import write_json
from ml_platform_core.result import RunResult

from .evaluate import run_evaluate
from .infer import run_infer
from .train import run_train


def _load_nested_task(root_cfg: dict[str, Any], section: str) -> dict[str, Any]:
    section_cfg = root_cfg.get(section, {})
    task_path = section_cfg.get("task_config")
    if not task_path:
        raise ValueError(f"{section}.task_config is required for tabular_pipeline.")
    task_cfg = load_yaml(Path(task_path))

    inherited = {k: v for k, v in root_cfg.items() if k not in {"task", "train", "eval", "infer"}}
    section_overrides = {k: v for k, v in section_cfg.items() if k != "task_config"}
    # Task config is the default. Profile/root pipeline settings override shared fields.
    # Section-specific overrides win last.
    merged = deep_merge(deep_merge(task_cfg, inherited), section_overrides)
    for overrides in (inherited, section_overrides):
        model_overrides = overrides.get("model")
        if isinstance(model_overrides, dict) and "params" in model_overrides:
            merged.setdefault("model", {})["params"] = deepcopy(model_overrides["params"])
    return merged


def run_pipeline(cfg: dict[str, Any]) -> RunResult:
    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    run_name = cfg.get("run", {}).get("name", "tabular_pipeline")
    pipeline_dir = prepare_run_dir(output_dir, run_name)

    train_cfg = _load_nested_task(cfg, "train")
    train_result = run_train(train_cfg)

    eval_cfg = _load_nested_task(cfg, "eval")
    eval_cfg.setdefault("model", {})
    eval_cfg["model"]["artifact_path"] = str(train_result.artifacts["model"])
    eval_result = run_evaluate(eval_cfg)

    infer_cfg = _load_nested_task(cfg, "infer")
    infer_cfg.setdefault("model", {})
    infer_cfg["model"]["artifact_path"] = str(train_result.artifacts["model"])
    infer_result = run_infer(infer_cfg)

    metrics = {
        **{f"train_{k}": v for k, v in train_result.metrics.items()},
        **{f"eval_{k}": v for k, v in eval_result.metrics.items()},
    }
    summary = {
        "train_run_dir": str(train_result.run_dir),
        "eval_run_dir": str(eval_result.run_dir),
        "infer_run_dir": str(infer_result.run_dir),
        "model": str(train_result.artifacts["model"]),
        "predictions": str(infer_result.tables["predictions"]),
        "metrics": metrics,
    }

    summary_path = write_json(summary, pipeline_dir / "pipeline_summary.json")
    metrics_path = write_json(metrics, pipeline_dir / "metrics.json")
    config_path = write_config_snapshot(cfg, pipeline_dir)
    manifest_path = write_manifest(
        pipeline_dir,
        config=cfg,
        metrics=metrics,
        artifacts={
            "summary": summary_path,
            "metrics": metrics_path,
            "config": config_path,
            "model": train_result.artifacts["model"],
            "predictions": infer_result.tables["predictions"],
        },
    )
    update_latest(pipeline_dir, output_dir / "latest_pipeline")
    update_latest(pipeline_dir, output_dir / "latest")

    return RunResult(
        run_dir=pipeline_dir,
        metrics=metrics,
        artifacts={
            "model": train_result.artifacts["model"],
            "summary": summary_path,
            "metrics": metrics_path,
            "config": config_path,
            "manifest": manifest_path,
        },
        tables={
            "train_validation_predictions": train_result.tables["validation_predictions"],
            "eval_evaluation_predictions": eval_result.tables["evaluation_predictions"],
            "infer_predictions": infer_result.tables["predictions"],
        },
        extra=summary,
    )
