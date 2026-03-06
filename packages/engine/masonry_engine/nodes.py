"""Stateless decision nodes for DCDA processing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DecisionNode:
    """A pure transformation over a record payload."""

    node_id: str

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        return dict(payload)


class ScoreBandNode(DecisionNode):
    """Adds a coarse score band to reduce identification risk."""

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        out = dict(payload)
        score = out.get("score")
        if isinstance(score, (int, float)):
            if score < 400:
                out["score_band"] = "low"
            elif score < 700:
                out["score_band"] = "medium"
            else:
                out["score_band"] = "high"
        return out
