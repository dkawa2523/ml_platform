import pandas as pd

from ml_platform_tabular.data_quality import build_data_quality_report


def _report(df, *, features, numeric, categorical, ids=("id",)):
    return build_data_quality_report(
        df,
        target_column="target",
        feature_columns=list(features),
        numeric_columns=list(numeric),
        categorical_columns=list(categorical),
        id_columns=list(ids),
    )


def test_data_quality_report_warns_for_duplicate_ids():
    df = pd.DataFrame({"id": [1, 1, 2], "x": [1.0, 1.5, 2.0], "target": [1.0, 1.5, 2.0]})

    summary, warnings = _report(df, features=["x"], numeric=["x"], categorical=[])

    assert summary["id_duplicate_count"] == 2
    assert "duplicate_ids" in set(warnings["warning_type"])


def test_data_quality_report_uses_learned_feature_roles_without_name_heuristics():
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "future_prediction": ["1", "2", "3"],
            "segment": ["a", "b", "c"],
            "target": [1.0, 2.0, 3.0],
        }
    )

    summary, warnings = _report(
        df,
        features=["future_prediction", "segment"],
        numeric=[],
        categorical=["future_prediction", "segment"],
    )

    assert summary["numeric_feature_count"] == 0
    assert summary["categorical_feature_count"] == 2
    assert "possible_leakage" not in set(warnings["warning_type"])


def test_data_quality_report_summarizes_actionable_input_risks():
    rows = 60
    data = {
        "id": [0, 0, *range(2, rows)],
        "target": range(rows),
        "category": [f"value_{index}" for index in range(rows)],
    }
    for index in range(12):
        data[f"mostly_missing_{index:02d}"] = [None] * (index + 1) + list(range(rows - index - 1))
    df = pd.DataFrame(data)
    numeric = [f"mostly_missing_{index:02d}" for index in range(12)]

    summary, warnings = _report(
        df,
        features=["category", *numeric],
        numeric=numeric,
        categorical=["category"],
    )

    assert summary["row_count"] == rows
    assert summary["feature_count"] == 13
    assert len(summary["high_missing_columns"]) == 10
    assert summary["high_missing_columns"][0]["column"] == "mostly_missing_11"
    assert summary["high_cardinality_columns"] == [
        {"column": "category", "unique_count": rows, "non_missing_count": rows}
    ]
    assert set(warnings["warning_type"]) >= {"duplicate_ids", "high_cardinality"}
