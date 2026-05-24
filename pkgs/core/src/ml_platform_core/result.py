from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RunResult:
    """Standard result object returned from package code.

    Package code returns this object. Runtime adapters decide whether to print it locally,
    upload it to ClearML, or inspect it in tests.
    """

    run_dir: Path
    metrics: dict[str, float] = field(default_factory=dict)
    artifacts: dict[str, Path] = field(default_factory=dict)
    tables: dict[str, Path] = field(default_factory=dict)
    plots: dict[str, Path] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_dir": str(self.run_dir),
            "metrics": self.metrics,
            "artifacts": {key: str(value) for key, value in self.artifacts.items()},
            "tables": {key: str(value) for key, value in self.tables.items()},
            "plots": {key: str(value) for key, value in self.plots.items()},
            "extra": self.extra,
        }
