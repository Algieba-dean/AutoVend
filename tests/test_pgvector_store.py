"""
Unit tests for PostgreSQL + pgvector vector store (src/rag/pgvector_store.py)
and vector store factory/configuration.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.models.vehicle import AmbiguousLabels, PreciseLabels, Vehicle
from src.rag.pgvector_store import PgVectorStore, _build_sql_where, _validate_identifier
from src.rag.vector_store import ChromaVectorStore, create_vector_store
from src.utils.config import Config


def _make_vehicle(model: str, brand: str = "Tesla", price: str = "25万") -> Vehicle:
    return Vehicle(
        car_model=model,
        precise_labels=PreciseLabels(
            brand=brand,
            price=price,
            vehicle_category_bottom="SUV",
            powertrain_type="EV",
        ),
        ambiguous_labels=AmbiguousLabels(
            size="Mid-Size",
            family_friendliness="High",
            comfort_level="High",
        ),
    )


class TestPgVectorFallbackMode:
    """Tests exercising PgVectorStore in deterministic in-memory fallback mode."""

    def test_upsert_query_and_filter_in_fallback(self):
        store = PgVectorStore(
            dsn="postgresql://invalid:invalid@127.0.0.1:1/nonexistent",
            table_name="test_vehicles",
            embed_dim=4,
            allow_memory_fallback=True,
        )
        assert store.is_fallback is True
        assert store.backend_mode == "memory_fallback"
        assert store.count() == 0
        assert store.collection.count() == 0

        store.upsert_document(
            doc_id="veh_1",
            text="Tesla Model Y electric SUV",
            metadata={"car_model": "Model Y", "brand": "Tesla", "price_min": 240000},
            embedding=[1.0, 0.0, 0.0, 0.0],
        )
        store.upsert_document(
            doc_id="veh_2",
            text="BYD Han electric sedan",
            metadata={"car_model": "Han EV", "brand": "BYD", "price_min": 200000},
            embedding=[0.0, 1.0, 0.0, 0.0],
        )
        assert store.count() == 2

        # Cosine similarity query
        res = store.query(query_embeddings=[[1.0, 0.0, 0.0, 0.0]], n_results=2)
        assert res["ids"][0][0] == "veh_1"
        assert res["distances"][0][0] == pytest.approx(0.0, abs=1e-6)
        assert res["distances"][0][1] == pytest.approx(1.0, abs=1e-6)

        # $in candidate filter (VehicleRetriever contract)
        filtered = store.query(
            query_embeddings=[[1.0, 0.0, 0.0, 0.0]],
            n_results=5,
            where={"car_model": {"$in": ["Han EV"]}},
        )
        assert filtered["ids"][0] == ["veh_2"]

        # get_vehicle_by_id & peek
        fetched = store.get_vehicle_by_id("veh_1")
        assert fetched is not None
        assert fetched["metadata"]["brand"] == "Tesla"
        peeked = store.collection.peek(limit=1)
        assert len(peeked["ids"]) == 1

    def test_add_update_delete_backup_and_clear(self, tmp_path):
        store = PgVectorStore(
            dsn="postgresql://invalid:invalid@127.0.0.1:1/nonexistent",
            table_name="test_vehicles_crud",
            embed_dim=4,
            allow_memory_fallback=True,
        )
        v1 = _make_vehicle("Model 3", brand="Tesla", price="23万")
        v2 = _make_vehicle("Tang DM-i", brand="BYD", price="21万")

        store.add_vehicles([v1, v2], [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]])
        assert store.count() == 2

        meta_hits = store.query_by_metadata({"brand": "BYD"})
        assert len(meta_hits["ids"]) == 1
        assert meta_hits["metadatas"][0]["car_model"] == "Tang DM-i"

        # Backup to JSONL
        backup_file = tmp_path / "pg_backup.jsonl"
        out_path = store.backup_collection(backup_file)
        assert out_path.exists()
        lines = out_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

        # Delete by car_model
        store.delete_document("Model 3")
        assert store.count() == 1

        # Clear
        store.clear_collection()
        assert store.count() == 0

        info = store.get_collection_info()
        assert info["backend"] == "pgvector"
        assert info["is_fallback"] is True


class TestPgVectorPostgresMocked:
    """Tests verifying SQL generation and execution against a mocked psycopg connection."""

    def _make_mock_conn(self, fetchone_val=(0,), fetchall_val=None):
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.return_value = fetchone_val
        cur.fetchall.return_value = fetchall_val or []
        ctx = MagicMock()
        ctx.__enter__.return_value = cur
        ctx.__exit__.return_value = False
        conn.cursor.return_value = ctx
        return conn, cur

    def test_schema_creation_and_sql_operations(self):
        conn, cur = self._make_mock_conn(fetchone_val=(1,))
        store = PgVectorStore(
            table_name="vehicle_knowledge",
            embed_dim=4,
            connection=conn,
            allow_memory_fallback=False,
        )
        assert store.is_fallback is False
        assert store.backend_mode == "postgres"

        executed_sql = "\n".join(str(call.args[0]) for call in cur.execute.call_args_list)
        assert "CREATE EXTENSION IF NOT EXISTS vector" in executed_sql
        assert "CREATE TABLE IF NOT EXISTS vehicle_knowledge" in executed_sql
        assert "USING hnsw" in executed_sql
        assert "vector_cosine_ops" in executed_sql
        assert "USING gin (metadata)" in executed_sql

        # Upsert (no trailing SELECT COUNT(*))
        store.upsert_document(
            doc_id="veh_abc",
            text="Model Y",
            metadata={"car_model": "Model Y", "brand": "Tesla"},
            embedding=[0.1, 0.2, 0.3, 0.4],
        )
        last_sql, last_params = cur.execute.call_args_list[-1].args
        assert "ON CONFLICT (id) DO UPDATE SET" in last_sql
        assert last_params[0] == "veh_abc"
        assert json.loads(last_params[2])["car_model"] == "Model Y"

        # Batch upsert via executemany
        v1 = _make_vehicle("Model 3", brand="Tesla", price="23万")
        v2 = _make_vehicle("Model Y", brand="Tesla", price="25万")
        store.add_vehicles([v1, v2], [[0.1, 0.2, 0.3, 0.4], [0.2, 0.3, 0.4, 0.5]])
        assert cur.executemany.called
        batch_sql, batch_params = cur.executemany.call_args.args
        assert "ON CONFLICT (id) DO UPDATE SET" in batch_sql
        assert len(batch_params) == 2

        # Query with $in filter
        cur.fetchall.return_value = [
            ("veh_abc", {"car_model": "Model Y", "brand": "Tesla"}, "Model Y", 0.05)
        ]
        res = store.query(
            query_embeddings=[[0.1, 0.2, 0.3, 0.4]],
            n_results=3,
            where={"car_model": {"$in": ["Model Y"]}},
            include=["metadatas", "documents", "distances"],
        )
        assert res["ids"] == [["veh_abc"]]
        assert res["distances"] == [[0.05]]

        # Delete & Clear
        store.delete_document("veh_abc")
        store.clear_collection()
        all_sql = "\n".join(str(call.args[0]) for call in cur.execute.call_args_list)
        assert "DELETE FROM vehicle_knowledge" in all_sql
        assert "TRUNCATE TABLE vehicle_knowledge" in all_sql

    def test_sql_identifier_validation_blocks_injection(self):
        with pytest.raises(ValueError):
            _validate_identifier("vehicle_knowledge; DROP TABLE users;--")

        where_sql, params = _build_sql_where(
            {"$and": [{"car_model": {"$in": ["Model 3", "Model Y"]}}, {"price_min": {"$gte": 20}}]}
        )
        assert "metadata->>'car_model' = ANY(%s::text[])" in where_sql
        assert "metadata->>'price_min' ~ '^-?[0-9]+(\\.[0-9]+)?$'" in where_sql
        assert "(metadata->>'price_min')::double precision >= %s" in where_sql
        assert params == [["Model 3", "Model Y"], 20.0]

        eq_sql, eq_params = _build_sql_where({"brand": "BYD"})
        assert eq_sql == "metadata @> %s::jsonb"
        assert json.loads(eq_params[0]) == {"brand": "BYD"}

        empty_in_sql, empty_in_params = _build_sql_where({"brand": {"$in": []}})
        assert empty_in_sql == "FALSE"
        assert empty_in_params == []

        nin_sql, nin_params = _build_sql_where({"brand": {"$nin": ["BYD"]}})
        assert "IS NULL OR NOT" in nin_sql
        assert "ANY(%s::text[])" in nin_sql
        assert nin_params == [["BYD"]]

    def test_schema_failure_closes_opened_pool_and_falls_back(self):
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = RuntimeError("extension vector not available")
        mock_pool = MagicMock()
        pool_ctx = MagicMock()
        pool_ctx.__enter__.return_value = mock_conn
        pool_ctx.__exit__.return_value = False
        mock_pool.connection.return_value = pool_ctx

        with patch("psycopg_pool.ConnectionPool", return_value=mock_pool):
            store = PgVectorStore(
                dsn="postgresql://user:pw@localhost:5432/autovend",
                table_name="vehicle_knowledge",
                embed_dim=4,
                allow_memory_fallback=True,
            )

        assert store.is_fallback is True
        mock_pool.close.assert_called_once()

    def test_fail_fast_when_memory_fallback_disabled_and_zero_vector_disabled(self):
        with pytest.raises(Exception):
            PgVectorStore(
                dsn="postgresql://invalid:invalid@127.0.0.1:1/nonexistent",
                table_name="vehicle_knowledge",
                embed_dim=4,
                allow_memory_fallback=False,
            )

        conn, _ = self._make_mock_conn(fetchone_val=(0,))
        degraded_emb = MagicMock()
        degraded_emb.is_degraded = True
        store = PgVectorStore(
            table_name="vehicle_knowledge",
            embed_dim=4,
            connection=conn,
            embedding_model=degraded_emb,
            allow_memory_fallback=False,
            allow_zero_vector_fallback=False,
        )
        with patch("src.rag.embeddings.BGEEmbeddingModel", side_effect=RuntimeError("no model")):
            with pytest.raises(ValueError, match="zero-vector fallback disabled"):
                store.upsert_document(doc_id="veh_no_emb", text="No embedding")


class TestVectorStoreFactoryAndConfig:
    """Tests for create_vector_store factory and Config pgvector settings."""

    def test_config_pgvector_connection_string(self):
        cfg = Config(
            pgvector_host="db.internal",
            pgvector_port=5433,
            pgvector_user="av",
            pgvector_password="secret",
            pgvector_database="av_db",
        )
        assert cfg.vector_store_backend == "pgvector"
        assert cfg.pgvector_connection_string == "postgresql://av:secret@db.internal:5433/av_db"

        cfg_dsn = Config(pgvector_dsn="postgresql://custom:pw@pg:5432/prod")
        assert cfg_dsn.pgvector_connection_string == "postgresql://custom:pw@pg:5432/prod"

    def test_factory_selects_pgvector_by_default_and_chroma_on_override(self, tmp_path):
        pg_store = create_vector_store(
            dsn="postgresql://invalid:invalid@127.0.0.1:1/nonexistent",
            allow_memory_fallback=True,
        )
        assert isinstance(pg_store, PgVectorStore)

        chroma_store = create_vector_store(
            backend="chroma",
            persist_directory=str(tmp_path / "chroma_test"),
            collection_name="test_col",
        )
        assert isinstance(chroma_store, ChromaVectorStore)

        with pytest.raises(ValueError):
            create_vector_store(backend="unknown_db")

    def test_cli_status_command_uses_create_vector_store(self):
        from src.main import status_command

        mock_store = MagicMock()
        mock_store.get_collection_info.return_value = {
            "backend": "pgvector",
            "mode": "memory_fallback",
            "name": "vehicle_knowledge",
            "count": 0,
            "distance_metric": "cosine",
            "embed_dim": 1024,
        }
        with (
            patch("src.main.create_vector_store", return_value=mock_store) as mock_factory,
            patch("src.main.BGEEmbeddingModel", side_effect=RuntimeError("skip model load")),
        ):
            status_command(SimpleNamespace())

        mock_factory.assert_called_once_with()
        mock_store.get_collection_info.assert_called_once_with()
