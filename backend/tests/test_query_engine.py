"""
Tests for the hybrid retrieval query engine.
"""

from unittest.mock import MagicMock

from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.vector_stores import (
    FilterCondition,
    FilterOperator,
)

from app.rag.query_engine import (
    FILTERABLE_FIELDS,
    _build_metadata_filters,
    build_query_engine,
    format_retrieval_results,
    retrieve_vehicles,
)


class TestBuildMetadataFilters:
    """Tests for _build_metadata_filters."""

    def test_single_filter(self):
        filters = _build_metadata_filters({"brand": "Tesla"})
        assert filters is not None
        assert len(filters.filters) == 1
        assert filters.filters[0].key == "brand"
        assert filters.filters[0].value == "Tesla"
        assert filters.filters[0].operator == FilterOperator.EQ

    def test_multiple_filters(self):
        filters = _build_metadata_filters(
            {
                "brand": "Tesla",
                "prize": "40,000~60,000",
                "powertrain_type": "Battery Electric Vehicle",
            }
        )
        assert filters is not None
        assert len(filters.filters) == 3
        assert filters.condition == FilterCondition.AND

    def test_ignores_unknown_fields(self):
        filters = _build_metadata_filters(
            {
                "brand": "Tesla",
                "unknown_field": "value",
                "another_unknown": "xyz",
            }
        )
        assert filters is not None
        assert len(filters.filters) == 1
        assert filters.filters[0].key == "brand"

    def test_ignores_empty_values(self):
        filters = _build_metadata_filters(
            {
                "brand": "",
                "prize": "10,000~20,000",
            }
        )
        assert filters is not None
        assert len(filters.filters) == 1
        assert filters.filters[0].key == "prize"

    def test_returns_none_for_empty_input(self):
        assert _build_metadata_filters({}) is None

    def test_returns_none_for_all_invalid(self):
        assert _build_metadata_filters({"unknown": "value"}) is None
        assert _build_metadata_filters({"brand": ""}) is None

    def test_all_filterable_fields_accepted(self):
        filters_dict = {field: "test_value" for field in FILTERABLE_FIELDS}
        filters = _build_metadata_filters(filters_dict)
        assert filters is not None
        assert len(filters.filters) == len(FILTERABLE_FIELDS)


class TestBuildQueryEngine:
    """Tests for build_query_engine."""

    def test_returns_retriever(self):
        mock_index = MagicMock()
        mock_retriever = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever

        retriever = build_query_engine(mock_index, similarity_top_k=3)
        assert retriever == mock_retriever
        mock_index.as_retriever.assert_called_once()

    def test_passes_top_k(self):
        mock_index = MagicMock()
        build_query_engine(mock_index, similarity_top_k=10)
        call_kwargs = mock_index.as_retriever.call_args[1]
        assert call_kwargs["similarity_top_k"] == 10

    def test_passes_metadata_filters(self):
        mock_index = MagicMock()
        build_query_engine(
            mock_index,
            metadata_filters={"brand": "Tesla"},
        )
        call_kwargs = mock_index.as_retriever.call_args[1]
        assert call_kwargs["filters"] is not None
        assert len(call_kwargs["filters"].filters) == 1

    def test_no_filters_when_none(self):
        mock_index = MagicMock()
        build_query_engine(mock_index)
        call_kwargs = mock_index.as_retriever.call_args[1]
        assert call_kwargs["filters"] is None


def _make_node(car_model: str, score: float, text: str = "", **meta) -> NodeWithScore:
    """Helper to create a NodeWithScore."""
    metadata = {"car_model": car_model, **meta}
    node = TextNode(text=text, metadata=metadata)
    return NodeWithScore(node=node, score=score)


class TestRetrieveVehicles:
    """Tests for retrieve_vehicles."""

    def test_returns_results(self):
        mock_index = MagicMock()
        mock_retriever = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever
        mock_retriever.retrieve.return_value = [
            _make_node("Tesla-Model Y", 0.95, "Electric SUV"),
            _make_node("BYD-Seal", 0.88, "Electric Sedan"),
        ]

        results = retrieve_vehicles(mock_index, "electric SUV for family")
        assert len(results) == 2
        assert results[0].score == 0.95

    def test_passes_filters(self):
        mock_index = MagicMock()
        mock_retriever = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever
        mock_retriever.retrieve.return_value = []

        retrieve_vehicles(
            mock_index,
            "SUV",
            metadata_filters={"brand": "Tesla"},
            top_k=3,
        )
        call_kwargs = mock_index.as_retriever.call_args[1]
        assert call_kwargs["similarity_top_k"] == 3
        assert call_kwargs["filters"] is not None

    def test_empty_results(self):
        mock_index = MagicMock()
        mock_retriever = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever
        mock_retriever.retrieve.return_value = []

        results = retrieve_vehicles(mock_index, "nonexistent vehicle type")
        assert len(results) == 0


class TestFormatRetrievalResults:
    """Tests for format_retrieval_results."""

    def test_formats_correctly(self):
        results = [
            _make_node(
                "Tesla-Model Y",
                0.95,
                "The Tesla Model Y is an all-electric compact SUV.",
                brand="Tesla",
                prize="40,000~60,000",
                source_file="test.toml",
            ),
            _make_node("BYD-Seal", 0.88, "A sporty EV sedan.", brand="BYD"),
        ]

        formatted = format_retrieval_results(results)
        assert len(formatted) == 2

        first = formatted[0]
        assert first["car_model"] == "Tesla-Model Y"
        assert first["score"] == 0.95
        assert first["metadata"]["brand"] == "Tesla"
        assert first["metadata"]["prize"] == "40,000~60,000"
        assert "source_file" not in first["metadata"]
        assert "Tesla Model Y" in first["text_snippet"]

    def test_handles_none_score(self):
        results = [_make_node("Test-Car", None, "Some text")]
        # NodeWithScore requires score, but we handle None gracefully
        results[0].score = None
        formatted = format_retrieval_results(results)
        assert formatted[0]["score"] is None

    def test_truncates_long_text(self):
        long_text = "A" * 500
        results = [_make_node("Test-Car", 0.5, long_text)]
        formatted = format_retrieval_results(results)
        assert len(formatted[0]["text_snippet"]) == 300

    def test_empty_results(self):
        formatted = format_retrieval_results([])
        assert formatted == []

    def test_empty_text(self):
        node = TextNode(text="", metadata={"car_model": "Empty"})
        results = [NodeWithScore(node=node, score=0.1)]
        formatted = format_retrieval_results(results)
        assert formatted[0]["text_snippet"] == ""
