from __future__ import annotations

import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .io import write_json


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def prepare_run_dir(base_dir: str | Path, run_name: str | None = None) -> Path:
    base_dir = Path(base_dir)
    run_name = run_name or "run"
    run_dir = base_dir / f"{run_name}_{utc_timestamp()}"
    suffix = 1
    while run_dir.exists():
        run_dir = base_dir / f"{run_name}_{utc_timestamp()}_{suffix}"
        suffix += 1
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def update_latest(run_dir: str | Path, latest_dir: str | Path) -> None:
    """Copy a run directory to a latest-style directory.

    We use a copy instead of a symlink because ClearML Agent / Windows / mounted
    PVC environments often differ in symlink behavior.
    """
    run_dir = Path(run_dir)
    latest_dir = Path(latest_dir)
    if latest_dir.exists() or latest_dir.is_symlink():
        if latest_dir.is_symlink() or latest_dir.is_file():
            latest_dir.unlink()
        else:
            shutil.rmtree(latest_dir)
    shutil.copytree(run_dir, latest_dir)


def file_hash(path: str | Path) -> str:
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_config_snapshot(config: dict[str, Any], run_dir: str | Path) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / "config.yaml"
    path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def _artifact_entry(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    return {
        "path": str(p),
        "exists": p.exists(),
        "sha256": file_hash(p) if p.exists() and p.is_file() else None,
    }


def write_manifest(
    run_dir: str | Path,
    *,
    config: dict[str, Any],
    metrics: dict[str, Any] | None = None,
    artifacts: dict[str, str | Path] | None = None,
    tables: dict[str, str | Path] | None = None,
    plots: dict[str, str | Path] | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Write a small manifest for reproducibility and handoff inspection."""
    run_dir = Path(run_dir)
    manifest = {
        "created_at": utc_timestamp(),
        "task": config.get("task"),
        "profile": config.get("profile"),
        "run_name": config.get("run", {}).get("name"),
        "run_dir": str(run_dir),
        "config_meta": config.get("_meta", {}),
        "metrics": metrics or {},
        "artifacts": {name: _artifact_entry(path) for name, path in (artifacts or {}).items()},
        "tables": {name: _artifact_entry(path) for name, path in (tables or {}).items()},
        "plots": {name: _artifact_entry(path) for name, path in (plots or {}).items()},
        "extra": extra or {},
    }
    return write_json(manifest, run_dir / "manifest.json")
