"""DCDA decision graph orchestrator."""

from __future__ import annotations

from typing import Any, Iterable

from .nodes import DecisionNode
from .stability import stable_enough, turbulence_score


class DecisionGraph:
    """Executes stateless decision nodes in sequence."""

    def __init__(self, nodes: Iterable[DecisionNode]) -> None:
        self.nodes = list(nodes)

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        out = dict(payload)
        for node in self.nodes:
            out = node.execute(out)
        return out

    def evaluate_turbulence(self, failures: int, input_variance: float) -> float:
        return turbulence_score(len(self.nodes), failures, input_variance)

    def is_stable(self, recent_scores: Iterable[float], threshold: float = 0.7) -> bool:
        return stable_enough(recent_scores, threshold=threshold)
