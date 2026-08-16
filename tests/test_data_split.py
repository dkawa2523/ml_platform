import pandas as pd
import pytest
from ml_platform_tabular.data import split_xy, train_valid_split


def _xy(df):
    return df[["x"]], df["target"]


def test_random_split_keeps_existing_deterministic_row_counts():
    df = pd.DataFrame({"x": range(10), "target": range(10)})
    X, y = _xy(df)
    cfg = {"run": {"seed": 7}, "split": {"method": "random", "valid_size": 0.3}}

    first = train_valid_split(X, y, cfg, df=df)
    second = train_valid_split(X, y, cfg, df=df)

    assert len(first[0]) == 7
    assert len(first[1]) == 3
    assert first[1].index.tolist() == second[1].index.tolist()


def test_group_split_keeps_groups_out_of_both_sides():
    df = pd.DataFrame(
        {
            "group": ["a", "a", "b", "b", "c", "c", "d", "d"],
            "x": range(8),
            "target": range(8),
        }
    )
    X, y = _xy(df)
    cfg = {"run": {"seed": 3}, "split": {"method": "group", "valid_size": 0.5, "group_column": "group"}}

    X_train, X_valid, _, _ = train_valid_split(X, y, cfg, df=df)

    train_groups = set(df.loc[X_train.index, "group"])
    valid_groups = set(df.loc[X_valid.index, "group"])
    assert train_groups
    assert valid_groups
    assert train_groups.isdisjoint(valid_groups)


def test_group_split_requires_at_least_two_groups():
    df = pd.DataFrame({"group": ["a", "a"], "x": [1, 2], "target": [1.0, 2.0]})
    X, y = _xy(df)
    cfg = {"split": {"method": "group", "valid_size": 0.5, "group_column": "group"}}

    with pytest.raises(ValueError, match="at least two distinct groups"):
        train_valid_split(X, y, cfg, df=df)


def test_time_split_uses_latest_rows_for_validation():
    df = pd.DataFrame(
        {
            "event_time": ["2024-01-03", "2024-01-01", "2024-01-04", "2024-01-02"],
            "x": [3, 1, 4, 2],
            "target": [30, 10, 40, 20],
        }
    )
    X, y = _xy(df)
    cfg = {"split": {"method": "time", "valid_size": 0.5, "time_column": "event_time"}}

    _, X_valid, _, y_valid = train_valid_split(X, y, cfg, df=df)

    assert X_valid["x"].tolist() == [3, 4]
    assert y_valid.tolist() == [30, 40]


def test_time_split_rejects_unparseable_dates():
    df = pd.DataFrame({"event_time": ["2024-01-01", "not-a-date"], "x": [1, 2], "target": [1, 2]})
    X, y = _xy(df)
    cfg = {"split": {"method": "time", "valid_size": 0.5, "time_column": "event_time"}}

    with pytest.raises(ValueError, match="cannot be parsed as datetimes"):
        train_valid_split(X, y, cfg, df=df)


def test_time_split_keeps_equal_timestamps_on_one_side():
    df = pd.DataFrame(
        {
            "event_time": ["2024-01-01", "2024-01-02", "2024-01-02", "2024-01-03"],
            "x": [1, 2, 3, 4],
            "target": [1, 2, 3, 4],
        }
    )
    X, y = _xy(df)
    cfg = {"split": {"method": "time", "valid_size": 0.5, "time_column": "event_time"}}

    X_train, X_valid, _, _ = train_valid_split(X, y, cfg, df=df)

    train_times = set(df.loc[X_train.index, "event_time"])
    valid_times = set(df.loc[X_valid.index, "event_time"])
    assert train_times.isdisjoint(valid_times)


def test_time_split_chooses_a_non_empty_distinct_timestamp_boundary():
    df = pd.DataFrame(
        {
            "event_time": ["2024-01-01"] * 90 + ["2024-01-02"] * 11,
            "x": range(101),
            "target": range(101),
        }
    )
    X, y = _xy(df)
    cfg = {"split": {"method": "time", "valid_size": 0.2, "time_column": "event_time"}}

    X_train, X_valid, _, _ = train_valid_split(X, y, cfg, df=df)

    assert len(X_train) == 90
    assert len(X_valid) == 11


def test_fixed_split_uses_filter_value_for_validation():
    df = pd.DataFrame({"split_flag": ["train", "valid", "train", "valid"], "x": [1, 2, 3, 4], "target": [1, 2, 3, 4]})
    X, y = _xy(df)
    cfg = {
        "split": {
            "method": "fixed",
            "valid_filter_column": "split_flag",
            "valid_filter_value": "valid",
        }
    }

    X_train, X_valid, _, _ = train_valid_split(X, y, cfg, df=df)

    assert X_train["x"].tolist() == [1, 3]
    assert X_valid["x"].tolist() == [2, 4]


def test_fixed_split_rejects_empty_train_or_valid():
    df = pd.DataFrame({"split_flag": ["valid", "valid"], "x": [1, 2], "target": [1, 2]})
    X, y = _xy(df)
    cfg = {
        "split": {
            "method": "fixed",
            "valid_filter_column": "split_flag",
            "valid_filter_value": "valid",
        }
    }

    with pytest.raises(ValueError, match="empty training split"):
        train_valid_split(X, y, cfg, df=df)


def test_explicit_features_reject_target_and_id_columns():
    df = pd.DataFrame({"id": [1, 2], "x": [3, 4], "target": [5, 6]})

    for protected_column in ("id", "target"):
        cfg = {
            "data": {
                "target_column": "target",
                "id_columns": ["id"],
                "feature_columns": ["x", protected_column],
            }
        }
        with pytest.raises(ValueError, match="cannot include target, ID, or split-control"):
            split_xy(df, cfg)


def test_split_control_column_is_not_a_default_feature():
    df = pd.DataFrame(
        {
            "split_flag": ["train", "valid"],
            "x": [1.0, 2.0],
            "target": [3.0, 4.0],
        }
    )
    cfg = {
        "data": {"target_column": "target"},
        "split": {
            "method": "fixed",
            "valid_filter_column": "split_flag",
            "valid_filter_value": "valid",
        },
    }

    _, _, features = split_xy(df, cfg)

    assert features == ["x"]


def test_target_must_be_finite_and_numeric():
    df = pd.DataFrame({"x": [1, 2], "target": ["bad", "2.0"]})

    with pytest.raises(ValueError, match="target_column must contain finite numeric values"):
        split_xy(df, {"data": {"target_column": "target"}})


@pytest.mark.parametrize(
    "target",
    [
        pd.Series(pd.to_datetime(["2024-01-01", "2024-01-02"])),
        pd.Series([1 + 2j, 3 + 4j]),
    ],
)
def test_target_rejects_datetime_and_complex_values(target):
    df = pd.DataFrame({"x": [1, 2], "target": target})

    with pytest.raises(ValueError, match="target_column must contain finite real numeric values"):
        split_xy(df, {"data": {"target_column": "target"}})
