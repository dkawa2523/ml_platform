from __future__ import annotations

from numbers import Real

from ml_platform_core.result import RunResult


def report_result(adapter, result: RunResult) -> None:
    """Report RunResult to ClearML.

    Keep this generic and avoid tabular-specific assumptions.
    """
    for name, value in result.metrics.items():
        if isinstance(value, Real):
            adapter.report_scalar("metrics", name, float(value), iteration=0)

    for name, path in result.artifacts.items():
        adapter.upload_artifact(name, path)

    for name, path in result.tables.items():
        adapter.upload_artifact(name, path)

    for name, path in result.plots.items():
        adapter.upload_artifact(name, path)
