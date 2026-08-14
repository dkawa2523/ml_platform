from __future__ import annotations

from typing import TypeVar

from ..selection import selection_sort_value
from .artifacts import CandidateResult

CandidateT = TypeVar("CandidateT", bound=CandidateResult)


def ranked_results(results: list[CandidateT], selection_metric: str) -> list[CandidateT]:
    return sorted(results, key=lambda item: selection_sort_value(item.metrics, selection_metric))
