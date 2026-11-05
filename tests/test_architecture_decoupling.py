"""
Unit tests for Architecture Decoupling & Agent Plugin Pipeline (tests/test_architecture_decoupling.py).
"""

from src.agent.plugins import AgentPluginPipeline
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
    state.needs.explicit.price = "below 20,000"

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


def test_rag_service_implements_base_rag_service():
    """Verify RAGService inherits from BaseRAGService and accepts RAGQueryRequest."""
    from dataclasses import dataclass, field

    from src.rag_service.service import RAGService

    assert issubclass(RAGService, BaseRAGService)

    @dataclass
    class _MockPipelineResult:
        results: list = field(default_factory=list)
        candidate_count: int = 0
        dense_count: int = 0
        bm25_count: int = 0
        degrade_level: int = 0

        def summary(self):
            return {"total_ms": 1.0, "tier1_ms": 0.5, "tier2_ms": 0.5, "tier3_ms": 0.0}

    class _MockPipeline:
        def search(self, query_text: str, top_k: int = 10):
            return _MockPipelineResult()

    class _MockDB:
        def find_matching_models(self, criteria):
            return set()

        def get_by_model(self, car_model: str):
            return {"car_model": car_model, "brand": "BYD"}

    rag = RAGService(pipeline=_MockPipeline(), db=_MockDB())
    ServiceContainer.reset()
    ServiceContainer.register_rag_service(rag)
    resolved = ServiceContainer.get_rag_service()
    assert resolved is rag

    resp = resolved.search_vehicles(RAGQueryRequest(query_text="测试混动SUV", top_k=3))
    assert isinstance(resp, RAGQueryResponse)
    assert resp.total_count == 0

    detail = resolved.get_vehicle_detail("比亚迪宋PLUS")
    assert detail["brand"] == "BYD"


def test_single_turn_extraction_signal_isolation(monkeypatch):
    """Verify _extract_information inspects latest_user_message instead of full history."""
    from llama_index.core.llms import MockLLM

    from src.agent.sales_agent import SalesAgent
    from src.agent.schemas import Stage

    agent = SalesAgent(llm=MockLLM(max_tokens=100))
    state = SessionState(stage=Stage.CAR_SELECTION)
    state.profile.name = "张三"

    profile_calls = []
    reservation_calls = []

    monkeypatch.setattr(
        "src.agent.sales_agent.extract_profile",
        lambda llm, text, existing: profile_calls.append(text) or existing,
    )
    monkeypatch.setattr(
        "src.agent.sales_agent.extract_combined_needs",
        lambda llm, text, profile, existing: existing,
    )
    monkeypatch.setattr(
        "src.agent.sales_agent.extract_reservation",
        lambda llm, text, existing: reservation_calls.append(text) or existing,
    )

    # Full history contains profile and reservation signals, but latest_user_message has neither
    history_text = "user: 我叫张三，家里3口人，预算20万，周末下午3点去4S店试驾\nassistant: 好的"
    agent._extract_information(state, history_text, latest_user_message="哈哈好的谢谢")
    assert len(profile_calls) == 0
    assert len(reservation_calls) == 0


def test_tiered_engine_singleton_reuses_cache_and_db():
    """Verify TieredRetrievalEngine reuses shared SemanticQueryCache and VehicleDB."""
    from src.retrieval.tiered_engine import TieredRetrievalEngine

    e1 = TieredRetrievalEngine.get_instance()
    e2 = TieredRetrievalEngine.get_instance()
    assert e1 is e2
    assert e1.cache is e2.cache
    assert e1.db is e2.db

