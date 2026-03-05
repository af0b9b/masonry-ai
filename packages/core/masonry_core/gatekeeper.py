"""Local Mason gate utility for validating + sanitising payloads.

This helper is intentionally lightweight and dependency-free so library users
can run the same fail-fast boundary checks used by the Gatekeeper service.
"""

from __future__ import annotations

from typing import Any

from .contracts import MasonContract
from .dp_filter import sanitise


def mason_gate(contract: type[MasonContract], payload: dict[str, Any]) -> MasonContract:
    """Validate a payload against a Mason contract and return the safe model.

    The returned object already contains masked/pseudonymised fields as defined
    by the contract validators.
    """
    return contract(**payload)


def mason_gate_and_sanitise(
    contract: type[MasonContract], payload: dict[str, Any]
) -> dict[str, Any]:
    """Validate payload and apply differential-privacy sanitisation."""
    validated = mason_gate(contract, payload)
    return sanitise(validated.model_dump())
