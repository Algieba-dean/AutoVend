"""
Tests for the ChromaDB vector index builder.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import toml
from llama_index.core.schema import Document

from app.ingestion.index_builder import (
    build_index,
    build_vehicle_index,
    get_chroma_client,
    get_chroma_vector_store,
)
from app.rag.vehicle_index import get_vehicle_index, reset_vehicle_index


def _write_toml(dir_path: Path, filename: str, data: dict) -> Path:
    """Helper to write a TOML file."""
    file_path = dir_path / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        toml.dump(data, f)
    return file_path


SAMPLE_VEHICLE = {
    "title": "CarLabels",
    "car_model": "TestBrand-TestModel A",
    "PriciseLabels": {
        "brand": "TestBrand",
        "prize": "10,000~20,000",
        "powertrain_type": "Battery Electric Vehicle",
    },
    "AmbiguousLabels": {"size": "Medium"},
    "KeyDetails": {
        "key_details": "A compact electric vehicle for testing.",
        "key_details_comments": "Designed for unit test scenarios.",
    },
}

SAMPLE_VEHICLE_B = {
    "title": "CarLabels",
    "car_model": "OtherBrand-Model B",
    "PriciseLabels": {
        "brand": "OtherBrand",
        "prize": "40,000~60,000",
        "powertrain_type": "Gasoline Engine",
    },
    "AmbiguousLabels": {"size": "Large"},
    "KeyDetails": {
        "key_details": "A large gasoline SUV.",
    },
}


class TestGetChromaClient:
    """Tests for get_chroma_client."""

    def test_creates_persistent_client(self, tmp_path):
        persist_dir = str(tmp_path / "chroma_test")
        client = get_chroma_client(persist_dir)
        assert client is not None
        assert Path(persist_dir).exists()

    def test_creates_directory_if_missing(self, tmp_path):
        persist_dir = str(tmp_path / "nested" / "chroma")
        client = get_chroma_client(persist_dir)
        assert client is not None
        assert Path(persist_dir).exists()


class TestGetChromaVectorStore:
    """Tests for get_chroma_vector_store."""

    def test_creates_vector_store(self, tmp_path):
        client = get_chroma_client(str(tmp_path / "chroma"))
        store = get_chroma_vector_store(client, "test_collection")
        assert store is not None

    def test_get_or_create_collection(self, tmp_path):
        client = get_chroma_client(str(tmp_path / "chroma"))
        store1 = get_chroma_vector_store(client, "test_col")
        store2 = get_chroma_vector_store(client, "test_col")
        # Both should reference the same collection
        assert store1._collection.name == store2._collection.name


class TestBuildIndex:
    """Tests for build_index with mock embedding to avoid downloading models."""

    def test_build_from_documents(self, tmp_path):
        from llama_index.core.embeddings.mock_embed_model import MockEmbedding

        mock_embed = MockEmbedding(embed_dim=384)

        docs = [
            Document(text="Test vehicle A", metadata={"brand": "A"}),
            Document(text="Test vehicle B", metadata={"brand": "B"}),
        ]

        client = get_chroma_client(str(tmp_path / "chroma"))
        store = get_chroma_vector_store(client, "test_build")

        index = build_index(docs, mock_embed, store)
        assert index is not None


class TestBuildVehicleIndex:
    """Tests for the end-to-end build_vehicle_index function."""

    def test_raises_on_empty_dir(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(ValueError, match="No vehicle documents parsed"):
            build_vehicle_index(
                vehicle_data_dir=str(empty_dir),
                persist_dir=str(tmp_path / "chroma"),
                embedding_model_name="BAAI/bge-m3",
            )

    def test_raises_on_nonexistent_dir(self, tmp_path):
        with pytest.raises(ValueError, match="No vehicle documents parsed"):
            build_vehicle_index(
                vehicle_data_dir="/nonexistent/path",
                persist_dir=str(tmp_path / "chroma"),
            )


class TestVehicleIndexManager:
    """Tests for vehicle_index.py get/reset functions."""

    def setup_method(self):
        reset_vehicle_index()

    def test_reset_clears_cache(self):
        reset_vehicle_index()
        # After reset, the module-level cache should be None
        from app.rag.vehicle_index import _vehicle_index

        assert _vehicle_index is None

    def test_get_raises_on_empty_collection(self, tmp_path):
        """Should raise RuntimeError if collection is empty."""
        with patch("app.rag.vehicle_index.get_chroma_client") as mock_client_fn:
            mock_collection = MagicMock()
            mock_collection.count.return_value = 0
            mock_collection.name = "test"

            mock_client = MagicMock()
            mock_client_fn.return_value = mock_client

            with patch("app.rag.vehicle_index.get_chroma_vector_store") as mock_store_fn:
                mock_store = MagicMock()
                mock_store._collection = mock_collection
                mock_store_fn.return_value = mock_store

                with pytest.raises(RuntimeError, match="empty"):
                    get_vehicle_index()
