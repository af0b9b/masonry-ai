"""test_dp.py — Pytest suite for the Differential Privacy filter.

Covers:
  - DPConfig validation (epsilon, delta, sensitivity bounds)
  - Epsilon budget exhaustion
  - k-anonymity quasi-identifier generalisation
  - Laplace noise injection (statistical test)
  - sanitise() high-level API
  - from_contract() sensitivity derivation for FinanceContract
"""
import pytest

from masonry_core.dp_filter import (
    EPSILON_MAX_PER_TENANT,
    DPConfig,
    _check_epsilon_budget,
    _k_anonymise_record,
    apply_dp_pipeline,
    reset_epsilon_budget,
    sanitise,
)


# ---------------------------------------------------------------------------
# DPConfig validation
# ---------------------------------------------------------------------------
class TestDPConfigValidation:
    def test_valid_config_created(self):
        cfg = DPConfig(epsilon=1.0, sensitivity=1.0)
        assert cfg.epsilon == 1.0

    def test_zero_epsilon_rejected(self):
        with pytest.raises(ValueError, match="epsilon must be > 0"):
            DPConfig(epsilon=0.0)

    def test_negative_epsilon_rejected(self):
        with pytest.raises(ValueError, match="epsilon must be > 0"):
            DPConfig(epsilon=-0.5)

    def test_zero_sensitivity_rejected(self):
        with pytest.raises(ValueError, match="sensitivity must be > 0"):
            DPConfig(sensitivity=0.0)

    def test_invalid_delta_rejected(self):
        with pytest.raises(ValueError, match="delta must be in"):
            DPConfig(delta=1.5)


# ---------------------------------------------------------------------------
# Epsilon budget tracker
# ---------------------------------------------------------------------------
class TestEpsilonBudget:
    def setup_method(self):
        """Each test gets a fresh tenant budget."""
        reset_epsilon_budget("test-tenant")

    def test_budget_consumed_incrementally(self):
        _check_epsilon_budget("test-tenant", 1.0)
        _check_epsilon_budget("test-tenant", 1.0)
        # No error after 2.0 spent

    def test_budget_exhausted_raises(self):
        # Exhaust budget
        _check_epsilon_budget("test-tenant", EPSILON_MAX_PER_TENANT)
        with pytest.raises(RuntimeError, match="epsilon budget exhausted"):
            _check_epsilon_budget("test-tenant", 0.01)

    def test_budget_reset_allows_new_queries(self):
        _check_epsilon_budget("test-tenant", EPSILON_MAX_PER_TENANT)
        reset_epsilon_budget("test-tenant")
        # Should not raise after reset
        _check_epsilon_budget("test-tenant", 1.0)


# ---------------------------------------------------------------------------
# k-anonymity
# ---------------------------------------------------------------------------
class TestKAnonymity:
    def test_age_generalised_to_decade(self):
        record = {"user_id": "hash123", "age": 37}
        out = _k_anonymise_record(record, quasi_ids=["age"], k=5)
        assert out["age"] == 30  # 37 -> 30s bracket

    def test_non_quasi_fields_untouched(self):
        record = {"user_id": "hash123", "age": 25, "email": "x***@example.com"}
        out = _k_anonymise_record(record, quasi_ids=["age"], k=5)
        assert out["email"] == "x***@example.com"

    def test_missing_quasi_field_skipped(self):
        record = {"user_id": "hash123"}  # no 'age'
        out = _k_anonymise_record(record, quasi_ids=["age"], k=5)
        assert "age" not in out  # no error, field just absent


# ---------------------------------------------------------------------------
# Noise injection
# ---------------------------------------------------------------------------
class TestNoiseInjection:
    def test_laplace_noise_modifies_value(self):
        """With epsilon=0.01 (strong noise), the output must differ from input."""
        cfg = DPConfig(epsilon=0.01, sensitivity=100.0, numeric_fields=["score"])
        reset_epsilon_budget("noise-test")
        record = {"score": 500.0, "age": 25}
        out = apply_dp_pipeline(record, cfg, tenant_id="noise-test")
        # Statistical: probability of identical result is negligible
        assert out["score"] != 500.0

    def test_noise_pipeline_does_not_modify_non_numeric(self):
        cfg = DPConfig(epsilon=1.0, sensitivity=1.0, numeric_fields=["score"])
        reset_epsilon_budget("noise-test2")
        record = {"score": 100.0, "email": "x***@example.com"}
        out = apply_dp_pipeline(record, cfg, tenant_id="noise-test2")
        assert out["email"] == "x***@example.com"


# ---------------------------------------------------------------------------
# sanitise() high-level API
# ---------------------------------------------------------------------------
class TestSanitiseAPI:
    def setup_method(self):
        reset_epsilon_budget("sanitise-test")

    def test_sanitise_returns_dict(self):
        data = {"user_id": "hash", "age": 29, "email": "x***@example.com"}
        out = sanitise(data, tenant_id="sanitise-test")
        assert isinstance(out, dict)

    def test_sanitise_k_anonymises_age(self):
        data = {"user_id": "hash", "age": 29}
        out = sanitise(data, quasi_identifiers=["age"], tenant_id="sanitise-test")
        assert out["age"] == 20  # 29 -> 20s

    def test_sanitise_consumes_epsilon_budget(self):
        """Calling sanitise repeatedly must eventually exhaust budget."""
        tenant = "budget-drain"
        reset_epsilon_budget(tenant)
        with pytest.raises(RuntimeError, match="epsilon budget exhausted"):
            for _ in range(int(EPSILON_MAX_PER_TENANT) + 2):
                sanitise({"age": 30}, epsilon=1.0, tenant_id=tenant)
