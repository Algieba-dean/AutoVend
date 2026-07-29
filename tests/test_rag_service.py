"""
Unit tests for Standalone RAG Service (src/rag_service).
"""

from src.rag_service.schemas import SpecCompareRequest, VehicleQueryRequest
from src.rag_service.service import RAGService


def test_rag_service_search_vehicles():
    """Test vehicle retrieval through RAGService."""
    service = RAGService()
    req = VehicleQueryRequest(
        query_text="中型纯电SUV 20万左右",
        explicit_needs={
            "vehicle_category_bottom": "中型SUV",
            "powertrain_type": "纯电动",
            "prize": "20万",
        },
        implicit_needs={"comfort_level": "高", "space": "大"},
        top_k=3,
        enable_rerank=True,
    )
    res = service.search_vehicles(req)

    assert res is not None
    assert isinstance(res.results, list)
    assert res.total_time_ms >= 0.0
    if res.results:
        first = res.results[0]
        assert first.car_model != ""
        assert first.score > 0.0


def test_rag_service_compare_vehicles():
    """Test side-by-side spec comparison matrix."""
    service = RAGService()
    req = SpecCompareRequest(car_models=["蔚来-ES6", "特斯拉-Model Y"])
    res = service.compare_vehicles(req)

    assert res.car_models == ["蔚来-ES6", "特斯拉-Model Y"]
    assert len(res.diff_matrix) > 0
    assert "vs" in res.comparison_summary

    # Verify rows in diff matrix
    feature_names = [row.feature_name for row in res.diff_matrix]
    assert "官方指导价" in feature_names or "级别/类型" in feature_names


def test_rag_service_get_vehicle_detail():
    """Test getting single vehicle detail."""
    service = RAGService()
    # Test query for a model or non-existing model
    detail = service.get_vehicle_detail("NonExistentCarModel_123")
    assert detail is None or isinstance(detail, dict)
