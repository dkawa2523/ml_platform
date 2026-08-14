from __future__ import annotations

from typing import Literal, TypeAlias, cast

StageName: TypeAlias = Literal[
    "preprocess_features",
    "train_model",
    "build_ensemble",
    "evaluate_models",
]

STAGE_NAMES: tuple[StageName, ...] = (
    "preprocess_features",
    "train_model",
    "build_ensemble",
    "evaluate_models",
)


def as_stage_name(value: str) -> StageName:
    """Validate and narrow a stage name while preserving serialized values."""
    if value in STAGE_NAMES:
        return cast(StageName, value)
    choices = ", ".join(STAGE_NAMES)
    raise ValueError(f"Unsupported tabular stage: {value}. Available: {choices}.")
