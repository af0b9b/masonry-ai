from masonry_core.contracts import GDPRUserContract
from masonry_core.gatekeeper import mason_gate, mason_gate_and_sanitise


def test_mason_gate_validates_and_masks_payload() -> None:
    result = mason_gate(
        GDPRUserContract,
        {
            "user_id": "abc-123",
            "age": 24,
            "email": "user@example.com",
            "consent_level": 2,
            "gdpr_accepted": True,
        },
    )

    assert result.user_id != "abc-123"
    assert result.email.endswith("@example.com")


def test_mason_gate_and_sanitise_returns_dict() -> None:
    result = mason_gate_and_sanitise(
        GDPRUserContract,
        {
            "user_id": "abc-123",
            "age": 24,
            "email": "user@example.com",
            "consent_level": 2,
            "gdpr_accepted": True,
        },
    )

    assert isinstance(result, dict)
    assert "user_id" in result
