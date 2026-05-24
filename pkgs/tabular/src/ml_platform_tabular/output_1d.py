from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ml_platform_core.artifacts import (
    prepare_run_dir,
    update_latest,
    write_config_snapshot,
    write_manifest,
)
from ml_platform_core.io import write_json, write_table
from ml_platform_core.result import RunResult

from .data import load_dataset


def _column_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        return [str(part) for part in value]
    raise ValueError(f"Column list must be null, string, or list: {value!r}")


def _require_column(df: pd.DataFrame, value: Any, key: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} is required for tabular_1d_output.")
    if value not in df.columns:
        raise ValueError(f"{key} not found in input table: {value}")
    return value


def _numeric_summary(series: pd.Series, prefix: str) -> dict[str, float]:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return {}
    return {
        f"{prefix}_min": float(numeric.min()),
        f"{prefix}_max": float(numeric.max()),
        f"{prefix}_mean": float(numeric.mean()),
    }


def run_output_1d(cfg: dict[str, Any]) -> RunResult:
    output_dir = Path(cfg.get("runtime", {}).get("output_dir", "outputs"))
    run_name = cfg.get("run", {}).get("name", "tabular_1d_output")
    run_dir = prepare_run_dir(output_dir, run_name)

    df = load_dataset(cfg)
    data_cfg = cfg.get("data", {})
    x_column = _require_column(df, data_cfg.get("x_column"), "data.x_column")
    value_column = _require_column(df, data_cfg.get("value_column"), "data.value_column")
    id_columns = _column_list(data_cfg.get("id_columns"))
    missing_id_columns = [column for column in id_columns if column not in df.columns]
    if missing_id_columns:
        raise ValueError(f"data.id_columns not found in input table: {missing_id_columns}")

    selected_columns = [*id_columns, x_column, value_column]
    output_df = df[selected_columns].copy().rename(columns={x_column: "x", value_column: "value"})
    output_df = output_df.sort_values("x", kind="mergesort").reset_index(drop=True)

    table_name = cfg.get("output", {}).get("table_name", "tabular_1d_output.csv")
    table_path = write_table(output_df, run_dir / table_name)
    summary = {
        "row_count": len(output_df),
        "x_column": x_column,
        "value_column": value_column,
        "id_columns": id_columns,
        **_numeric_summary(df[x_column], "x"),
        **_numeric_summary(df[value_column], "value"),
    }
    summary_path = write_json(summary, run_dir / "summary.json")
    config_path = write_config_snapshot(cfg, run_dir)

    metrics = {"row_count": float(len(output_df))}
    artifacts = {"summary": summary_path, "config": config_path}
    tables = {"output_1d": table_path}
    manifest_path = write_manifest(run_dir, config=cfg, metrics=metrics, artifacts=artifacts, tables=tables)
    artifacts["manifest"] = manifest_path

    update_latest(run_dir, output_dir / "latest_1d_output")
    update_latest(run_dir, output_dir / "latest")

    return RunResult(
        run_dir=run_dir,
        metrics=metrics,
        artifacts=artifacts,
        tables=tables,
        extra=summary,
    )
