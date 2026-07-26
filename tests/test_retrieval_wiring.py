"""
Tests for the retrieval wiring between the hybrid pipeline and the chat route.

Covers `src/retrieval/adapters.py` (shape conversion) and
`backend/app/routes/chat.py::_retrieve_cars` (stage gating, needs-change cache,
failure degradation). The pipeline itself is stubbed — these tests assert the
contract between the layers, not retrieval quality, which is what the
evaluation gate measures.
"""

from types import SimpleNamespace

import pytest

from backend.app.routes import chat as chat_route
from src.agent.schemas import SessionState, Stage
from src.retrieval.adapters import (
    hybrid_result_to_cars,
    needs_to_query_text,
    search_response_to_cars,
)


def _make_search_result(car_model: str, score: float, *, snippet: str = "details"):
    """Build the minimal duck-typed stand-in for a `SearchResult`."""
    return SimpleNamespace(
        vehicle=SimpleNamespace(
            car_model=car_model,
            precise_labels=SimpleNamespace(
                brand="BMW",
                prize="30,000~40,000",
                vehicle_category_bottom="Mid-Size SUV",
                powertrain_type=None,
            ),
            ambiguous_labels=SimpleNamespace(
                size="Medium",
                family_friendliness=None,
                comfort_level="High",
            ),
            key_details=SimpleNamespace(key_details=snippet),
        ),
        score=SimpleNamespace(overall_score=score),
    )


def _make_response(*results):
    return SimpleNamespace(results=list(results))


class TestAdapters:
    def test_converts_to_the_agent_car_shape(self):
        response = _make_response(_make_search_result("BMW-X3", 0.8123))

        cars = search_response_to_cars(response)

        assert cars == [
            {
                "car_model": "BMW-X3",
                "score": 0.8123,
                "metadata": {
                    "car_model": "BMW-X3",
                    "brand": "BMW",
                    "price": "30,000~40,000",
                    "category": "Mid-Size SUV",
                    "size": "Medium",
                    "comfort_level": "High",
                },
                "text_snippet": "details",
            }
        ]

    def test_drops_unpopulated_labels_from_metadata(self):
        cars = search_response_to_cars(_make_response(_make_search_result("BMW-X3", 0.5)))

        # powertrain_type and family_friendliness were None on the source vehicle.
        assert "powertrain_type" not in cars[0]["metadata"]
        assert "family_friendliness" not in cars[0]["metadata"]

    def test_truncates_long_snippets(self):
        long_text = "x" * 500
        cars = search_response_to_cars(
            _make_response(_make_search_result("BMW-X3", 0.5, snippet=long_text))
        )

        assert len(cars[0]["text_snippet"]) == 300

    def test_applies_limit(self):
        response = _make_response(
            *[_make_search_result(f"car-{i}", 0.9 - i / 10) for i in range(6)]
        )

        assert len(search_response_to_cars(response, limit=3)) == 3

    @pytest.mark.parametrize("empty", [None, SimpleNamespace(results=[])])
    def test_empty_input_yields_empty_list(self, empty):
        assert search_response_to_cars(empty) == []
        assert hybrid_result_to_cars(None) == []

    def test_hybrid_result_unwraps_search_response(self):
        result = SimpleNamespace(search_response=_make_response(_make_search_result("BMW-X3", 0.5)))

        assert hybrid_result_to_cars(result)[0]["car_model"] == "BMW-X3"

    def test_hybrid_result_without_response_yields_empty_list(self):
        assert hybrid_result_to_cars(SimpleNamespace(search_response=None)) == []


class TestNeedsToQueryText:
    def test_emits_label_values_verbatim(self):
        explicit = SimpleNamespace(
            vehicle_category_bottom="Mid-Size SUV",
            powertrain_type="Battery Electric Vehicle",
            design_style="",
            seat_layout="",
            brand="NIO",
            prize="30,000~40,000",
        )

        # The rule parser matches against the same vocabulary the extractors
        # write, so values must not be paraphrased or wrapped in prose.
        assert needs_to_query_text(explicit) == (
            "Mid-Size SUV Battery Electric Vehicle NIO 30,000~40,000"
        )

    def test_falls_back_when_no_needs_are_known(self):
        explicit = SimpleNamespace(
            vehicle_category_bottom="",
            powertrain_type="",
            design_style="",
            seat_layout="",
            brand="",
            prize="",
        )

        assert needs_to_query_text(explicit) == "recommend a good vehicle"


class _StubPipeline:
    """Records calls and returns a fixed result."""

    def __init__(self, cars=("BMW-X3",), fail=False):
        self.calls = []
        self._cars = cars
        self._fail = fail

    def search(self, query_text, top_k=10):
        self.calls.append((query_text, top_k))
        if self._fail:
            raise RuntimeError("index unavailable")
        return SimpleNamespace(
            search_response=_make_response(*[_make_search_result(c, 0.7) for c in self._cars]),
            candidate_count=len(self._cars),
            degrade_level=0,
            total_time=0.01,
        )


@pytest.fixture
def pipeline():
    """Install a stub pipeline and reset the per-session needs cache."""
    stub = _StubPipeline()
    chat_route.set_pipeline(stub)
    chat_route._prev_explicit.clear()
    yield stub
    chat_route.set_pipeline(None)
    chat_route._prev_explicit.clear()


def _state(stage=Stage.NEEDS_ANALYSIS, session_id="s1"):
    state = SessionState(session_id=session_id, stage=stage)
    state.needs.explicit.vehicle_category_bottom = "Mid-Size SUV"
    return state


class TestRetrieveCars:
    def test_retrieves_during_needs_analysis(self, pipeline):
        cars = chat_route._retrieve_cars(_state(Stage.NEEDS_ANALYSIS))

        assert [c["car_model"] for c in cars] == ["BMW-X3"]
        assert pipeline.calls == [("Mid-Size SUV", chat_route.RETRIEVAL_TOP_K)]

    def test_retrieves_during_car_selection(self, pipeline):
        chat_route._retrieve_cars(_state(Stage.CAR_SELECTION))

        assert len(pipeline.calls) == 1

    @pytest.mark.parametrize("stage", [Stage.WELCOME, Stage.PROFILE_ANALYSIS, Stage.RESERVATION_4S])
    def test_skips_retrieval_outside_recommendation_stages(self, pipeline, stage):
        state = _state(stage)
        state.matched_cars = [{"car_model": "previous"}]

        cars = chat_route._retrieve_cars(state)

        assert pipeline.calls == []
        assert cars == [{"car_model": "previous"}]

    def test_reuses_previous_cars_when_needs_are_unchanged(self, pipeline):
        state = _state()
        first = chat_route._retrieve_cars(state)
        state.matched_cars = first

        second = chat_route._retrieve_cars(state)

        assert len(pipeline.calls) == 1, "unchanged needs must not re-query the index"
        assert second == first

    def test_requeries_when_needs_change(self, pipeline):
        state = _state()
        state.matched_cars = chat_route._retrieve_cars(state)

        state.needs.explicit.brand = "NIO"
        chat_route._retrieve_cars(state)

        assert len(pipeline.calls) == 2
        assert pipeline.calls[1][0] == "Mid-Size SUV NIO"

    def test_keeps_previous_cars_when_retrieval_fails(self):
        chat_route.set_pipeline(_StubPipeline(fail=True))
        chat_route._prev_explicit.clear()
        state = _state()
        state.matched_cars = [{"car_model": "previous"}]

        try:
            assert chat_route._retrieve_cars(state) == [{"car_model": "previous"}]
        finally:
            chat_route.set_pipeline(None)
            chat_route._prev_explicit.clear()

    def test_keeps_previous_cars_when_retrieval_returns_nothing(self):
        chat_route.set_pipeline(_StubPipeline(cars=()))
        chat_route._prev_explicit.clear()
        state = _state()
        state.matched_cars = [{"car_model": "previous"}]

        try:
            # An empty result is worse than a stale one — the agent needs
            # something concrete to talk about.
            assert chat_route._retrieve_cars(state) == [{"car_model": "previous"}]
        finally:
            chat_route.set_pipeline(None)
            chat_route._prev_explicit.clear()

    def test_returns_empty_when_no_pipeline_is_configured(self):
        chat_route.set_pipeline(None)

        assert chat_route._retrieve_cars(_state()) == []


class TestRetrievalOrdering:
    """
    Regression guard for the observe -> retrieve -> respond ordering.

    Retrieving before extraction queries the index with the *previous* turn's
    needs: a user who asks for a mid-size electric SUV gets recommendations for
    whatever they asked for one turn earlier. This drives the real route so the
    ordering is asserted where it actually lives.
    """

    async def test_route_retrieves_with_this_turns_needs(self):
        from httpx import ASGITransport, AsyncClient

        from backend.app.main import _startup_status, app
        from src.agent.schemas import AgentResult, Stage

        class _ExtractingAgent:
            """Fills in this turn's needs during observe(), like the real extractors."""

            def observe(self, state, user_message):
                updated = state.model_copy(deep=True)
                updated.stage = Stage.NEEDS_ANALYSIS
                updated.needs.explicit.vehicle_category_bottom = "Mid-Size SUV"
                updated.needs.explicit.powertrain_type = "Battery Electric Vehicle"
                return updated

            def respond(self, state, retrieved_cars=None):
                updated = state.model_copy(deep=True)
                updated.matched_cars = retrieved_cars or []
                return AgentResult(session_state=updated, response_text="ok", stage_changed=False)

        stub = _StubPipeline(cars=("BMW-iX",))
        chat_route.set_agent(_ExtractingAgent())
        chat_route.set_pipeline(stub)
        chat_route._sessions.clear()
        chat_route._prev_explicit.clear()
        _startup_status["agent_ready"] = True

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/chat/message",
                    json={"session_id": "ordering", "message": "我想要中型纯电SUV"},
                )

            assert response.status_code == 200
            assert stub.calls, "the route never queried the index"
            assert stub.calls[0][0] == "Mid-Size SUV Battery Electric Vehicle", (
                "retrieval ran against stale needs — observe() must precede _retrieve_cars()"
            )
            assert [c["car_model"] for c in response.json()["matched_car_models"]] == ["BMW-iX"]
        finally:
            chat_route.set_pipeline(None)
            chat_route._sessions.clear()
            chat_route._prev_explicit.clear()
