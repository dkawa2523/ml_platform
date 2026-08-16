import numpy as np
import pandas as pd
import pytest
from ml_platform_tabular.features import build_feature_pipeline


def test_feature_transformer_basic_options():
    frame = pd.DataFrame({"num": [1.0, np.nan, 3.0], "cat": ["a", None, "a"]})

    transformer = build_feature_pipeline(
        "basic",
        frame,
        {
            "numeric_impute_strategy": "mean",
            "categorical_impute_strategy": "mode",
            "scaling": "none",
        },
    )

    assert transformer.numeric_fill_values["num"] == pytest.approx(2.0)
    assert transformer.categorical_fill_values["cat"] == "a"
    assert transformer.transform(frame)[:, 0].tolist() == pytest.approx([1.0, 2.0, 3.0])


def test_feature_transformer_drop_and_passthrough_rules():
    frame = pd.DataFrame(
        {
            "num": [1.0, 2.0, 3.0],
            "raw": [10.0, 20.0, 30.0],
            "cat": ["a", "b", "a"],
            "unused": [99.0, 99.0, 99.0],
        }
    )
    transformer = build_feature_pipeline(
        "basic",
        frame,
        {
            "categorical_encoder": "drop",
            "drop_columns": ["unused"],
            "passthrough_columns": ["raw"],
        },
    )

    assert transformer.categorical_cols == []
    assert transformer.passthrough_cols == ["raw"]
    assert "unused" not in transformer.feature_config["passthrough_columns"]
    assert transformer.transform(frame).shape[1] == 2
    with pytest.raises(ValueError, match="must be numeric"):
        build_feature_pipeline("basic", frame, {"passthrough_columns": ["cat"]})


def test_feature_transformer_uses_float32_and_guards_dense_allocation():
    frame = pd.DataFrame({"num": [1.0, 2.0, 3.0], "cat": ["a", "b", "c"]})
    transformer = build_feature_pipeline("basic", frame)

    assert transformer.transform(frame).dtype == np.float32

    guarded = build_feature_pipeline("basic", frame, {"max_dense_cells": 5})
    with pytest.raises(ValueError, match="max_dense_cells"):
        guarded.transform(frame)
