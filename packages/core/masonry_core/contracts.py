"""
masonry_core.contracts
======================
Core Data Contracts for MASONRY.AI - Privacy by Mason implementation.

Each contract is a Pydantic model that acts as the Mason gate:
- Non-conforming data is REJECTED at ingestion (fail-fast)
- PII is masked/pseudonymized at the boundary
- Privacy predicates are structural, not policy-based

License: AGPL-3.0 (open source)
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Privacy Predicates
# ---------------------------------------------------------------------------

class PrivacyPredicate:
    """Reusable privacy predicates. Replaces formal type theory."""

    @staticmethod
    def mask_email(value: str) -> str:
        """Mask email local part, keeping domain. Masks at ingestion."""
        parts = value.split("@")
        if len(parts) != 2:
            raise ValueError("Invalid email format")
        local = parts[0]
        masked = (local[0] + "***") if len(local) > 1 else "***"
        return f"{masked}@{parts[1]}"

    @staticmethod
    def pseudonymize(value: str) -> str:
        """Deterministic pseudonymization via SHA-256."""
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def mask_partial(value: str, keep: int = 2) -> str:
        """Keep first N chars, mask the rest."""
        if len(value) <= keep:
            return "*" * len(value)
        return value[:keep] + "*" * (len(value) - keep)


# ---------------------------------------------------------------------------
# Base Contract
# ---------------------------------------------------------------------------

class MasonContract(BaseModel):
    """
    Base Mason Contract.

    All customer schemas inherit from this. Config forbids extra fields
    (Structural Privacy: the container defines what is admissible).
    """

    class Config:
        extra = "forbid"  # No unknown fields allowed. Ever.
        populate_by_name = True

    def to_safe_dict(self) -> dict[str, Any]:
        """Export safe (already masked) data as dict."""
        return self.model_dump()


# ---------------------------------------------------------------------------
# Tier 1: GDPR Basic Contract (Shield tier - SMB)
# ---------------------------------------------------------------------------

class GDPRUserContract(MasonContract):
    """
    GDPR Basic Contract - ready-to-use for SMB/startups.
    Activation: 5 minutes. Zero math required.

    Mason gates enforced:
    - Age > 18 (structural constraint)
    - GDPR must be explicitly accepted
    - Email masked at ingestion boundary
    - user_id pseudonymized at ingestion boundary
    - Consent level >= 2 required
    """

    user_id: str = Field(description="Will be pseudonymized at ingestion")
    age: int = Field(gt=0, lt=150, description="Must be > 18 for most data processing")
    email: str = Field(description="Will be masked at ingestion")
    consent_level: int = Field(
        ge=1, le=4,
        description="1=basic, 2=marketing, 3=AI-processing, 4=full"
    )
    gdpr_accepted: bool = Field(description="Must be True. No exceptions.")
    ingested_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("user_id")
    @classmethod
    def pseudonymize_user_id(cls, v: str) -> str:
        return PrivacyPredicate.pseudonymize(v)

    @field_validator("email")
    @classmethod
    def mask_email_at_ingestion(cls, v: str) -> str:
        return PrivacyPredicate.mask_email(v)

    @field_validator("age")
    @classmethod
    def enforce_adult(cls, v: int) -> int:
        if v < 18:
            raise ValueError(
                f"MASON STOP: age {v} < 18. "
                "Processing minors' data requires special legal basis. "
                "Data rejected."
            )
        return v

    @field_validator("gdpr_accepted")
    @classmethod
    def require_gdpr_acceptance(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "MASON STOP: gdpr_accepted=False. "
                "No legal basis for processing. Data rejected."
            )
        return v

    @field_validator("consent_level")
    @classmethod
    def require_minimum_consent(cls, v: int) -> int:
        if v < 2:
            raise ValueError(
                f"MASON STOP: consent_level {v} < 2. "
                "Insufficient consent for data processing. Data rejected."
            )
        return v


# ---------------------------------------------------------------------------
# Tier 2: Finance Contract (Trust tier - Mid-Market FinTech)
# ---------------------------------------------------------------------------

class FinanceContract(GDPRUserContract):
    """
    Finance/FinTech Contract - Mid-Market.

    Extends GDPR base with financial data constraints:
    - No exact amounts (only ranges)
    - No raw account numbers (only hashes)
    - Consent level >= 3 required for financial data
    """

    annual_income_range: str = Field(
        pattern=r"^(0-20k|20-50k|50-100k|100-200k|200k\+)$",
        description="Range only. Exact income is never stored."
    )
    credit_score_band: str = Field(
        pattern=r"^(poor|fair|good|very_good|exceptional)$",
        description="Band only. Exact score is never stored."
    )
    account_hash: str = Field(
        description="SHA-256 of account number. Never the raw number."
    )
    transaction_count_range: Optional[str] = Field(
        default=None,
        pattern=r"^(0-10|10-50|50-200|200\+)$"
    )

    @field_validator("consent_level")
    @classmethod
    def finance_requires_level3(cls, v: int) -> int:
        if v < 3:
            raise ValueError(
                f"MASON STOP: Financial data requires consent_level >= 3. "
                f"Got {v}. Data rejected."
            )
        return v

    @field_validator("account_hash")
    @classmethod
    def validate_account_hash(cls, v: str) -> str:
        if len(v) < 16:
            raise ValueError(
                "MASON STOP: account_hash too short. "
                "Must be SHA-256 derived (min 16 chars). Data rejected."
            )
        return v


# ---------------------------------------------------------------------------
# Tier 2: Health Contract (Trust tier - Mid-Market Healthcare)
# ---------------------------------------------------------------------------

class HealthContract(GDPRUserContract):
    """
    Healthcare Contract - Mid-Market (clinics, telemedicine, pharma).

    Special category data (Art. 9 GDPR):
    - Explicit consent level 4 required
    - Diagnosis codes (ICD-10) allowed, free text diagnoses forbidden
    - No direct patient identifiers beyond pseudonymized user_id
    """

    icd10_codes: list[str] = Field(
        description="ICD-10 codes only. No free-text diagnoses."
    )
    treatment_category: str = Field(
        pattern=r"^(preventive|diagnostic|therapeutic|rehabilitative|palliative)$"
    )
    data_controller_id: str = Field(
        description="Healthcare provider identifier (pseudonymized)"
    )

    @field_validator("consent_level")
    @classmethod
    def health_requires_level4(cls, v: int) -> int:
        if v < 4:
            raise ValueError(
                f"MASON STOP: Special category health data requires "
                f"explicit consent (level 4). Got {v}. Data rejected."
            )
        return v

    @field_validator("icd10_codes")
    @classmethod
    def validate_icd10(cls, v: list[str]) -> list[str]:
        import re
        pattern = re.compile(r"^[A-Z][0-9]{2}(\.[0-9A-Z]{1,4})?$")
        for code in v:
            if not pattern.match(code):
                raise ValueError(
                    f"MASON STOP: '{code}' is not a valid ICD-10 code. "
                    "Free-text diagnoses are not permitted. Data rejected."
                )
        return v


# ---------------------------------------------------------------------------
# Contract Registry
# ---------------------------------------------------------------------------

CONTRACT_REGISTRY: dict[str, type[MasonContract]] = {
    "gdpr_basic": GDPRUserContract,
    "finance_trust": FinanceContract,
    "health_trust": HealthContract,
}


def get_contract(name: str) -> type[MasonContract]:
    """Retrieve a contract class by name."""
    if name not in CONTRACT_REGISTRY:
        available = list(CONTRACT_REGISTRY.keys())
        raise KeyError(
            f"Contract '{name}' not found. Available: {available}"
        )
    return CONTRACT_REGISTRY[name]
