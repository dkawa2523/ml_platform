import pandas as pd

from ml_platform_tabular.inference.prediction_frame import _prediction_frame
from ml_platform_tabular.inference.schema import _schema_check_summary


class _CategoryTransformer:
    category_levels = {"segment": ["a", "b"]}
    categorical_fill_values = {"segment": "__missing__"}


def test_infer_schema_check_missing_feature_is_error():
    df = pd.DataFrame({"id": [1, 2], "x1": [0.1, 0.2]})

    summary = _schema_check_summary(
        df,
        feature_columns=["x1", "x2"],
        id_columns=["id"],
        target_column=None,
        preprocess_bundle={},
    )

    assert summary["status"] == "error"
    assert summary["missing_features"] == ["x2"]
    assert summary["provided_feature_count"] == 1


def test_infer_schema_check_extra_column_is_warning():
    df = pd.DataFrame({"id": [1, 2], "x1": [0.1, 0.2], "note": ["new", "new"]})

    summary = _schema_check_summary(
        df,
        feature_columns=["x1"],
        id_columns=["id"],
        target_column=None,
        preprocess_bundle={},
    )

    assert summary["status"] == "warning"
    assert summary["extra_columns"] == ["note"]
    assert summary["missing_features"] == []


def test_infer_schema_check_unseen_category_is_warning_when_levels_available():
    df = pd.DataFrame({"id": [1, 2], "x1": [0.1, 0.2], "segment": ["a", "new"]})

    summary = _schema_check_summary(
        df,
        feature_columns=["x1", "segment"],
        id_columns=["id"],
        target_column=None,
        preprocess_bundle={"transformer": _CategoryTransformer()},
    )

    assert summary["status"] == "warning"
    assert summary["unknown_or_unseen_category_warning"] is True
    assert summary["unseen_category_columns"] == ["segment"]


def test_prediction_frame_keeps_row_index_and_id_without_copying_features():
    df = pd.DataFrame(
        {
            "id": [10, 11],
            "x1": [0.1, 0.2],
            "segment": ["a", "b"],
        },
        index=[5, 6],
    )

    predictions = _prediction_frame(
        df,
        [1.2, 1.4],
        id_columns=["id"],
        model_info={"model_name": "ridge", "artifact_kind": "model"},
        run_id="run-1",
        model_artifact_id="artifact-1",
    )

    assert predictions.columns.tolist() == [
        "row_index",
        "id",
        "prediction",
        "model_name",
        "artifact_kind",
        "model_artifact_id",
        "prediction_run_id",
    ]
    assert predictions["row_index"].tolist() == [5, 6]
    assert predictions["id"].tolist() == [10, 11]
    assert "x1" not in predictions.columns
    assert "segment" not in predictions.columns
