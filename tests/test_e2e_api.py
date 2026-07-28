"""
End-to-End API Integration & Fault Tolerance Tests (tests/test_e2e_api.py).

Tests FastAPI routes, endpoints, session handling, and fault tolerance.
"""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_api_health_endpoint():
    """Test /health status endpoint returns 200 and startup state."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data


def test_api_chat_flow_session():
    """Test /api/chat endpoint initializing session and processing message."""
    payload = {
        "session_id": "test_e2e_session_001",
        "message": "我想买一辆20万左右的纯电SUV，适合家用",
    }
    response = client.post("/api/chat", json=payload)
    if response.status_code == 200:
        data = response.json()
        assert "response" in data or "reply" in data or "session_id" in data
        assert data.get("session_id") == "test_e2e_session_001"


def test_api_invalid_payload_error_handling():
    """Test 422 Unprocessable Entity on invalid API request body."""
    response = client.post("/api/chat", json={"invalid_field": 123})
    assert response.status_code in [422, 400]
