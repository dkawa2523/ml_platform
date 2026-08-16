from pathlib import Path

import ml_platform_tabular.target_sources as target_sources
import numpy as np
import pandas as pd
import pytest
from ml_platform_tabular.target_sources import (
    SOURCE_ROW_COLUMN,
    TARGET_COLUMN,
    VALUE_COLUMN,
    load_target_sources,
)


def _write_csv(root: Path, name: str, data: dict) -> None:
    pd.DataFrame(data).to_csv(root / name, index=False)


def _manifest(*targets: dict) -> dict:
    return {
        "schema_version": 1,
        "defaults": {
            "columns": {
                "x": "x",
                "time": "t",
                "value": "f",
            }
        },
        "targets": list(targets),
    }


def test_loads_sparse_target_files_without_aligning_their_coordinates(tmp_path):
    _write_csv(tmp_path, "temperature.csv", {"x": [0.0, 1.0], "t": [1, 2], "temperature": [10, 11]})
    _write_csv(tmp_path, "pressure.csv", {"X": [9.0], "timestamp": [4], "pressure": [100]})
    manifest = _manifest(
        {"name": "temperature", "file": "temperature.csv", "columns": {"value": "temperature"}},
        {
            "name": "pressure",
            "file": "pressure.csv",
            "columns": {"x": "X", "time": "timestamp", "value": "pressure"},
        },
    )

    observations = load_target_sources(tmp_path, manifest)

    assert observations.columns.tolist() == [
        TARGET_COLUMN,
        "x",
        "time",
        VALUE_COLUMN,
        SOURCE_ROW_COLUMN,
    ]
    assert len(observations) == 3
    assert observations[TARGET_COLUMN].tolist() == ["temperature", "temperature", "pressure"]
    assert observations["x"].tolist() == [0.0, 1.0, 9.0]
    assert observations[VALUE_COLUMN].tolist() == [10.0, 11.0, 100.0]
    assert observations[SOURCE_ROW_COLUMN].tolist() == [0, 1, 0]


def test_inference_sources_do_not_require_observed_values(tmp_path):
    _write_csv(tmp_path, "query.csv", {"x": [1, 2], "t": [3, 4]})

    observations = load_target_sources(
        tmp_path,
        _manifest({"name": "temperature", "file": "query.csv"}),
        require_values=False,
    )

    assert observations.columns.tolist() == [TARGET_COLUMN, "x", "time", SOURCE_ROW_COLUMN]
    assert observations[TARGET_COLUMN].tolist() == ["temperature", "temperature"]


def test_parquet_sources_use_the_shared_table_reader(tmp_path, monkeypatch):
    source = tmp_path / "target.parquet"
    source.write_bytes(b"table-reader-placeholder")

    def fake_read_table(path):
        assert path == source
        return pd.DataFrame({"x": [1], "t": [2], "f": [3]})

    monkeypatch.setattr(target_sources, "read_table", fake_read_table)

    observations = load_target_sources(tmp_path, _manifest({"name": "target", "file": source.name}))

    assert observations[VALUE_COLUMN].tolist() == [3.0]


@pytest.mark.parametrize("coordinate", [None, np.nan, np.inf, -np.inf])
def test_rejects_missing_or_non_finite_coordinates(tmp_path, coordinate):
    _write_csv(tmp_path, "target.csv", {"x": [0.0, coordinate], "t": [1, 2], "f": [3, 4]})

    with pytest.raises(ValueError, match="invalid coordinate 'x'"):
        load_target_sources(tmp_path, _manifest({"name": "target", "file": "target.csv"}))


@pytest.mark.parametrize("value", [None, np.nan, np.inf, -np.inf, "not-a-number"])
def test_rejects_missing_non_numeric_or_non_finite_values(tmp_path, value):
    _write_csv(tmp_path, "target.csv", {"x": [0, 1], "t": [1, 2], "f": [3, value]})

    with pytest.raises(ValueError, match="values must be finite numeric values"):
        load_target_sources(tmp_path, _manifest({"name": "target", "file": "target.csv"}))


def test_rejects_duplicate_coordinates_within_a_target(tmp_path):
    _write_csv(tmp_path, "target.csv", {"x": [1, 1], "t": [2, 2], "f": [3, 4]})

    with pytest.raises(ValueError, match="duplicate normalized coordinates"):
        load_target_sources(tmp_path, _manifest({"name": "target", "file": "target.csv"}))


def test_allows_the_same_coordinates_in_different_targets(tmp_path):
    _write_csv(tmp_path, "first.csv", {"x": [1], "t": [2], "f": [3]})
    _write_csv(tmp_path, "second.csv", {"x": [1], "t": [2], "f": [4]})

    observations = load_target_sources(
        tmp_path,
        _manifest(
            {"name": "first", "file": "first.csv"},
            {"name": "second", "file": "second.csv"},
        ),
    )

    assert len(observations) == 2


def test_rejects_duplicate_target_names_before_loading(tmp_path):
    manifest = _manifest(
        {"name": "same", "file": "missing-a.csv"},
        {"name": " same ", "file": "missing-b.csv"},
    )

    with pytest.raises(ValueError, match="Duplicate target name: same"):
        load_target_sources(tmp_path, manifest)


@pytest.mark.parametrize("relative_file", ["../outside.csv", "nested/../target.csv"])
def test_rejects_parent_path_traversal(tmp_path, relative_file):
    dataset_root = tmp_path / "dataset"
    dataset_root.mkdir()

    with pytest.raises(ValueError, match="must stay within the dataset root"):
        load_target_sources(dataset_root, _manifest({"name": "target", "file": relative_file}))


def test_rejects_absolute_source_paths(tmp_path):
    source = tmp_path / "target.csv"
    _write_csv(tmp_path, source.name, {"x": [1], "t": [2], "f": [3]})

    with pytest.raises(ValueError, match="must stay within the dataset root"):
        load_target_sources(tmp_path, _manifest({"name": "target", "file": str(source.resolve())}))


def test_rejects_missing_mapped_columns(tmp_path):
    _write_csv(tmp_path, "target.csv", {"x": [1], "f": [3]})

    with pytest.raises(ValueError, match=r"missing columns: \['t'\]"):
        load_target_sources(tmp_path, _manifest({"name": "target", "file": "target.csv"}))


def test_rejects_two_roles_mapped_to_the_same_source_column(tmp_path):
    manifest = _manifest(
        {
            "name": "target",
            "file": "target.csv",
            "columns": {"time": "x"},
        }
    )

    with pytest.raises(ValueError, match="maps multiple canonical columns"):
        load_target_sources(tmp_path, manifest)


@pytest.mark.parametrize(
    ("manifest", "message"),
    [
        ({}, "schema_version"),
        ({"schema_version": 1}, "manifest.defaults"),
        (
            {"schema_version": 1, "defaults": {"columns": {"value": "f"}}, "targets": [{"name": "a", "file": "a.csv"}]},
            "at least one coordinate",
        ),
        (
            {"schema_version": 1, "defaults": {"columns": {"x": "x", "value": "f"}}, "targets": []},
            "non-empty list",
        ),
    ],
)
def test_rejects_incomplete_manifests(tmp_path, manifest, message):
    with pytest.raises(ValueError, match=message):
        load_target_sources(tmp_path, manifest)
