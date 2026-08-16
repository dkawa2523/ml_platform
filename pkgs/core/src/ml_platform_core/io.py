from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

import pandas as pd

TABLE_SUFFIXES = {".csv", ".parquet", ".pq"}


def is_supported_table_file(path: str | Path) -> bool:
    path = Path(path)
    return path.is_file() and path.suffix.lower() in TABLE_SUFFIXES


def _require_supported_table_file(path: Path, *, context: str = "Table file") -> Path:
    if is_supported_table_file(path):
        return path
    supported = ", ".join(sorted(TABLE_SUFFIXES))
    raise ValueError(f"{context} has unsupported table format: {path.suffix}. Supported: {supported}")


def find_table_file(path: str | Path, *, preferred_name: str | None = None) -> Path:
    """Resolve a table file from a file or directory path.

    ClearML Dataset local copies are often directories. To keep pkgs ClearML-free,
    the caller can pass the resolved local copy and this helper chooses a table file.
    """
    path = Path(path)
    if path.is_file():
        return _require_supported_table_file(path)
    _require_existing_directory(path)

    if preferred_name:
        return _preferred_table_file(path, preferred_name)

    return _single_table_file(path)


def _require_existing_directory(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Table path not found: {path}")
    if not path.is_dir():
        raise ValueError(f"Table path is neither file nor directory: {path}")


def _preferred_table_file(path: Path, preferred_name: str) -> Path:
    candidate = path / preferred_name
    if candidate.exists() and candidate.is_file():
        return _require_supported_table_file(candidate, context="Preferred table file")
    raise FileNotFoundError(f"Preferred table file not found in dataset copy: {candidate}")


def _single_table_file(path: Path) -> Path:
    candidates = sorted(p for p in path.rglob("*") if is_supported_table_file(p))
    if not candidates:
        raise FileNotFoundError(f"No supported table file found under directory: {path}")
    if len(candidates) > 1:
        formatted = ", ".join(str(p.relative_to(path)) for p in candidates[:10])
        raise ValueError(f"Multiple table files found. Set data.dataset_file to choose one. Candidates: {formatted}")
    return candidates[0]


def read_table(path: str | Path, *, preferred_name: str | None = None) -> pd.DataFrame:
    path = find_table_file(path, preferred_name=preferred_name)

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)

    raise ValueError(f"Unsupported table format: {path.suffix}")


def write_table(df: pd.DataFrame, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    suffix = path.suffix.lower()
    if suffix == ".csv":
        df.to_csv(path, index=False)
        return path
    if suffix in {".parquet", ".pq"}:
        df.to_parquet(path, index=False)
        return path

    raise ValueError(f"Unsupported table format: {path.suffix}")


def read_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(data: dict[str, Any], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def dump_joblib(obj: Any, path: str | Path) -> Path:
    """Serialize a trusted internal model artifact using the stable public API name."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(obj, f)
    return path


def load_joblib(path: str | Path) -> Any:
    """Load a trusted model artifact produced by this platform.

    Pickle-compatible artifacts must never be accepted from an untrusted source.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Model artifact file not found: {path}")
    with path.open("rb") as f:
        return pickle.load(f)
