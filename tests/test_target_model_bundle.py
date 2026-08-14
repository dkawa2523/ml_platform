from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pytest

from ml_platform_core.io import dump_joblib, load_joblib
from ml_platform_tabular.target_model_bundle import TargetModelBundle


class _IdentityTransformer:
    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        return frame.to_numpy(dtype=float)


@dataclass
class _LinearPredictor:
    scale: float
    offset: float

    def fit(self, X: object, y: object) -> "_LinearPredictor":
        return self

    def predict(self, X: object) -> np.ndarray:
        values = np.asarray(X)
        return values[:, 0] * self.scale + self.offset


class _TwoDimensionalPredictor:
    def fit(self, X: object, y: object) -> "_TwoDimensionalPredictor":
        return self

    def predict(self, X: object) -> np.ndarray:
        return np.zeros((len(np.asarray(X)), 1))


def _bundle(**overrides) -> TargetModelBundle:
    values = {
        "transformer": _IdentityTransformer(),
        "models": {
            "temperature": _LinearPredictor(scale=2.0, offset=1.0),
            "pressure": _LinearPredictor(scale=-1.0, offset=10.0),
        },
        "feature_columns": ["x", "t"],
    }
    values.update(overrides)
    return TargetModelBundle(**values)


def test_predicts_each_target_and_preserves_interleaved_input_order():
    frame = pd.DataFrame(
        {
            "__target__": ["pressure", "temperature", "pressure", "temperature"],
            "x": [2.0, 3.0, 5.0, 7.0],
            "t": [0.0, 1.0, 2.0, 3.0],
        },
        index=[40, 10, 40, 20],
    )

    predictions = _bundle().predict(frame)

    np.testing.assert_allclose(predictions, [8.0, 7.0, 5.0, 15.0])
    assert predictions.shape == (len(frame),)


def test_scalar_bundle_predicts_legacy_frame_without_target_column():
    frame = pd.DataFrame({"x": [1.0, 4.0], "t": [0.0, 2.0]})
    model = _LinearPredictor(scale=2.0, offset=1.0)
    bundle = _bundle(models={"temperature": model})

    np.testing.assert_allclose(bundle.predict(frame), [3.0, 9.0])
    assert bundle.model is model


def test_multi_target_bundle_has_no_legacy_scalar_model():
    assert _bundle().model is None


@pytest.mark.parametrize(
    ("frame", "message"),
    [
        (pd.DataFrame({"x": [1.0], "t": [0.0]}), "missing required columns: ['__target__']"),
        (
            pd.DataFrame({"__target__": ["temperature"], "x": [1.0]}),
            "missing required columns: ['t']",
        ),
    ],
)
def test_rejects_missing_required_columns(frame, message):
    with pytest.raises(ValueError, match=message.replace("[", r"\[").replace("]", r"\]")):
        _bundle().predict(frame)


def test_rejects_unknown_or_missing_target_values():
    unknown = pd.DataFrame({"__target__": ["humidity"], "x": [1.0], "t": [0.0]})
    missing = pd.DataFrame({"__target__": [None], "x": [1.0], "t": [0.0]})

    with pytest.raises(ValueError, match="Unknown target values: 'humidity'"):
        _bundle().predict(unknown)
    with pytest.raises(ValueError, match="contains missing values in target column"):
        _bundle().predict(missing)


def test_rejects_non_scalar_model_predictions():
    frame = pd.DataFrame({"__target__": ["temperature"], "x": [1.0], "t": [0.0]})
    bundle = _bundle(models={"temperature": _TwoDimensionalPredictor()})

    with pytest.raises(ValueError, match=r"shape \(1, 1\); expected \(1,\)"):
        bundle.predict(frame)


def test_bundle_round_trips_through_model_artifact_serialization(tmp_path):
    frame = pd.DataFrame({"x": [3.0, 2.0], "t": [1.0, 0.0]})
    model = _LinearPredictor(scale=2.0, offset=1.0)
    path = dump_joblib(_bundle(models={"temperature": model}), tmp_path / "target_bundle.joblib")

    loaded = load_joblib(path)

    assert isinstance(loaded, TargetModelBundle)
    np.testing.assert_allclose(loaded.predict(frame), [7.0, 5.0])
    assert loaded.model is not None
