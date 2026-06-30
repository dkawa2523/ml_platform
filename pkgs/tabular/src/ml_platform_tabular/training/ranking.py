from __future__ import annotations

from typing import TypeVar

from ..ensemble import metric_value
from .artifacts import CandidateResult

CandidateT = TypeVar("CandidateT", bound=CandidateResult)


def _selection_sort_value(metrics: dict[str, float], selection_metric: str) -> float:
    value = metric_value(metrics, selection_metric)
    return -value if selection_metric == "r2" else value


def ranked_results(results: list[CandidateT], selection_metric: str) -> list[CandidateT]:
    return sorted(results, key=lambda item: _selection_sort_value(item.metrics, selection_metric))
