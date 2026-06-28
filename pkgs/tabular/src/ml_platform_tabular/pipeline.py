"""Compatibility facade for tabular training pipeline entrypoints."""

from __future__ import annotations

from .training import EvaluationResult, evaluate_model_candidates, run_pipeline

__all__ = ["EvaluationResult", "evaluate_model_candidates", "run_pipeline"]
