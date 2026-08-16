"""Preprocessing-stage orchestration."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from .artifacts import PreprocessResult
from .preprocess_artifacts import write_preprocess_outputs
from .preprocess_data import prepare_preprocess


def preprocess_features(cfg: dict[str, Any], pipeline_dir: Path) -> PreprocessResult:
    stage_dir = pipeline_dir / "preprocess_features"
    stage_dir.mkdir(parents=True, exist_ok=True)

    prepared = prepare_preprocess(cfg)
    artifacts, tables, plots = write_preprocess_outputs(prepared, stage_dir)
    return replace(prepared.result, artifacts=artifacts, tables=tables, plots=plots)
