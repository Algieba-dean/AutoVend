"""
End-to-end check: a chat turn reaches the real hybrid retrieval pipeline and
comes back through the API as populated `matched_car_models`.

Unlike tests/test_retrieval_wiring.py, nothing here is stubbed on the retrieval
side — this exercises the actual SQLite catalogue, BGE-M3 embeddings and
ChromaDB index. Only the LLM is mocked, so the test runs without credentials.

Marked `slow` because loading the embedding model costs ~15s on a cold start.
Run with:  pytest -m slow
"""

import json
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.slow


def _needs_driven_llm() -> MagicMock:
    """
    Mock LLM that reports a concrete vehicle need on every extraction call.

    This is what pushes the FSM past profile_analysis into needs_analysis, which
    is the only stage where retrieval runs.
    """
    mock = MagicMock()

    def side_effect(prompt):
        resp = MagicMock()
        lowered = prompt.lower()
        if "profile" in lowered and "extract" in lowered:
            resp.text = json.dumps(
                {
                    "name": "TestUser",
                    "age": "30",
                    "family_size": "3",
                    "residence": "Shanghai",
                    "parking_conditions": "Fixed parking space",
                    "price_sensitivity": "Medium",
                    "target_driver": "Self",
                    "expertise": "Novice",
                    "title": "Engineer",
                }
            )
        elif "explicit" in lowered or "vehicle requirements" in lowered:
            resp.text = json.dumps(
                {
                    "vehicle_category_bottom": "Mid-Size SUV",
                    "powertrain_type": "Battery Electric Vehicle",
                }
            )
        elif "deduce" in lowered or "implicit" in lowered:
            resp.text = json.dumps({"comfort_level": "High", "family_friendliness": "High"})
        elif "reservation" in lowered:
            resp.text = json.dumps({})
        else:
            resp.text = "Here are some vehicles that match your needs."
        return resp

    mock.complete.side_effect = side_effect
    return mock


@pytest.fixture(scope="module")
def pipeline():
    """Build the real pipeline once — the embedding model load dominates runtime."""
    from src.retrieval.hybrid_pipeline import build_default_pipeline

    try:
        built = build_default_pipeline(enable_llm_parser=False)
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"retrieval indices unavailable: {exc}")

    if built.db.count() == 0:
        pytest.skip("vehicle catalogue is empty — run `python -m src.main build-index`")

    return built


@pytest.fixture
async def client(pipeline, tmp_path, monkeypatch):
    from backend.app.main import _startup_status, app
    from backend.app.routes.chat import _prev_explicit, _sessions, set_agent, set_pipeline
    from src.agent.sales_agent import SalesAgent

    set_agent(SalesAgent(llm=_needs_driven_llm()))
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    monkeypatch.setattr("backend.app.models.storage.SESSIONS_DIR", sessions_dir)
    set_pipeline(pipeline)
    _startup_status["agent_ready"] = True
    _sessions.clear()
    _prev_explicit.clear()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    set_pipeline(None)
    _sessions.clear()
    _prev_explicit.clear()


async def test_chat_turn_returns_cars_from_the_hybrid_pipeline(client):
    created = await client.post("/api/chat/session", json={"phone_number": "13888888888"})
    assert created.status_code == 200
    session_id = created.json()["session_id"]

    cars = []
    stages = []
    # The FSM needs a few turns to walk welcome -> profile_analysis -> needs_analysis.
    for message in ["你好", "我想买车", "中型纯电SUV，家用", "预算30万"]:
        response = await client.post(
            "/api/chat/message", json={"session_id": session_id, "message": message}
        )
        assert response.status_code == 200
        body = response.json()
        stages.append(body["stage"]["current_stage"])
        if body["matched_car_models"]:
            cars = body["matched_car_models"]
            break

    assert cars, f"no vehicles retrieved; stages visited: {stages}"

    # Shape contract consumed by Chat.js and by the agent's recommendation prompt.
    first = cars[0]
    assert isinstance(first["car_model"], str) and first["car_model"]
    assert 0.0 <= first["score"] <= 1.0
    assert first["metadata"]["car_model"] == first["car_model"]

    # The structured pre-filter should have honoured the extracted category,
    # not just returned whatever the vector search liked best.
    categories = {c["metadata"].get("category", "") for c in cars}
    assert any("SUV" in c for c in categories), f"expected SUVs, got {categories}"
