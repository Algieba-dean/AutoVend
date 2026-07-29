"""
Unit tests for Hermes Agent Enhancements (tests/test_hermes_enhancements.py).

Tests ErrorClassifier, AgentSelfHealingLoop, and VerificationEvidenceLedger.
"""

from src.agent.error_recovery import AgentErrorCategory, AgentSelfHealingLoop, ErrorClassifier
from src.agent.evidence_ledger import VerificationEvidenceLedger


def test_error_classifier_schema_mismatch():
    """Test ErrorClassifier classifying Pydantic schema validation errors."""
    err = ValueError("JSON output validation failed for field 'prize'")
    hint = ErrorClassifier.classify(err)

    assert hint.category == AgentErrorCategory.SCHEMA_MISMATCH
    assert hint.should_retry is True
    assert "Pydantic" in hint.hint_text or "JSON" in hint.hint_text


def test_error_classifier_timeout():
    """Test ErrorClassifier classifying transient timeout errors."""
    err = TimeoutError("Connection timeout to vLLM server")
    hint = ErrorClassifier.classify(err)

    assert hint.category == AgentErrorCategory.TRANSIENT_TIMEOUT
    assert hint.should_retry is True


def test_verification_evidence_ledger():
    """Test VerificationEvidenceLedger verifying phone, car model, and 4S store."""
    ledger = VerificationEvidenceLedger()

    # 1. Valid phone
    assert ledger.verify_phone_number("13812345678") is True
    # 2. Invalid phone
    assert ledger.verify_phone_number("12345") is False

    # 3. Car model verification
    assert ledger.verify_car_model_exists("理想L7", ["理想L7 Max", "问界M7"]) is True
    assert ledger.verify_car_model_exists("保时捷911", ["理想L7", "问界M7"]) is False

    # 4. Store verification
    assert ledger.verify_4s_store("上海浦东理想体验中心") is True

    # 5. Check reservation confirmation gate
    can_confirm, missing = ledger.can_confirm_reservation()
    assert can_confirm is True
    assert missing == []


def test_self_healing_loop_retry():
    """Test AgentSelfHealingLoop executing retries on failure."""
    loop = AgentSelfHealingLoop(max_retries=2)
    attempts = 0

    def flaky_function():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ValueError("Validation error in JSON response")
        return "SUCCESS"

    result = loop.execute_with_self_healing("session_test", flaky_function)
    assert result == "SUCCESS"
    assert attempts == 2
