from __future__ import annotations

import pytest
from ml_platform_core.io import dump_joblib, read_json
from ml_platform_tabular.model_artifact import (
    MODEL_ARTIFACT_SCHEMA_VERSION,
    validate_model_artifact,
    write_model_info,
)


def _write_artifact(tmp_path):
    model_path = dump_joblib({"coefficient": 1.0}, tmp_path / "model.joblib")
    info_path = write_model_info(
        tmp_path / "model_info.json",
        feature_columns=["x"],
        target_column="y",
        feature_preset="default",
        model_name="linear",
        model_path=model_path,
    )
    return model_path, read_json(info_path)


def test_model_artifact_integrity_is_recorded_and_verified(tmp_path):
    model_path, model_info = _write_artifact(tmp_path)

    assert model_info["model_artifact_schema_version"] == MODEL_ARTIFACT_SCHEMA_VERSION
    assert len(model_info["model_sha256"]) == 64
    validate_model_artifact(model_path, model_info, require_integrity=True)


def test_model_artifact_integrity_rejects_tampering_before_deserialization(tmp_path):
    model_path, model_info = _write_artifact(tmp_path)
    model_path.write_bytes(model_path.read_bytes() + b"tampered")

    with pytest.raises(ValueError, match="hash does not match"):
        validate_model_artifact(model_path, model_info, require_integrity=True)


def test_remote_model_artifact_requires_versioned_metadata(tmp_path):
    model_path = dump_joblib({"coefficient": 1.0}, tmp_path / "legacy.joblib")

    validate_model_artifact(model_path, {}, require_integrity=False)
    with pytest.raises(ValueError, match="schema version"):
        validate_model_artifact(model_path, {}, require_integrity=True)
