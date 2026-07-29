"""
Unit tests for Incremental Ingestion & Index Pipeline (src/ingestion/pipeline.py).
"""

from src.ingestion.pipeline import ChangeType, IncrementalIngestionPipeline


def test_incremental_ingestion_detect_changes():
    """Test detecting created, updated, and deleted vehicle records."""
    pipeline = IncrementalIngestionPipeline()
    for m in ["Test_Model_A", "Test_Model_B", "Test_Model_C"]:
        pipeline.db.delete_vehicle(m)
        pipeline.checksum_store.pop(m, None)

    v1 = {"car_model": "Test_Model_A", "brand": "TestBrand", "prize": "20万"}
    v2 = {"car_model": "Test_Model_B", "brand": "TestBrand", "prize": "30万"}

    # 1. First batch: Created
    summary1 = pipeline.ingest_batch([v1, v2])
    assert summary1.created_count == 2
    assert summary1.updated_count == 0

    # 2. Second batch: Update Model A price, keep Model B, add Model C, remove Model B (not in list)
    v1_updated = {"car_model": "Test_Model_A", "brand": "TestBrand", "prize": "18万"}
    v3 = {"car_model": "Test_Model_C", "brand": "TestBrand", "prize": "50万"}

    patches = pipeline.detect_changes([v1_updated, v3])
    change_map = {p.car_model: p.change_type for p in patches}

    assert change_map["Test_Model_A"] == ChangeType.UPDATED
    assert change_map["Test_Model_C"] == ChangeType.CREATED
    assert change_map["Test_Model_B"] == ChangeType.DELETED

    # Execute batch
    summary2 = pipeline.ingest_batch([v1_updated, v3])
    assert summary2.created_count == 1
    assert summary2.updated_count == 1
    assert summary2.deleted_count == 1
