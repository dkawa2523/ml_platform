import pandas as pd

from ml_platform_tabular.inference.prediction_frame import _model_artifact_id, _prediction_frame
from ml_platform_tabular.inference.runner import _schema_transformer
from ml_platform_tabular.inference.schema import _required_feature_columns, _schema_check_summary


class _CategoryTransformer:
    category_levels = {"segment": ["a", "b"]}
    categorical_fill_values = {"segment": "__missing__"}


class _NumericTransformer:
    numeric_cols = ["x1"]
    passthrough_cols = []


class _PassthroughTransformer:
    numeric_cols = []
    passthrough_cols = ["x1"]


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


def test_infer_schema_check_invalid_numeric_value_is_error():
    df = pd.DataFrame({"id": [1, 2], "x1": ["corrupt", "2.0"]})

    summary = _schema_check_summary(
        df,
        feature_columns=["x1"],
        id_columns=["id"],
        target_column=None,
        preprocess_bundle={"transformer": _NumericTransformer()},
    )

    assert summary["status"] == "error"
    assert summary["invalid_numeric_features"] == ["x1"]


def test_infer_schema_check_passthrough_missing_value_is_error():
    df = pd.DataFrame({"id": [1, 2], "x1": [1.0, None]})

    summary = _schema_check_summary(
        df,
        feature_columns=["x1"],
        id_columns=["id"],
        target_column=None,
        preprocess_bundle={"transformer": _PassthroughTransformer()},
    )

    assert summary["status"] == "error"
    assert summary["invalid_numeric_features"] == ["x1"]


def test_required_features_reject_config_that_disagrees_with_trained_schema():
    try:
        _required_feature_columns(
            {"data": {"feature_columns": ["x2"]}},
            estimator=object(),
            model_info={"feature_columns": ["x1"]},
        )
    except ValueError as exc:
        assert "must match the trained model schema exactly" in str(exc)
    else:
        raise AssertionError("Expected mismatched inference schema to fail.")


def test_required_features_reject_disagreement_between_trained_artifacts():
    try:
        _required_feature_columns(
            {},
            estimator=type("Estimator", (), {"feature_columns": ["x1"]})(),
            model_info={"feature_columns": ["x2"]},
        )
    except ValueError as exc:
        assert "Trained model schema artifacts disagree" in str(exc)
    else:
        raise AssertionError("Expected trained schema disagreement to fail.")


def test_schema_check_uses_first_base_estimator_transformer_for_ensemble():
    base = type("BaseEstimator", (), {"transformer": _NumericTransformer()})()
    ensemble = type("EnsembleEstimator", (), {"estimators": [base]})()

    bundle = _schema_transformer(ensemble)

    assert isinstance(bundle["transformer"], _NumericTransformer)


def test_schema_check_prefers_estimator_transformer_over_stale_bundle():
    estimator = type("Estimator", (), {"transformer": _NumericTransformer()})()

    bundle = _schema_transformer(estimator)

    assert isinstance(bundle["transformer"], _NumericTransformer)


def test_model_artifact_id_hashes_model_bytes(tmp_path):
    first = tmp_path / "first.joblib"
    second = tmp_path / "second.joblib"
    first.write_bytes(b"model-a")
    second.write_bytes(b"model-b")

    assert _model_artifact_id(first) != _model_artifact_id(second)
    assert len(_model_artifact_id(first)) == 16


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
        coordinate_columns=[],
    )

    assert predictions.columns.tolist() == [
        "row_index",
        "id",
        "prediction",
    ]
    assert predictions["row_index"].tolist() == [5, 6]
    assert predictions["id"].tolist() == [10, 11]
    assert "x1" not in predictions.columns
    assert "segment" not in predictions.columns
