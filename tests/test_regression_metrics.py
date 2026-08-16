import numpy as np
import pytest
from ml_platform_tabular.metrics import regression_metrics


def test_regression_metrics_can_select_mse():
    values = regression_metrics([1.0, 2.0, 3.0], [1.0, 2.0, 5.0], metrics=["mse", "rmse"])
    assert list(values) == ["mse", "rmse"]
    assert values["mse"] == pytest.approx(4.0 / 3.0)

    from_string = regression_metrics([1.0, 2.0], [1.0, 4.0], metrics="mse,rmse")
    assert list(from_string) == ["mse", "rmse"]


def test_regression_metrics_constant_target_distinguishes_perfect_prediction():
    assert regression_metrics([5.0, 5.0], [5.0, 5.0])["r2"] == 1.0
    assert regression_metrics([5.0, 5.0], [4.0, 5.0])["r2"] == 0.0


def test_regression_metrics_rejects_non_finite_values_and_single_sample_r2():
    with pytest.raises(ValueError, match="finite values"):
        regression_metrics([1.0, 2.0], [1.0, np.inf])
    with pytest.raises(ValueError, match="r2 requires at least two samples"):
        regression_metrics([1.0], [1.0])
    assert regression_metrics([1.0], [1.0], metrics=["mae"]) == {"mae": 0.0}


def test_regression_metrics_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="same length"):
        regression_metrics([1.0, 2.0], [1.0])
    with pytest.raises(ValueError, match="must not be empty"):
        regression_metrics([], [])
    with pytest.raises(ValueError, match="At least one"):
        regression_metrics([1.0], [1.0], metrics=[])
    with pytest.raises(ValueError, match="Unsupported regression metric"):
        regression_metrics([1.0, 2.0], [1.0, 2.0], metrics=["median-error"])
