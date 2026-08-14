from __future__ import annotations

from pathlib import Path
from typing import Any

from ml_platform_core.artifacts import prepare_run_dir, update_latest, write_config_snapshot, write_manifest
from ml_platform_core.result import RunResult
from ml_platform_core.stages import StageName


def stage_run_dir(cfg: dict[str, Any], stage: StageName | str) -> Path:
    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    run_name = cfg.get("run", {}).get("name") or stage
    return prepare_run_dir(output_dir, run_name)


def finish_stage(
    cfg: dict[str, Any],
    run_dir: Path,
    *,
    metrics: dict[str, Any] | None,
    artifacts: dict[str, Path],
    tables: dict[str, Path] | None = None,
    plots: dict[str, Path] | None = None,
    extra: dict[str, Any] | None = None,
) -> RunResult:
    tables = tables or {}
    plots = plots or {}
    extra = extra or {}
    config_path = write_config_snapshot(cfg, run_dir)
    artifacts = {**artifacts, "config": config_path}
    manifest_path = write_manifest(
        run_dir,
        config=cfg,
        metrics=metrics or {},
        artifacts=artifacts,
        tables=tables,
        plots=plots,
        extra=extra,
    )
    artifacts["manifest"] = manifest_path
    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    if not cfg.get("runtime", {}).get("use_clearml"):
        update_latest(run_dir, output_dir / "latest_tabular_stage")
    return RunResult(
        run_dir=run_dir,
        metrics=metrics or {},
        artifacts=artifacts,
        tables=tables,
        plots=plots,
        extra=extra,
    )
