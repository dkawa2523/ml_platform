from __future__ import annotations

import math
from collections.abc import Mapping
from numbers import Complex, Number, Real
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml_platform_core.io import read_table

TARGET_COLUMN = "__target__"
VALUE_COLUMN = "__value__"
SOURCE_ROW_COLUMN = "__source_row__"
_RESERVED_COLUMNS = {TARGET_COLUMN, VALUE_COLUMN, SOURCE_ROW_COLUMN, "value", "target", "source_row"}


def load_target_sources(
    dataset_root: str | Path,
    manifest: Mapping[str, Any],
    *,
    require_values: bool = True,
) -> pd.DataFrame:
    """Load independent target tables as sparse, canonical observations.

    ``manifest`` is a YAML/JSON-loaded mapping. ``defaults.columns`` maps
    canonical coordinate names to source columns and uses ``value`` for the
    observed target column. Each target may override source column names while
    keeping the same canonical coordinate schema.
    """
    root = _dataset_root(dataset_root)
    coordinate_columns, sources = _source_specs(manifest)
    frames = [
        _load_source(
            root,
            target_name,
            relative_file,
            columns,
            coordinate_columns,
            require_values=require_values,
        )
        for target_name, relative_file, columns in sources
    ]
    result_columns = [TARGET_COLUMN, *coordinate_columns]
    if require_values:
        result_columns.append(VALUE_COLUMN)
    result_columns.append(SOURCE_ROW_COLUMN)
    return pd.concat(frames, ignore_index=True)[result_columns]


def _dataset_root(dataset_root: str | Path) -> Path:
    root = Path(dataset_root).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Target dataset root not found: {root}")
    if not root.is_dir():
        raise ValueError(f"Target dataset root must be a directory: {root}")
    return root


def _source_specs(
    manifest: Mapping[str, Any],
) -> tuple[tuple[str, ...], list[tuple[str, str, dict[str, str]]]]:
    if not isinstance(manifest, Mapping):
        raise TypeError("target source manifest must be a mapping.")
    if manifest.get("schema_version") != 1:
        raise ValueError("target source manifest schema_version must be 1.")

    defaults = _required_mapping(manifest.get("defaults"), "manifest.defaults")
    default_columns = _column_mapping(
        _required_mapping(defaults.get("columns"), "manifest.defaults.columns"),
        "manifest.defaults.columns",
    )
    if "value" not in default_columns:
        raise ValueError("manifest.defaults.columns.value is required.")

    coordinate_columns = tuple(name for name in default_columns if name != "value")
    if not coordinate_columns:
        raise ValueError("manifest.defaults.columns requires at least one coordinate column.")

    targets = manifest.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("manifest.targets must be a non-empty list.")

    seen_names: set[str] = set()
    sources: list[tuple[str, str, dict[str, str]]] = []
    for index, raw_target in enumerate(targets):
        context = f"manifest.targets[{index}]"
        target = _required_mapping(raw_target, context)
        name = _required_name(target.get("name"), f"{context}.name")
        if name in seen_names:
            raise ValueError(f"Duplicate target name: {name}")
        seen_names.add(name)

        relative_file = _required_name(target.get("file"), f"{context}.file")
        overrides = _column_mapping(
            _required_mapping(target.get("columns", {}), f"{context}.columns"),
            f"{context}.columns",
        )
        unknown_roles = sorted(set(overrides) - set(default_columns))
        if unknown_roles:
            raise ValueError(f"{context}.columns contains unknown canonical columns: {unknown_roles}")
        columns = {**default_columns, **overrides}
        _validate_distinct_source_columns(columns, context)
        sources.append((name, relative_file, columns))

    return coordinate_columns, sources


def _required_mapping(value: Any, setting: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{setting} must be a mapping.")
    return value


def _required_name(value: Any, setting: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{setting} must be a non-empty string.")
    return value.strip()


def _column_mapping(value: Mapping[str, Any], setting: str) -> dict[str, str]:
    columns: dict[str, str] = {}
    for raw_role, raw_source in value.items():
        role = _required_name(raw_role, f"{setting} canonical column")
        if role in _RESERVED_COLUMNS:
            if role != "value":
                raise ValueError(f"{setting} uses reserved canonical column: {role}")
        columns[role] = _required_name(raw_source, f"{setting}.{role}")
    return columns


def _validate_distinct_source_columns(columns: Mapping[str, str], context: str) -> None:
    source_names = list(columns.values())
    duplicates = sorted({name for name in source_names if source_names.count(name) > 1})
    if duplicates:
        raise ValueError(f"{context} maps multiple canonical columns to the same source column: {duplicates}")


def _source_path(root: Path, relative_file: str) -> Path:
    relative = Path(relative_file)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Target source file must stay within the dataset root: {relative_file}")

    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Target source file must stay within the dataset root: {relative_file}") from exc
    if not candidate.exists():
        raise FileNotFoundError(f"Target source file not found: {candidate}")
    if not candidate.is_file():
        raise ValueError(f"Target source path must be a file: {candidate}")
    return candidate


def _load_source(
    root: Path,
    target_name: str,
    relative_file: str,
    columns: Mapping[str, str],
    coordinate_columns: tuple[str, ...],
    *,
    require_values: bool,
) -> pd.DataFrame:
    source_path = _source_path(root, relative_file)
    source = read_table(source_path)
    if source.empty:
        raise ValueError(f"Target source is empty: {target_name}")

    canonical_columns = [*coordinate_columns, *(["value"] if require_values else [])]
    source_columns = [columns[name] for name in canonical_columns]
    missing = [source_name for source_name in source_columns if source_name not in source.columns]
    if missing:
        raise ValueError(f"Target source {target_name!r} is missing columns: {missing}")

    rename = {
        source_name: VALUE_COLUMN if canonical_name == "value" else canonical_name
        for canonical_name, source_name in columns.items()
        if canonical_name in canonical_columns
    }
    observations = source[source_columns].rename(columns=rename).copy()
    observations.insert(0, TARGET_COLUMN, target_name)
    observations[SOURCE_ROW_COLUMN] = np.arange(len(observations), dtype=np.int64)

    _validate_coordinates(observations, target_name, coordinate_columns)
    if require_values:
        observations[VALUE_COLUMN] = _finite_values(observations[VALUE_COLUMN], target_name)
    _validate_unique_coordinates(observations, target_name, coordinate_columns)
    return observations


def _validate_coordinates(frame: pd.DataFrame, target_name: str, coordinate_columns: tuple[str, ...]) -> None:
    for column in coordinate_columns:
        values = frame[column]
        missing_count = int(values.isna().sum())
        non_finite_count = int(values.map(_is_invalid_number).sum())
        unhashable_count = int(values.map(_is_unhashable).sum())
        if missing_count or non_finite_count or unhashable_count:
            raise ValueError(
                f"Target source {target_name!r} has invalid coordinate {column!r} "
                f"(missing={missing_count}, non_finite={non_finite_count}, non_scalar={unhashable_count})."
            )


def _is_invalid_number(value: Any) -> bool:
    if not isinstance(value, Number):
        return False
    if isinstance(value, Complex) and not isinstance(value, Real):
        return True
    try:
        return not math.isfinite(_number_as_float(value))
    except (TypeError, ValueError, OverflowError):
        return True


def _number_as_float(value: Any) -> float:
    return float(value)


def _is_unhashable(value: Any) -> bool:
    try:
        hash(value)
    except TypeError:
        return True
    return False


def _finite_values(values: pd.Series, target_name: str) -> pd.Series:
    if (
        pd.api.types.is_datetime64_any_dtype(values.dtype)
        or pd.api.types.is_timedelta64_dtype(values.dtype)
        or pd.api.types.is_complex_dtype(values.dtype)
    ):
        raise ValueError(f"Target source {target_name!r} values must be finite real numbers.")

    numeric = pd.to_numeric(values, errors="coerce")
    if pd.api.types.is_complex_dtype(numeric.dtype):
        raise ValueError(f"Target source {target_name!r} values must be finite real numbers.")
    array = numeric.to_numpy(dtype=float)
    invalid_count = int((~np.isfinite(array)).sum())
    if invalid_count:
        raise ValueError(
            f"Target source {target_name!r} values must be finite numeric values (invalid={invalid_count})."
        )
    return pd.Series(array, index=values.index, name=VALUE_COLUMN)


def _validate_unique_coordinates(
    frame: pd.DataFrame,
    target_name: str,
    coordinate_columns: tuple[str, ...],
) -> None:
    duplicate_count = int(frame.duplicated(subset=list(coordinate_columns), keep=False).sum())
    if duplicate_count:
        raise ValueError(
            f"Target source {target_name!r} contains {duplicate_count} rows with duplicate normalized coordinates."
        )
