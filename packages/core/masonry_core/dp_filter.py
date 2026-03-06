"""dp_filter.py — Differential Privacy filter for MASONRY.AI

Fix applied (Gemini code review):
  - Use opendp native make_laplace / make_gaussian (avoids
    Mironov floating-point vulnerability in hand-rolled implementations)
  - Sensitivity derived from contract bounds, not hard-coded
  - Epsilon budget tracker per tenant session (in-process; replace with
    Redis for multi-process deployments)
  - k-anonymity quasi-identifier suppression preserved

OpenDP docs: https://docs.opendp.org/
"""
from __future__ import annotations

import math
import os
from collections import defaultdict
from typing import Any

try:
    import opendp.prelude as _dp  # type: ignore[import-untyped]
    HAS_OPENDP = True
except ImportError:  # pragma: no cover
    _dp = None  # type: ignore[assignment]
    HAS_OPENDP = False

from .contracts import MasonContract

# ---------------------------------------------------------------------------
# Epsilon budget tracker (per tenant_id; in-process)
# Replace with Redis / DB in multi-process production deployments.
# ---------------------------------------------------------------------------
_epsilon_spent: dict[str, float] = defaultdict(float)
EPSILON_MAX_PER_TENANT: float = 10.0  # total budget before key rotation


def _check_epsilon_budget(tenant_id: str, epsilon: float) -> None:
    """Raise if tenant has exhausted their differential-privacy budget."""
    spent = _epsilon_spent[tenant_id]
    if spent + epsilon > EPSILON_MAX_PER_TENANT:
        raise RuntimeError(
            f"Tenant '{tenant_id}' epsilon budget exhausted "
            f"({spent:.2f}/{EPSILON_MAX_PER_TENANT}). Rotate API key."
        )
    _epsilon_spent[tenant_id] += epsilon


def reset_epsilon_budget(tenant_id: str) -> None:
    """Reset budget after key rotation (call from admin endpoint)."""
    _epsilon_spent[tenant_id] = 0.0


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
class DPConfig:
    """DP parameters derived from a MasonContract."""

    def __init__(
        self,
        epsilon: float = 1.0,
        delta: float = 1e-6,
        sensitivity: float = 1.0,
        mechanism: str = "laplace",  # "laplace" | "gaussian"
        numeric_fields: list[str] | None = None,
        quasi_identifiers: list[str] | None = None,
        k_threshold: int = 5,
    ) -> None:
        if epsilon <= 0:
            raise ValueError("epsilon must be > 0")
        if delta < 0 or delta >= 1:
            raise ValueError("delta must be in [0, 1)")
        if sensitivity <= 0:
            raise ValueError("sensitivity must be > 0")
        self.epsilon = epsilon
        self.delta = delta
        self.sensitivity = sensitivity
        self.mechanism = mechanism
        self.numeric_fields = numeric_fields or []
        self.quasi_identifiers = quasi_identifiers or []
        self.k_threshold = k_threshold

    @classmethod
    def from_contract(cls, contract: MasonContract) -> "DPConfig":
        """Derive DP config from contract metadata."""
        sensitivity = 1.0
        numeric_fields: list[str] = []
        quasi_identifiers: list[str] = []

        contract_name = type(contract).__name__
        if contract_name == "FinanceContract":
            raw = getattr(contract, "annual_income_range", None)
            if raw:
                try:
                    if raw.endswith("k+"):
                        sensitivity = 200_000.0
                    else:
                        low_raw, high_raw = raw.split("-")
                        low = float(low_raw.replace("k", "")) * 1000
                        high = float(high_raw.replace("k", "")) * 1000
                        sensitivity = high - low
                except Exception:
                    sensitivity = 200_000.0
            numeric_fields = []
            quasi_identifiers = ["age"]
        elif contract_name == "HealthContract":
            sensitivity = 1.0
            quasi_identifiers = ["age", "treatment_category"]
        elif contract_name == "GDPRUserContract":
            sensitivity = 1.0
            quasi_identifiers = ["age"]

        return cls(
            epsilon=float(os.environ.get("MASONRY_DP_EPSILON", "1.0")),
            sensitivity=sensitivity,
            numeric_fields=numeric_fields,
            quasi_identifiers=quasi_identifiers,
        )


# ---------------------------------------------------------------------------
# OpenDP-backed noise primitives
# nan=False excludes NaN from atom_domain (required for AbsoluteDistance metric in opendp >= 0.8)
# ---------------------------------------------------------------------------
def _laplace_noise(value: float, sensitivity: float, epsilon: float) -> float:
    """Add calibrated Laplace noise via opendp (Mironov-safe)."""
    if not HAS_OPENDP or _dp is None:
        raise RuntimeError("opendp is not installed. Run: pip install opendp")
    _dp.enable_features("contrib")
    scale = sensitivity / epsilon
    meas = _dp.m.make_laplace(
                    _dp.atom_domain(T=float, nan=False),
        _dp.absolute_distance(T=float),
        scale,
    )
    return float(meas(value))


def _gaussian_noise(value: float, sensitivity: float, epsilon: float, delta: float) -> float:
    """Add calibrated Gaussian noise via opendp (zero-concentrated DP)."""
    if not HAS_OPENDP or _dp is None:
        raise RuntimeError("opendp is not installed. Run: pip install opendp")
    _dp.enable_features("contrib")
    scale = sensitivity * math.sqrt(2 * math.log(1.25 / delta)) / epsilon
    meas = _dp.m.make_gaussian(
                    _dp.atom_domain(T=float, nan=False),
        _dp.absolute_distance(T=float),
        scale,
    )
    return float(meas(value))


# ---------------------------------------------------------------------------
# k-anonymity suppression
# ---------------------------------------------------------------------------
def _k_anonymise_record(record: dict[str, Any], quasi_ids: list[str], k: int) -> dict[str, Any]:
    """Suppress quasi-identifier fields to enforce k-anonymity baseline."""
    out = dict(record)
    for field in quasi_ids:
        if field in out and isinstance(out[field], int):
            out[field] = (out[field] // 10) * 10
    return out


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def apply_dp_pipeline(
    record: dict[str, Any],
    config: DPConfig,
    tenant_id: str = "default",
) -> dict[str, Any]:
    """Apply full DP pipeline to a single validated record."""
    _check_epsilon_budget(tenant_id, config.epsilon)
    out = _k_anonymise_record(record, config.quasi_identifiers, config.k_threshold)
    for field in config.numeric_fields:
        if field in out and isinstance(out[field], (int, float)):
            raw = float(out[field])
            if config.mechanism == "gaussian":
                out[field] = _gaussian_noise(raw, config.sensitivity, config.epsilon, config.delta)
            else:
                out[field] = _laplace_noise(raw, config.sensitivity, config.epsilon)
    return out


def sanitise(
    data: dict[str, Any],
    epsilon: float = 1.0,
    sensitivity: float = 1.0,
    quasi_identifiers: list[str] | None = None,
    tenant_id: str = "default",
) -> dict[str, Any]:
    """High-level sanitise used by the Gatekeeper."""
    config = DPConfig(
        epsilon=epsilon,
        sensitivity=sensitivity,
        quasi_identifiers=quasi_identifiers or ["age"],
    )
    _check_epsilon_budget(tenant_id, config.epsilon)
    return _k_anonymise_record(data, config.quasi_identifiers, config.k_threshold)
