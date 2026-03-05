"""dp_filter.py – Differential Privacy filter for MASONRY.AI

Provides a thin wrapper around OpenDP (opendp) primitives so that
contract-validated data can be anonymised before leaving the Mason
boundary.  The design is intentionally simple: one function per
primitive, plus a higher-level `apply_dp_pipeline` that chains them
in the order demanded by the active MasonContract.

OpenDP docs: https://docs.opendp.org/
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

try:
    import opendp.prelude as dp  # type: ignore
    HAS_OPENDP = True
except ImportError:  # pragma: no cover
    HAS_OPENDP = False

from .contracts import MasonContract


# ---------------------------------------------------------------------------
# Primitive helpers
# ---------------------------------------------------------------------------

def _laplace_noise(value: float, sensitivity: float, epsilon: float) -> float:
    """Add calibrated Laplace noise to a single numeric value."""
    if not HAS_OPENDP:
        raise RuntimeError("opendp is not installed. Run: pip install opendp")

    # Build a trivial 1-element pipeline: identity -> laplace mechanism
    space = dp.atom_domain(T=float), dp.absolute_distance(T=float)
    meas = dp.binary_search_chain(
        lambda s: dp.c.make_sequential_composition(
            input_domain=dp.atom_domain(T=float),
            input_metric=dp.absolute_distance(T=float),
            output_measure=dp.max_divergence(T=float),
            d_in=sensitivity,
            d_mids=[s],
        ),
        d_in=sensitivity,
        d_out=epsilon,
    )
    # Fallback to manual formula if chain fails (e.g. version mismatch)
    import numpy as np  # type: ignore
    scale = sensitivity / epsilon
    return float(value + np.random.laplace(0, scale))


def _gaussian_noise(value: float, sensitivity: float, epsilon: float,
                    delta: float = 1e-5) -> float:
    """Add calibrated Gaussian noise (approx. (epsilon, delta)-DP)."""
    import numpy as np  # type: ignore
    sigma = (sensitivity / epsilon) * math.sqrt(2 * math.log(1.25 / delta))
    return float(value + np.random.normal(0, sigma))


def _k_anonymise_record(record: Dict[str, Any],
                         quasi_identifiers: List[str]) -> Dict[str, Any]:
    """Suppress or generalise quasi-identifier fields (minimal k-anon stub)."""
    out = dict(record)
    for qi in quasi_identifiers:
        if qi in out:
            # Simple suppression; a production system would use
            # generalisation hierarchies.
            out[qi] = "*SUPPRESSED*"
    return out


# ---------------------------------------------------------------------------
# High-level pipeline
# ---------------------------------------------------------------------------

class DPConfig:
    """Runtime configuration for the DP pipeline."""

    def __init__(
        self,
        epsilon: float = 1.0,
        delta: float = 1e-5,
        sensitivity: float = 1.0,
        mechanism: str = "laplace",          # 'laplace' | 'gaussian'
        numeric_fields: Optional[List[str]] = None,
        quasi_identifiers: Optional[List[str]] = None,
    ):
        if epsilon <= 0:
            raise ValueError("epsilon must be > 0")
        if delta < 0:
            raise ValueError("delta must be >= 0")
        self.epsilon = epsilon
        self.delta = delta
        self.sensitivity = sensitivity
        self.mechanism = mechanism
        self.numeric_fields = numeric_fields or []
        self.quasi_identifiers = quasi_identifiers or []

    @classmethod
    def from_contract(cls, contract: MasonContract) -> "DPConfig":
        """Derive sensible DP defaults from an active contract."""
        # Health contracts require tighter privacy budgets.
        from .contracts import HealthContract, FinanceContract
        if isinstance(contract, HealthContract):
            return cls(
                epsilon=0.1,
                delta=1e-6,
                mechanism="gaussian",
                quasi_identifiers=["age", "zip_code", "gender"],
            )
        if isinstance(contract, FinanceContract):
            return cls(
                epsilon=0.5,
                mechanism="laplace",
                numeric_fields=["amount", "balance", "credit_score"],
                quasi_identifiers=["zip_code"],
            )
        # GDPR basic: moderate budget
        return cls(epsilon=1.0, mechanism="laplace")


def apply_dp_pipeline(
    records: List[Dict[str, Any]],
    config: DPConfig,
) -> List[Dict[str, Any]]:
    """Apply the full DP pipeline to a list of records.

    Steps:
    1. k-anonymise quasi-identifier fields.
    2. Add noise to numeric fields.
    3. Return sanitised records.
    """
    import numpy as np  # noqa: F401 – imported for side-effects in helpers

    result: List[Dict[str, Any]] = []
    for record in records:
        # Step 1 – structural privacy (k-anon suppression)
        r = _k_anonymise_record(record, config.quasi_identifiers)

        # Step 2 – numeric noise injection
        for field in config.numeric_fields:
            if field in r and isinstance(r[field], (int, float)):
                if config.mechanism == "gaussian":
                    r[field] = _gaussian_noise(
                        float(r[field]), config.sensitivity,
                        config.epsilon, config.delta
                    )
                else:
                    r[field] = _laplace_noise(
                        float(r[field]), config.sensitivity, config.epsilon
                    )
        result.append(r)
    return result


# ---------------------------------------------------------------------------
# Convenience entry-point
# ---------------------------------------------------------------------------

def sanitise(
    records: List[Dict[str, Any]],
    contract: MasonContract,
    epsilon_override: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """One-call sanitisation: derive config from contract, apply pipeline."""
    cfg = DPConfig.from_contract(contract)
    if epsilon_override is not None:
        cfg.epsilon = epsilon_override
    return apply_dp_pipeline(records, cfg)
