"""
Unit tests for Architecture Decoupling & Agent Plugin Pipeline (tests/test_architecture_decoupling.py).
"""

from src.agent.plugins import AgentPluginPipeline, BattlecardPlugin, ConstraintReconcilerPlugin, ReflectionGuardPlugin
from src.agent.schemas import SessionState
from src.core.container import ServiceContainer
from src.core.interfaces import BaseRAGService, RAGQueryRequest, RAGQueryResponse


class DummyRAGService(BaseRAGService):
    """Mock RAG Service for Container testing."""

    def search_vehicles(self, request: RAGQueryRequest) -> RAGQueryResponse:
        return RAGQueryResponse(results=[{"car_model": "TestModel"}], total_count=1)

    def get_vehicle_detail(self, car_model: str):
        return {"car_model": car_model, "brand": "Mock"}


def test_service_container():
    """Test registering and resolving RAG service via ServiceContainer."""
    ServiceContainer.reset()
    dummy = DummyRAGService()
    ServiceContainer.register_rag_service(dummy)

    service = ServiceContainer.get_rag_service()
    res = service.search_vehicles(RAGQueryRequest(query_text="测试"))
    assert res.total_count == 1
    assert res.results[0]["car_model"] == "TestModel"


def test_agent_plugin_pipeline():
    """Test pre-processing and post-processing plugin pipeline execution."""
    pipeline = AgentPluginPipeline()
    state = SessionState()
    state.profile.family_size = "5"
    state.needs.explicit.brand = "保时捷"
    state.needs.explicit.prize = "below 20,000"

    context = {"user_input": "我想看看特斯拉 Model Y 比亚迪汉"}

    # Run pre-processing plugins
    pipeline.run_before_response(state, context)

    # Check constraint reconciliation & battlecard notes were injected into system_notes list
    assert len(state.system_notes) > 0
    assert context.get("battlecards_matched", 0) > 0

    # Run post-processing reflection plugin
    response_input = "推荐您保时捷和特斯拉 Model Y，售价保证全网最低价"
    guarded_output = pipeline.run_after_response(response_input, context)

    # Redacted forbidden promise
    assert "保证全网最低价" not in guarded_output
