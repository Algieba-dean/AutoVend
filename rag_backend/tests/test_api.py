"""
Integration tests for FastAPI API routes.

Uses httpx AsyncClient with mock LLM to test all endpoints
without actual LLM calls or vector index.
"""

import json
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.routes.chat import set_workflow
from app.workflow.stage_workflow import StageWorkflow


def _mock_llm() -> MagicMock:
    """Create a mock LLM for testing."""
    mock = MagicMock()

    def side_effect(prompt):
        resp = MagicMock()
        if "profile" in prompt.lower() and "extract" in prompt.lower():
            resp.text = json.dumps({"name": "TestUser", "age": "30"})
        elif "vehicle requirements" in prompt.lower() or "explicit" in prompt.lower():
            resp.text = json.dumps({"brand": "Tesla"})
        elif "deduce" in prompt.lower() or "implicit" in prompt.lower():
            resp.text = json.dumps({"comfort_level": "High"})
        elif "reservation" in prompt.lower() and "extract" in prompt.lower():
            resp.text = json.dumps({})
        else:
            resp.text = "Hello! Welcome to AutoVend."
        return resp

    mock.complete.side_effect = side_effect
    return mock


@pytest.fixture
def workflow():
    """Create a workflow with mock LLM."""
    llm = _mock_llm()
    wf = StageWorkflow(llm=llm, vehicle_index=None)
    set_workflow(wf)
    return wf


@pytest.fixture
async def client(workflow):
    """Create an async test client."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ============================================================
# Health / Root
# ============================================================

class TestRootEndpoints:
    @pytest.mark.asyncio
    async def test_root(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "AutoVend RAG API"

    @pytest.mark.asyncio
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ============================================================
# Chat endpoints
# ============================================================

class TestChatAPI:
    @pytest.mark.asyncio
    async def test_create_session(self, client):
        resp = await client.post(
            "/api/chat/session",
            json={"phone_number": "13800000000"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["stage"]["current_stage"] == "welcome"

    @pytest.mark.asyncio
    async def test_send_message(self, client):
        # Create session first
        resp = await client.post(
            "/api/chat/session",
            json={"phone_number": "13800000001"},
        )
        session_id = resp.json()["session_id"]

        # Send message
        resp = await client.post(
            "/api/chat/message",
            json={"session_id": session_id, "message": "Hello, I want to buy a car"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"]["content"] == "Hello, I want to buy a car"
        assert data["response"]["content"]  # Non-empty
        assert data["response"]["sender_id"] == "AutoVend"

    @pytest.mark.asyncio
    async def test_send_message_auto_creates_session(self, client):
        resp = await client.post(
            "/api/chat/message",
            json={"session_id": "auto_session", "message": "Hi there"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_messages(self, client):
        # Create session and send a message
        resp = await client.post(
            "/api/chat/session",
            json={"phone_number": "13800000002"},
        )
        session_id = resp.json()["session_id"]

        await client.post(
            "/api/chat/message",
            json={"session_id": session_id, "message": "Hello"},
        )

        # Get messages
        resp = await client.get(f"/api/chat/session/{session_id}/messages")
        assert resp.status_code == 200
        assert "history" in resp.json()

    @pytest.mark.asyncio
    async def test_get_messages_not_found(self, client):
        resp = await client.get("/api/chat/session/nonexistent/messages")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_end_session(self, client):
        resp = await client.post(
            "/api/chat/session",
            json={"phone_number": "13800000003"},
        )
        session_id = resp.json()["session_id"]

        resp = await client.put(f"/api/chat/session/{session_id}/end")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_end_session_not_found(self, client):
        resp = await client.put("/api/chat/session/nonexistent/end")
        assert resp.status_code == 404


# ============================================================
# Profile endpoints
# ============================================================

class TestProfileAPI:
    @pytest.mark.asyncio
    async def test_get_default_profile(self, client):
        resp = await client.get("/api/profile/default")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == ""

    @pytest.mark.asyncio
    async def test_create_profile(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.PROFILES_DIR", tmp_path)

        resp = await client.post(
            "/api/profile",
            json={"phone_number": "13900000001", "name": "John"},
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "John"

    @pytest.mark.asyncio
    async def test_create_profile_no_phone(self, client):
        resp = await client.post("/api/profile", json={"name": "John"})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_profile_duplicate(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.PROFILES_DIR", tmp_path)

        await client.post(
            "/api/profile",
            json={"phone_number": "13900000002", "name": "John"},
        )
        resp = await client.post(
            "/api/profile",
            json={"phone_number": "13900000002", "name": "John"},
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_get_profile(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.PROFILES_DIR", tmp_path)

        await client.post(
            "/api/profile",
            json={"phone_number": "13900000003", "name": "Alice"},
        )
        resp = await client.get("/api/profile/13900000003")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.PROFILES_DIR", tmp_path)
        resp = await client.get("/api/profile/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_profile(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.PROFILES_DIR", tmp_path)

        await client.post(
            "/api/profile",
            json={"phone_number": "13900000004", "name": "Bob"},
        )
        resp = await client.put(
            "/api/profile/13900000004",
            json={"phone_number": "13900000004", "age": "25"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Bob"  # Preserved
        assert resp.json()["age"] == "25"  # Updated

    @pytest.mark.asyncio
    async def test_delete_profile(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.PROFILES_DIR", tmp_path)

        await client.post(
            "/api/profile",
            json={"phone_number": "13900000005", "name": "Eve"},
        )
        resp = await client.delete("/api/profile/13900000005")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_profiles(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.PROFILES_DIR", tmp_path)

        await client.post(
            "/api/profile",
            json={"phone_number": "13900000006", "name": "A"},
        )
        resp = await client.get("/api/profile")
        assert resp.status_code == 200
        assert "13900000006" in resp.json()


# ============================================================
# Test Drive endpoints
# ============================================================

class TestTestDriveAPI:
    @pytest.mark.asyncio
    async def test_create_test_drive(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.TEST_DRIVES_DIR", tmp_path)

        resp = await client.post(
            "/api/test-drive",
            json={
                "phone_number": "14000000001",
                "test_driver": "John",
                "reservation_date": "2024-03-15",
                "reservation_time": "14:00",
                "reservation_location": "Downtown",
                "car_model": "Tesla-Model Y",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["phone_number"] == "14000000001"
        assert data["reservation"]["test_driver"] == "John"
        assert data["car_model"] == "Tesla-Model Y"

    @pytest.mark.asyncio
    async def test_create_test_drive_no_phone(self, client):
        resp = await client.post("/api/test-drive", json={"test_driver": "John"})
        assert resp.status_code == 422  # Pydantic validation: phone_number required

    @pytest.mark.asyncio
    async def test_get_test_drive(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.TEST_DRIVES_DIR", tmp_path)

        await client.post(
            "/api/test-drive",
            json={"phone_number": "14000000002", "test_driver": "Alice"},
        )
        resp = await client.get("/api/test-drive/14000000002")
        assert resp.status_code == 200
        assert resp.json()["reservation"]["test_driver"] == "Alice"

    @pytest.mark.asyncio
    async def test_get_test_drive_not_found(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.TEST_DRIVES_DIR", tmp_path)
        resp = await client.get("/api/test-drive/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_test_drive(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.TEST_DRIVES_DIR", tmp_path)

        await client.post(
            "/api/test-drive",
            json={"phone_number": "14000000003", "test_driver": "Bob"},
        )
        resp = await client.put(
            "/api/test-drive/14000000003",
            json={
                "phone_number": "14000000003",
                "reservation_time": "15:00",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["reservation"]["test_driver"] == "Bob"  # Preserved
        assert resp.json()["reservation"]["reservation_time"] == "15:00"  # Updated

    @pytest.mark.asyncio
    async def test_delete_test_drive(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.TEST_DRIVES_DIR", tmp_path)

        await client.post(
            "/api/test-drive",
            json={"phone_number": "14000000004", "test_driver": "Eve"},
        )
        resp = await client.delete("/api/test-drive/14000000004")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_test_drives(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.TEST_DRIVES_DIR", tmp_path)

        await client.post(
            "/api/test-drive",
            json={"phone_number": "14000000005", "test_driver": "X"},
        )
        resp = await client.get("/api/test-drive")
        assert resp.status_code == 200
        assert "14000000005" in resp.json()
