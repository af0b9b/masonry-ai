"""test_contracts.py — Comprehensive pytest suite for MasonContracts.

Covers:
  - Fail-Fast rejection (underage, missing consent, invalid email)
  - PII masking at ingestion (email pseudonymisation)
  - Contract Registry lookup
  - Finance and Health contract specifics
  - extra=forbid (unknown fields rejected)
"""
import pytest
from pydantic import ValidationError

from masonry_core.contracts import (
    CONTRACT_REGISTRY,
    FinanceContract,
    GDPRUserContract,
    HealthContract,
    get_contract,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
VALID_GDPR = dict(
    user_id=1,
    age=25,
    email="top_secret@example.com",
    consent_level=2,
    gdpr_accepted=True,
)

VALID_FINANCE = dict(
    user_id=2,
    age=30,
    email="finance@example.com",
    consent_level=3,
    gdpr_accepted=True,
    income_range="[20000-80000]",
    credit_score_band="A",
    account_hash="abc123hash",
)

VALID_HEALTH = dict(
    user_id=3,
    age=40,
    email="health@example.com",
    consent_level=4,
    gdpr_accepted=True,
    icd10_codes=["A01.0", "Z00.0"],
    treatment_category="outpatient",
)


# ---------------------------------------------------------------------------
# GDPR Contract — Structural Fail-Fast
# ---------------------------------------------------------------------------
class TestGDPRContractRejection:
    def test_underage_user_rejected(self):
        """Mason MUST reject users under 18 (Structural Privacy invariant)."""
        payload = {**VALID_GDPR, "age": 17}
        with pytest.raises(ValidationError):
            GDPRUserContract(**payload)

    def test_missing_gdpr_acceptance_rejected(self):
        payload = {**VALID_GDPR, "gdpr_accepted": False}
        with pytest.raises(ValidationError):
            GDPRUserContract(**payload)

    def test_insufficient_consent_rejected(self):
        payload = {**VALID_GDPR, "consent_level": 1}
        with pytest.raises(ValidationError):
            GDPRUserContract(**payload)

    def test_invalid_email_format_rejected(self):
        payload = {**VALID_GDPR, "email": "not-an-email"}
        with pytest.raises(ValidationError):
            GDPRUserContract(**payload)

    def test_unknown_field_rejected(self):
        """extra=forbid must block unknown fields."""
        payload = {**VALID_GDPR, "sneaky_field": "injected"}
        with pytest.raises(ValidationError):
            GDPRUserContract(**payload)


class TestGDPRContractAcceptance:
    def test_valid_user_accepted(self):
        c = GDPRUserContract(**VALID_GDPR)
        assert c.user_id == 1
        assert c.age == 25

    def test_email_masking_at_ingestion(self):
        """The Mason must pseudonymise email on ingestion (Privacy by Design)."""
        c = GDPRUserContract(**VALID_GDPR)
        # Email must be masked — original must NOT appear verbatim
        assert "top_secret" not in c.email
        # But domain part should still be identifiable for routing
        assert "@" in c.email

    def test_user_id_pseudonymised(self):
        """user_id should be hashed/pseudonymised, not stored in clear."""
        c = GDPRUserContract(**VALID_GDPR)
        # After pseudonymisation, the raw integer should not appear in model_dump
        dump = c.model_dump()
        assert dump["user_id"] != 1  # must be transformed


# ---------------------------------------------------------------------------
# Finance Contract
# ---------------------------------------------------------------------------
class TestFinanceContract:
    def test_valid_finance_contract_accepted(self):
        c = FinanceContract(**VALID_FINANCE)
        assert c.credit_score_band == "A"

    def test_finance_requires_consent_level_3(self):
        payload = {**VALID_FINANCE, "consent_level": 2}
        with pytest.raises(ValidationError):
            FinanceContract(**payload)

    def test_invalid_income_range_rejected(self):
        payload = {**VALID_FINANCE, "income_range": "not-a-range"}
        with pytest.raises(ValidationError):
            FinanceContract(**payload)


# ---------------------------------------------------------------------------
# Health Contract
# ---------------------------------------------------------------------------
class TestHealthContract:
    def test_valid_health_contract_accepted(self):
        c = HealthContract(**VALID_HEALTH)
        assert "A01.0" in c.icd10_codes

    def test_health_requires_consent_level_4(self):
        payload = {**VALID_HEALTH, "consent_level": 3}
        with pytest.raises(ValidationError):
            HealthContract(**payload)

    def test_invalid_icd10_code_rejected(self):
        """ICD-10 regex must reject malformed codes."""
        payload = {**VALID_HEALTH, "icd10_codes": ["NOTACODE"]}
        with pytest.raises(ValidationError):
            HealthContract(**payload)


# ---------------------------------------------------------------------------
# Contract Registry
# ---------------------------------------------------------------------------
class TestContractRegistry:
    def test_gdpr_contract_resolvable(self):
        cls = get_contract("gdpr")
        assert cls is GDPRUserContract

    def test_finance_contract_resolvable(self):
        cls = get_contract("finance")
        assert cls is FinanceContract

    def test_health_contract_resolvable(self):
        cls = get_contract("health")
        assert cls is HealthContract

    def test_unknown_contract_returns_none(self):
        cls = get_contract("nonexistent_contract")
        assert cls is None

    def test_registry_not_empty(self):
        assert len(CONTRACT_REGISTRY) >= 3
