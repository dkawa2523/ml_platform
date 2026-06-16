import json

import pandas as pd

from ml_platform_tabular.data_quality import build_data_quality_report


def test_data_quality_report_warns_for_target_missing():
    df = pd.DataFrame({"id": [1, 2, 3], "x": [1.0, 2.0, 3.0], "target": [1.0, None, 3.0]})

    summary, _, warnings = build_data_quality_report(
        df,
        target_column="target",
        feature_columns=["x"],
        id_columns=["id"],
    )

    assert summary["target_missing_count"] == 1
    assert summary["target_missing_rate"] == 1 / 3
    assert "target_missing" in set(warnings["warning_type"])


def test_data_quality_report_warns_for_duplicate_ids():
    df = pd.DataFrame({"id": [1, 1, 2], "x": [1.0, 1.5, 2.0], "target": [1.0, 1.5, 2.0]})

    summary, _, warnings = build_data_quality_report(
        df,
        target_column="target",
        feature_columns=["x"],
        id_columns=["id"],
    )

    assert summary["id_duplicate_count"] == 2
    assert "duplicate_ids" in set(warnings["warning_type"])


def test_data_quality_report_detects_possible_leakage_columns():
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "x": [1.0, 2.0, 3.0],
            "future_prediction": [0.8, 1.8, 2.8],
            "target": [1.0, 2.0, 3.0],
        }
    )

    summary, _, warnings = build_data_quality_report(
        df,
        target_column="target",
        feature_columns=["x", "future_prediction"],
        id_columns=["id"],
    )

    assert summary["possible_leakage_columns"] == ["future_prediction"]
    assert "possible_leakage" in set(warnings["warning_type"])


def test_data_quality_report_summarizes_target_duplicates_and_leakage():
    df = pd.DataFrame(
        {
            "id": [1, 1, 2, 3, 4, 4],
            "x": [10, 10, 20, None, 40, 40],
            "segment": ["a", "a", "b", "c", "d", "d"],
            "target_score_hint": [0, 0, 1, 1, 0, 0],
            "target": ["1.0", "1.0", "2.0", None, "4.0", "4.0"],
        }
    )

    summary, summary_table, warnings = build_data_quality_report(
        df,
        target_column="target",
        feature_columns=["x", "segment", "target_score_hint"],
        id_columns=["id"],
    )

    assert summary["row_count"] == 6
    assert summary["column_count"] == 5
    assert summary["target_missing_count"] == 1
    assert summary["target_missing_rate"] == 1 / 6
    assert summary["target_is_numeric"] is True
    assert summary["duplicate_row_count"] == 4
    assert summary["id_duplicate_count"] == 4
    assert summary["feature_count"] == 3
    assert summary["numeric_feature_count"] == 2
    assert summary["categorical_feature_count"] == 1
    assert "x" in {item["column"] for item in summary["high_missing_columns"]}
    assert summary["possible_leakage_columns"] == ["target_score_hint"]
    assert set(summary_table.columns) == {"metric", "value"}
    assert set(warnings["warning_type"]) >= {
        "target_missing",
        "duplicate_rows",
        "duplicate_ids",
        "possible_leakage",
    }


def test_data_quality_report_limits_missing_and_cardinality_lists():
    rows = 60
    data = {
        "id": range(rows),
        "target": range(rows),
        "category": [f"value_{index}" for index in range(rows)],
    }
    for index in range(12):
        data[f"mostly_missing_{index:02d}"] = [None] * (index + 1) + list(range(rows - index - 1))
    df = pd.DataFrame(data)

    summary, summary_table, warnings = build_data_quality_report(
        df,
        target_column="target",
        feature_columns=["category", *[f"mostly_missing_{index:02d}" for index in range(12)]],
        id_columns=[],
    )

    assert len(summary["high_missing_columns"]) == 10
    assert summary["high_missing_columns"][0]["column"] == "mostly_missing_11"
    assert summary["high_cardinality_columns"] == [
        {"column": "category", "unique_count": rows, "non_missing_count": rows}
    ]
    encoded_lists = dict(zip(summary_table["metric"], summary_table["value"]))
    assert isinstance(json.loads(encoded_lists["high_missing_columns"]), list)
    assert "high_cardinality" in set(warnings["warning_type"])
