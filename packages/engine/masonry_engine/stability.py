"""Turbulence / stability helpers for DCDA graph execution."""

from __future__ import annotations

from typing import Iterable


def turbulence_score(edge_count: int, failure_count: int, input_variance: float) -> float:
    """Compute a bounded turbulence score in [0, 1]."""
    if edge_count <= 0:
        return 0.0
    raw = (failure_count / edge_count) + min(input_variance, 1.0)
    return min(max(raw / 2.0, 0.0), 1.0)


def stable_enough(scores: Iterable[float], threshold: float = 0.7) -> bool:
    values = list(scores)
    if not values:
        return True
    return sum(values) / len(values) <= threshold
