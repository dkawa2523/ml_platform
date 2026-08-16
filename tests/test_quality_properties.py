from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from ml_platform_core.io import dump_joblib, load_joblib
from ml_platform_tabular.data import train_valid_split
from ml_platform_tabular.metrics import regression_metrics, target_regression_metrics
from ml_platform_tabular.target_model_bundle import TargetModelBundle

FINITE_FLOATS = st.floats(
    min_value=-1e6,
    max_value=1e6,
    allow_nan=False,
    allow_infinity=False,
    width=64,
)


class _ArrayTransformer:
    def transform(self, X: pd.DataFrame) -> np.ndarray:
        return X.to_numpy(dtype=float)


@dataclass
class _AffinePredictor:
    scale: float
    offset: float

    def fit(self, X: np.ndarray, y: object) -> _AffinePredictor:
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return X[:, 0] * self.scale + self.offset


def _target_bundle(scale: float = 2.0, offset: float = 1.0) -> TargetModelBundle:
    return TargetModelBundle(
        transformer=_ArrayTransformer(),
        models={
            "temperature": _AffinePredictor(scale=scale, offset=offset),
            "pressure": _AffinePredictor(scale=-scale, offset=offset),
        },
        feature_columns=["x"],
    )


@given(st.lists(FINITE_FLOATS, min_size=2, max_size=50))
def test_regression_metrics_identity_is_finite_and_shape_safe(values):
    result = regression_metrics(values, values)

    assert set(result) == {"mae", "rmse", "r2"}
    assert all(np.isfinite(list(result.values())))
    assert result["mae"] == pytest.approx(0.0, rel=1e-12, abs=1e-12)
    assert result["rmse"] == pytest.approx(0.0, rel=1e-12, abs=1e-12)
    assert result["r2"] == pytest.approx(1.0, rel=1e-12, abs=1e-12)


@given(st.lists(FINITE_FLOATS, min_size=4, max_size=40), st.floats(-100, 100, allow_nan=False))
def test_target_metric_macro_is_equal_target_mean(values, offset):
    actual = np.asarray(values, dtype=float)
    prediction = actual + offset
    targets = np.asarray(["a" if index % 2 == 0 else "b" for index in range(len(actual))])

    aggregate, table = target_regression_metrics(actual, prediction, targets)
    expected = [regression_metrics(actual[targets == target], prediction[targets == target]) for target in ("a", "b")]

    assert set(table.columns) == {"target", "metric", "value", "observation_count"}
    for metric in ("mae", "rmse", "r2"):
        expected_macro = np.mean([item[metric] for item in expected])
        assert aggregate[metric] == pytest.approx(expected_macro, rel=1e-10, abs=1e-12)
        assert np.isfinite(aggregate[metric])


@given(
    group_count=st.integers(min_value=2, max_value=12),
    rows_per_group=st.integers(min_value=1, max_value=5),
    seed=st.integers(min_value=0, max_value=2**16),
)
def test_group_split_never_leaks_a_group(group_count, rows_per_group, seed):
    groups = [f"group-{group}" for group in range(group_count) for _ in range(rows_per_group)]
    frame = pd.DataFrame({"group": groups, "x": range(len(groups)), "target": range(len(groups))})
    X = frame[["x"]]
    y = frame["target"]
    cfg = {
        "run": {"seed": seed},
        "split": {"method": "group", "valid_size": 0.3, "group_column": "group"},
    }

    X_train, X_valid, _, _ = train_valid_split(X, y, cfg, df=frame)
    train_groups = set(frame.loc[X_train.index, "group"])
    valid_groups = set(frame.loc[X_valid.index, "group"])

    assert train_groups
    assert valid_groups
    assert train_groups.isdisjoint(valid_groups)


@given(
    targets=st.lists(st.sampled_from(("temperature", "pressure")), min_size=1, max_size=50),
    values=st.data(),
)
def test_target_bundle_preserves_row_order_dtype_and_shape(targets, values):
    x = values.draw(st.lists(FINITE_FLOATS, min_size=len(targets), max_size=len(targets)))
    frame = pd.DataFrame({"__target__": targets, "x": x}, index=list(reversed(range(len(targets)))))

    prediction = _target_bundle().predict(frame)
    expected = np.asarray(
        [
            2.0 * value + 1.0 if target == "temperature" else -2.0 * value + 1.0
            for target, value in zip(targets, x, strict=True)
        ],
        dtype=float,
    )

    assert prediction.shape == (len(frame),)
    assert prediction.dtype == np.dtype(float)
    np.testing.assert_allclose(prediction, expected, rtol=1e-12, atol=1e-12)


@given(st.text(min_size=1).filter(lambda value: value not in {"temperature", "pressure"}))
def test_target_bundle_rejects_every_unknown_target(target):
    frame = pd.DataFrame({"__target__": [target], "x": [1.0]})

    with pytest.raises(ValueError, match="Unknown target values"):
        _target_bundle().predict(frame)


@settings(max_examples=20)
@given(scale=st.floats(-10, 10, allow_nan=False), offset=st.floats(-10, 10, allow_nan=False))
def test_target_bundle_serialization_round_trip_preserves_predictions(scale, offset):
    frame = pd.DataFrame({"__target__": ["temperature", "pressure"], "x": [1.25, -3.5]})
    bundle = _target_bundle(scale=scale, offset=offset)
    before = bundle.predict(frame)

    with tempfile.TemporaryDirectory() as directory:
        path = dump_joblib(bundle, Path(directory) / "target-model.joblib")
        restored = load_joblib(path)

        assert isinstance(restored, TargetModelBundle)
        np.testing.assert_allclose(restored.predict(frame), before, rtol=1e-12, atol=1e-12)
