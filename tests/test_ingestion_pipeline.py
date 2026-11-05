"""
Unit tests for Incremental Ingestion & Index Pipeline (src/ingestion/pipeline.py).
Validates incremental CDC semantics, checksum persistence across restarts,
SAGA rollback compensation, and explicit vs full snapshot deletion.
"""

from unittest.mock import MagicMock
from src.filter.vehicle_db import VehicleDB
from src.ingestion.pipeline import ChangeType, IncrementalIngestionPipeline


def test_incremental_ingestion_delta_batch_preserves_omitted_models(tmp_path):
    """
    Incremental batch must NOT treat omitted models as deleted.
    Only explicit is_deleted=True or full_sync=True triggers deletion.
    """
    test_db = VehicleDB(db_path=str(tmp_path / "test_vehicles.db"))
    pipeline = IncrementalIngestionPipeline(db=test_db)

    v1 = {"car_model": "Test_Model_A", "brand": "TestBrand", "prize": "20万"}
    v2 = {"car_model": "Test_Model_B", "brand": "TestBrand", "prize": "30万"}

    # 1. First batch: Created
    summary1 = pipeline.ingest_batch([v1, v2])
    assert summary1.created_count == 2
    assert summary1.updated_count == 0

    # 2. Incremental batch: Update Model A, omit Model B, add Model C
    v1_updated = {"car_model": "Test_Model_A", "brand": "TestBrand", "prize": "18万"}
    v3 = {"car_model": "Test_Model_C", "brand": "TestBrand", "prize": "50万"}

    patches = pipeline.detect_changes([v1_updated, v3], full_sync=False)
    change_map = {p.car_model: p.change_type for p in patches}

    assert change_map["Test_Model_A"] == ChangeType.UPDATED
    assert change_map["Test_Model_C"] == ChangeType.CREATED
    # Model B must NOT be marked DELETED in incremental sync
    assert "Test_Model_B" not in change_map

    # Execute incremental batch
    summary2 = pipeline.ingest_batch([v1_updated, v3], full_sync=False)
    assert summary2.created_count == 1
    assert summary2.updated_count == 1
    assert summary2.deleted_count == 0
    # Model B is still in SQLite
    assert test_db.get_by_model("Test_Model_B") is not None


def test_explicit_deletion_and_full_sync_reconciliation(tmp_path):
    """Test explicit deletion flag and full_sync snapshot reconciliation."""
    test_db = VehicleDB(db_path=str(tmp_path / "test_vehicles_sync.db"))
    pipeline = IncrementalIngestionPipeline(db=test_db)

    v1 = {"car_model": "Model_X", "brand": "BrandX", "prize": "20万"}
    v2 = {"car_model": "Model_Y", "brand": "BrandY", "prize": "30万"}
    pipeline.ingest_batch([v1, v2])

    # Explicit deletion patch
    del_patch = pipeline.detect_changes([{"car_model": "Model_X", "is_deleted": True}])
    assert len(del_patch) == 1
    assert del_patch[0].change_type == ChangeType.DELETED

    # Full sync mode: omitting Model X marks it DELETED
    full_patches = pipeline.detect_changes([v2], full_sync=True)
    full_change_map = {p.car_model: p.change_type for p in full_patches}
    assert full_change_map["Model_X"] == ChangeType.DELETED
    assert full_change_map["Model_Y"] == ChangeType.UNCHANGED

    # Ingest with full_sync=True removes Model_X from DB
    summary_full = pipeline.ingest_batch([v2], full_sync=True)
    assert summary_full.deleted_count == 1
    assert test_db.get_by_model("Model_X") is None


def test_checksum_persistence_across_pipeline_restarts(tmp_path):
    """Test that checksums persist in SQLite across pipeline instances (simulating Pod restart)."""
    db_path = str(tmp_path / "persistent_checksums.db")
    db1 = VehicleDB(db_path=db_path)
    pipeline1 = IncrementalIngestionPipeline(db=db1)

    v1 = {"car_model": "Model_Z", "brand": "BrandZ", "prize": "25万"}
    pipeline1.ingest_batch([v1])

    assert "Model_Z" in pipeline1.checksum_store
    saved_checksum = pipeline1.checksum_store["Model_Z"]

    # Restart: instantiate a new pipeline on the same SQLite file
    db2 = VehicleDB(db_path=db_path)
    pipeline2 = IncrementalIngestionPipeline(db=db2)

    assert "Model_Z" in pipeline2.checksum_store
    assert pipeline2.checksum_store["Model_Z"] == saved_checksum

    # Re-ingesting the identical record should detect UNCHANGED
    patches = pipeline2.detect_changes([v1])
    assert patches[0].change_type == ChangeType.UNCHANGED


def test_saga_rollback_and_dlq_on_downstream_failure(tmp_path):
    """
    Test SAGA compensation: if vector store or downstream fails, SQLite is rolled back,
    error is logged to DLQ / outbox, and persistent checksum is NOT advanced.
    """
    test_db = VehicleDB(db_path=str(tmp_path / "saga_test.db"))

    # Mock hybrid pipeline with vector_store that fails
    mock_vs = MagicMock()
    mock_vs.upsert_document.side_effect = ConnectionError("ChromaDB connection refused")
    mock_retriever = MagicMock()
    mock_retriever.vector_store = mock_vs
    mock_hybrid = MagicMock()
    mock_hybrid.retriever = mock_retriever

    pipeline = IncrementalIngestionPipeline(db=test_db, hybrid_pipeline=mock_hybrid)

    v_new = {"car_model": "Model_Fail", "brand": "FailBrand", "prize": "100万"}

    # Attempt ingestion
    summary = pipeline.ingest_batch([v_new])
    assert summary.created_count == 0  # Rolled back
    assert test_db.get_by_model("Model_Fail") is None  # SQLite was rolled back

    # DLQ captured the failure
    assert len(pipeline.dlq) == 1
    assert pipeline.dlq[0]["car_model"] == "Model_Fail"
    assert "ChromaDB connection refused" in pipeline.dlq[0]["error"]

    # Checksum was NOT advanced
    assert "Model_Fail" not in pipeline.checksum_store
