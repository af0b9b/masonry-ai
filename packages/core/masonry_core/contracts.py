"""Core Data Contracts for MASONRY.AI - Privacy by Mason implementation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .predicates import PrivacyPredicate


class MasonContract(BaseModel):
    """Base contract: strict schema at the ingestion boundary."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    def to_safe_dict(self) -> dict[str, Any]:
        return self.model_dump()


class GDPRUserContract(MasonContract):
    """GDPR baseline contract for general user data."""

    user_id: str = Field(description="Will be pseudonymized at ingestion")
    age: int = Field(gt=0, lt=150, description="Must be > 18 for most processing")
    email: str = Field(description="Will be masked at ingestion")
    consent_level: int = Field(
        ge=1,
        le=4,
        description="1=basic, 2=marketing, 3=AI-processing, 4=full",
    )
    gdpr_accepted: bool = Field(description="Must be True")
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

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


class FinanceContract(GDPRUserContract):
    """Finance contract with stricter constraints."""

    annual_income_range: str = Field(
        pattern=r"^(0-20k|20-50k|50-100k|100-200k|200k\+)$",
        description="Range only. Exact income is never stored.",
    )
    credit_score_band: str = Field(
        pattern=r"^(poor|fair|good|very_good|exceptional)$",
        description="Band only. Exact score is never stored.",
    )
    account_hash: str = Field(description="SHA-256 of account number.")
    transaction_count_range: Optional[str] = Field(
        default=None,
        pattern=r"^(0-10|10-50|50-200|200\+)$",
    )

    @field_validator("consent_level")
    @classmethod
    def finance_requires_level3(cls, v: int) -> int:
        if v < 3:
            raise ValueError(
                "MASON STOP: Financial data requires consent_level >= 3. "
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


class HealthContract(GDPRUserContract):
    """Health contract for Art.9-like sensitive data."""

    icd10_codes: list[str] = Field(description="ICD-10 codes only.")
    treatment_category: str = Field(
        pattern=r"^(preventive|diagnostic|therapeutic|rehabilitative|palliative)$"
    )
    data_controller_id: str = Field(description="Healthcare provider identifier")

    @field_validator("consent_level")
    @classmethod
    def health_requires_level4(cls, v: int) -> int:
        if v < 4:
            raise ValueError(
                "MASON STOP: Special category health data requires "
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


CONTRACT_REGISTRY: dict[str, type[MasonContract]] = {
    "gdpr_basic": GDPRUserContract,
    "finance_trust": FinanceContract,
    "health_trust": HealthContract,
    "gdpr": GDPRUserContract,
    "finance": FinanceContract,
    "health": HealthContract,
}


def get_contract(name: str) -> type[MasonContract]:
    if name not in CONTRACT_REGISTRY:
        available = list(CONTRACT_REGISTRY.keys())
        raise KeyError(f"Contract '{name}' not found. Available: {available}")
    return CONTRACT_REGISTRY[name]
