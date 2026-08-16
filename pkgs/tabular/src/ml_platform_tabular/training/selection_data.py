"""Create the model-selection holdout inside the training partition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from ..data import train_valid_split
from ..metrics import target_labels
from .artifacts import PreprocessResult


@dataclass(frozen=True)
class SelectionSplit:
    X_fit: pd.DataFrame
    X_selection: pd.DataFrame
    y_fit: pd.Series
    y_selection: pd.Series


def selection_split(cfg: dict[str, Any], preprocess: PreprocessResult) -> SelectionSplit:
    """Split training rows while leaving ``X_valid`` untouched for final evaluation."""
    split_cfg = dict(cfg.get("split", {}) or {})
    method = str(split_cfg.get("method") or "random").strip().lower()
    if method == "fixed":
        method = "random"
    split_cfg.update(
        method=method,
        valid_size=float(split_cfg.get("selection_size", 0.2)),
    )
    inner_cfg = {**cfg, "split": split_cfg}
    labels = target_labels(preprocess.X_train, preprocess.target_names)
    X_fit, X_selection, y_fit, y_selection = train_valid_split(
        preprocess.X_train,
        preprocess.y_train,
        inner_cfg,
        df=preprocess.X_train,
        coordinate_columns=preprocess.coordinate_columns or None,
        target_labels=labels,
    )
    return SelectionSplit(X_fit, X_selection, y_fit, y_selection)
