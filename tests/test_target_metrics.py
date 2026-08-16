import pandas as pd
import pytest
from ml_platform_tabular.metrics import target_means, target_regression_metrics
from ml_platform_tabular.selection import (
    higher_is_better,
    metric_settings,
    validate_target_selection_metric,
)


def test_target_metrics_use_equal_target_macro_and_keep_diagnostics_long():
    actual = [0.0, 2.0, 0.0, 200.0]
    prediction = [0.0, 1.0, 0.0, 100.0]
    targets = ["small", "small", "large", "large"]
    baselines = {"small": 0.0, "large": 0.0}

    aggregate, table = target_regression_metrics(
        actual,
        prediction,
        targets,
        metrics=["rmse", "relative_rmse", "skill"],
        baseline_means=baselines,
    )

    assert aggregate["rmse"] == pytest.approx((2**-0.5 + 5000**0.5) / 2)
    assert aggregate["relative_rmse"] == pytest.approx(0.5)
    assert aggregate["skill"] == pytest.approx(0.5)
    assert set(table["target"]) == {"small", "large", "__macro__"}
    assert {"baseline_rmse", "relative_rmse", "skill"} <= set(table["metric"])


def test_target_baselines_align_by_position_not_series_index():
    values = pd.Series([1.0, 3.0, 10.0, 14.0], index=[8, 3, 9, 1])
    targets = pd.Series(["a", "a", "b", "b"], index=[20, 21, 22, 23])

    assert target_means(values, targets) == {"a": 2.0, "b": 12.0}


def test_skill_is_a_supported_higher_is_better_selection_metric():
    selection_metric, metrics = metric_settings(
        {"metrics": {"names": ["mae"]}},
        {"selection_metric": "skill"},
    )

    assert selection_metric == "skill"
    assert metrics == ["mae", "rmse", "r2", "skill"]
    assert higher_is_better("skill") is True


def test_multiple_targets_reject_raw_scale_dependent_selection():
    with pytest.raises(ValueError, match="Multiple targets require"):
        validate_target_selection_metric("rmse", 2)

    validate_target_selection_metric("rmse", 1)
    validate_target_selection_metric("skill", 2)
