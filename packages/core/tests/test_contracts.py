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
  FinanceContract,
    GDPRUserContract,
    HealthContract,
    get_contract,
)

# ---------------------------------------------------------------------------
# Fixtures — all user_ids must be strings (will be pseudonymised)
# ---------------------------------------------------------------------------
VALID_GDPR = dict(
    user_id="user-001",
    age=25,
    email="top_secret@example.com",
    consent_level=2,
    gdpr_accepted=True,
)

VALID_FINANCE = dict(
    user_id="user-002",
    age=30,
    email="finance@example.com",
    consent_level=3,
    gdpr_accepted=True,
    annual_income_range="20-50k",
    credit_score_band="good",
    account_hash="abc123hash_sha256_16chars",
)

VALID_HEALTH = dict(
    user_id="user-003",
    age=40,
    email="health@example.com",
    consent_level=4,
    gdpr_accepted=True,
    icd10_codes=["A01.0", "Z00.0"],
            treatment_category="diagnostic",
    data_controller_id="clinic-pseudonymised-id",
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

    def test_missing_consent_rejected(self):
        """Mason MUST reject if gdpr_accepted=False."""
        payload = {**VALID_GDPR, "gdpr_accepted": False}
        with pytest.raises(ValidationError):
            GDPRUserContract(**payload)

    def test_low_consent_level_rejected(self):
        """Consent level 1 is insufficient for any processing."""
        payload = {**VALID_GDPR, "consent_level": 1}
        with pytest.raises(ValidationError):
            GDPRUserContract(**payload)

    def test_invalid_email_rejected(self):
        """Emails without @ separator are structurally invalid."""
        payload = {**VALID_GDPR, "email": "notanemail"}
        with pytest.raises(ValidationError):
            GDPRUserContract(**payload)

    def test_unknown_field_rejected(self):
        """extra=forbid: unknown fields must be structurally rejected."""
        payload = {**VALID_GDPR, "unknown_field": "sneaky_data"}
        with pytest.raises(ValidationError):
            GDPRUserContract(**payload)


class TestGDPRContractAcceptance:
    def test_valid_user_accepted(self):
        """Happy-path: valid adult with consent should be accepted."""
        c = GDPRUserContract(**VALID_GDPR)
        assert c.age == 25

    def test_email_masked_at_ingestion(self):
        """Email local part must be masked immediately at the boundary."""
        c = GDPRUserContract(**VALID_GDPR)
        # e.g. top_secret@example.com -> t***@example.com
        assert "@example.com" in c.email
        assert "top_secret" not in c.email

    def test_user_id_pseudonymised(self):
        """user_id must be pseudonymised (SHA-256 prefix, not the original)."""
        c = GDPRUserContract(**VALID_GDPR)
        assert c.user_id != "user-001"
        assert len(c.user_id) == 16  # SHA-256 hexdigest[:16]

    def test_safe_dict_returns_masked_data(self):
        """to_safe_dict() must never expose raw PII."""
        c = GDPRUserContract(**VALID_GDPR)
        d = c.to_safe_dict()
        assert "top_secret" not in str(d)
        assert "user-001" not in str(d)


# ---------------------------------------------------------------------------
# Finance Contract
# ---------------------------------------------------------------------------
class TestFinanceContract:
    def test_valid_finance_accepted(self):
        c = FinanceContract(**VALID_FINANCE)
        assert c.credit_score_band == "good"

    def test_finance_requires_consent_level_3(self):
        payload = {**VALID_FINANCE, "consent_level": 2}
        with pytest.raises(ValidationError):
            FinanceContract(**payload)

    def test_invalid_credit_band_rejected(self):
        payload = {**VALID_FINANCE, "credit_score_band": "A+"}
        with pytest.raises(ValidationError):
            FinanceContract(**payload)

    def test_short_account_hash_rejected(self):
        payload = {**VALID_FINANCE, "account_hash": "short"}
        with pytest.raises(ValidationError):
            FinanceContract(**payload)


# ---------------------------------------------------------------------------
# Health Contract
# ---------------------------------------------------------------------------
class TestHealthContract:
    def test_valid_health_accepted(self):
        c = HealthContract(**VALID_HEALTH)
                assert c.treatment_category == "diagnostic"

    def test_health_requires_consent_level_4(self):
        payload = {**VALID_HEALTH, "consent_level": 3}
        with pytest.raises(ValidationError):
            HealthContract(**payload)

    def test_invalid_icd10_rejected(self):
        payload = {**VALID_HEALTH, "icd10_codes": ["flu", "cold"]}
        with pytest.raises(ValidationError):
            HealthContract(**payload)

    def test_invalid_treatment_category_rejected(self):
        payload = {**VALID_HEALTH, "treatment_category": "surgery"}
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

    def test_long_names_also_work(self):
        assert get_contract("gdpr_basic") is GDPRUserContract
        assert get_contract("finance_trust") is FinanceContract
        assert get_contract("health_trust") is HealthContract

    def test_unknown_contract_returns_none(self):
        with pytest.raises(KeyError):
            get_contract("nonexistent_contract")
