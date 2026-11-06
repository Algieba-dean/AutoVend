"""
Unit tests for Incremental Ingestion & Index Pipeline (src/ingestion/pipeline.py).
Validates incremental CDC semantics, checksum persistence across restarts,
SAGA rollback compensation, and explicit vs full snapshot deletion.
"""

from unittest.mock import MagicMock
import pytest
from src.filter.vehicle_db import VehicleDB
from src.ingestion.pipeline import ChangeType, IncrementalIngestionPipeline
from src.rag.vector_store import ChromaVectorStore, generate_vehicle_doc_id


def test_incremental_ingestion_delta_batch_preserves_omitted_models(tmp_path):
    """
    Incremental batch must NOT treat omitted models as deleted.
    Only explicit is_deleted=True or full_sync=True triggers deletion.
    """
    test_db = VehicleDB(db_path=str(tmp_path / "test_vehicles.db"))
    pipeline = IncrementalIngestionPipeline(db=test_db)

    v1 = {"car_model": "Test_Model_A", "brand": "TestBrand", "price": "20万"}
    v2 = {"car_model": "Test_Model_B", "brand": "TestBrand", "price": "30万"}

    # 1. First batch: Created
    summary1 = pipeline.ingest_batch([v1, v2])
    assert summary1.created_count == 2
    assert summary1.updated_count == 0

    # 2. Incremental batch: Update Model A, omit Model B, add Model C
    v1_updated = {"car_model": "Test_Model_A", "brand": "TestBrand", "price": "18万"}
    v3 = {"car_model": "Test_Model_C", "brand": "TestBrand", "price": "50万"}

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

    v1 = {"car_model": "Model_X", "brand": "BrandX", "price": "20万"}
    v2 = {"car_model": "Model_Y", "brand": "BrandY", "price": "30万"}
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

    v1 = {"car_model": "Model_Z", "brand": "BrandZ", "price": "25万"}
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

    # Mock hybrid pipeline with vector_store conforming to real ChromaVectorStore contract that fails
    mock_vs = MagicMock(spec=ChromaVectorStore)
    mock_vs.upsert_document.side_effect = ConnectionError("ChromaDB connection refused")
    mock_retriever = MagicMock()
    mock_retriever.vector_store = mock_vs
    mock_hybrid = MagicMock()
    mock_hybrid.retriever = mock_retriever

    pipeline = IncrementalIngestionPipeline(db=test_db, hybrid_pipeline=mock_hybrid)

    v_new = {"car_model": "Model_Fail", "brand": "FailBrand", "price": "100万"}

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


def test_change_type_string_and_enum_variations(tmp_path):
    """Verify string 'DELETED', 'deleted', and ChangeType.DELETED all trigger explicit deletion."""
    test_db = VehicleDB(db_path=str(tmp_path / "test_del_variants.db"))
    pipeline = IncrementalIngestionPipeline(db=test_db)

    pipeline.ingest_batch([
        {"car_model": "Model_1", "brand": "B1", "price": "10万"},
        {"car_model": "Model_2", "brand": "B2", "price": "20万"},
    ])

    # Pass uppercase 'DELETED'
    patches = pipeline.detect_changes([{"car_model": "Model_1", "change_type": "DELETED"}])
    assert len(patches) == 1
    assert patches[0].car_model == "Model_1"
    assert patches[0].change_type == ChangeType.DELETED

    # Execute batch and verify Model_2 remains untouched
    summary = pipeline.ingest_batch([{"car_model": "Model_1", "change_type": "DELETED"}])
    assert summary.deleted_count == 1
    assert test_db.get_by_model("Model_1") is None
    assert test_db.get_by_model("Model_2") is not None


def test_saga_rollback_restores_preexisting_record(tmp_path):
    """
    Verify SAGA rollback restores the previous SQLite record when an update fails downstream,
    rather than deleting the record.
    """
    test_db = VehicleDB(db_path=str(tmp_path / "saga_restore.db"))
    pipeline = IncrementalIngestionPipeline(db=test_db)

    original = {"car_model": "Model_Preserve", "brand": "OriginalBrand", "price": "30万"}
    pipeline.ingest_batch([original])

    # Set up failing vector store conforming to real ChromaVectorStore contract
    mock_vs = MagicMock(spec=ChromaVectorStore)
    mock_vs.upsert_document.side_effect = TimeoutError("ChromaDB timeout")
    mock_retriever = MagicMock()
    mock_retriever.vector_store = mock_vs
    mock_hybrid = MagicMock()
    mock_hybrid.retriever = mock_retriever
    pipeline.hybrid_pipeline = mock_hybrid

    # Attempt to update the vehicle
    updated = {"car_model": "Model_Preserve", "brand": "ChangedBrand", "price": "40万"}
    summary = pipeline.ingest_batch([updated])

    assert summary.updated_count == 0
    # SQLite must retain original data
    stored = test_db.get_by_model("Model_Preserve")
    assert stored is not None
    assert stored.get("brand") == "originalbrand"


def test_file_and_doc_keys_ignored_in_full_sync_reconciliation(tmp_path):
    """Verify that file: and doc: checksum keys are not treated as vehicle models in full_sync."""
    test_db = VehicleDB(db_path=str(tmp_path / "file_keys_sync.db"))
    pipeline = IncrementalIngestionPipeline(db=test_db)

    # Ingest a vehicle model
    pipeline.ingest_batch([{"car_model": "Real_Car", "brand": "CarBrand", "price": "15万"}])

    # Artificially insert a file and doc key into checksum store
    pipeline._set_checksum("file:somehash:manual.pdf", "hash123")
    pipeline._set_checksum("doc:tech_spec_su7", "dochash456")

    # Perform full_sync with only Real_Car
    patches = pipeline.detect_changes([{"car_model": "Real_Car", "brand": "CarBrand", "price": "15万"}], full_sync=True)

    # Real_Car is UNCHANGED, and neither file: nor doc: should be marked DELETED
    patch_models = [p.car_model for p in patches]
    assert patch_models == ["Real_Car"]
    assert patches[0].change_type == ChangeType.UNCHANGED


def test_table_block_handles_none_rows():
    """Verify TableBlock does not raise TypeError when rows is None."""
    from src.ingestion.layout_parser import TableBlock

    tbl = TableBlock(page_num=1, rows=None)
    assert tbl.row_count == 0
    assert tbl.col_count == 0
    assert tbl.headers == []
    assert tbl.body_rows == []


def test_vehicle_db_price_normalization_and_outbox(tmp_path):
    """Verify VehicleDB parses 'price' and supports outbox querying."""
    test_db = VehicleDB(db_path=str(tmp_path / "vdb_test.db"))

    # Test outbox recording and retrieval
    test_db.record_outbox_event(
        event_id="evt_001",
        event_type="test_sync",
        payload_json='{"test": 123}',
        status="FAILED",
        error_message="downstream unavailable",
    )
    events = test_db.get_outbox_events(status="FAILED")
    assert len(events) == 1
    assert events[0]["id"] == "evt_001"
    assert events[0]["error_message"] == "downstream unavailable"

    # Test price normalization in TOML rows
    toml_path = tmp_path / "model_p.toml"
    toml_path.write_text(
        'car_model = "Model_P"\n[PriciseLabels]\nprice = "100,000 ~ 200,000"\nbrand = "TestBrand"\n',
        encoding="utf-8",
    )
    row = test_db._parse_toml(str(toml_path))
    assert row is not None
    assert "price" in row
    assert row["price"] == "100,000 ~ 200,000"


def test_optimistic_locking_conflict_on_missing_or_concurrent_row(tmp_path):
    """Verify that expected_version conflict is raised when row was deleted or modified."""
    from src.filter.vehicle_db import OptimisticLockError

    test_db = VehicleDB(db_path=str(tmp_path / "opt_lock.db"))
    test_db.upsert_vehicle({"car_model": "ConflictCar", "brand": "BrandX", "version": 1})

    # Record exists at version 1; updating with expected_version=2 should fail
    with pytest.raises(OptimisticLockError):
        test_db.upsert_vehicle({"car_model": "ConflictCar", "brand": "BrandX"}, expected_version=2)

    # Deleting with expected_version=2 should fail
    with pytest.raises(OptimisticLockError):
        test_db.delete_vehicle("ConflictCar", expected_version=2)

    # Delete the car
    test_db.delete_vehicle("ConflictCar", expected_version=1)

    # Now row is deleted; updating with expected_version=1 must fail because row is missing
    with pytest.raises(OptimisticLockError):
        test_db.upsert_vehicle({"car_model": "ConflictCar", "brand": "BrandX"}, expected_version=1)

    # Deleting missing row with expected_version=1 must fail
    with pytest.raises(OptimisticLockError):
        test_db.delete_vehicle("ConflictCar", expected_version=1)


def test_concurrent_threads_optimistic_locking(tmp_path):
    """Stress test: 50 concurrent threads simultaneously updating the same vehicle record."""
    import concurrent.futures
    from src.filter.vehicle_db import OptimisticLockError

    test_db = VehicleDB(db_path=str(tmp_path / "concurrent_opt.db"))
    test_db.upsert_vehicle({"car_model": "RaceCar", "brand": "BrandR", "version": 1})

    success_count = 0
    conflict_count = 0

    def attempt_update(target_brand: str):
        row = test_db.get_by_model("RaceCar")
        v = row["version"]
        import time
        time.sleep(0.001)
        try:
            test_db.upsert_vehicle(
                {"car_model": "RaceCar", "brand": target_brand},
                expected_version=v,
            )
            return True
        except OptimisticLockError:
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(attempt_update, f"Brand_{i}") for i in range(50)]
        for f in concurrent.futures.as_completed(futures):
            if f.result():
                success_count += 1
            else:
                conflict_count += 1

    assert success_count >= 1
    assert conflict_count > 0  # Some threads must have hit optimistic lock conflicts
    # Final version should equal initial version + successful updates
    final_row = test_db.get_by_model("RaceCar")
    assert final_row["version"] == 1 + success_count


def test_borderless_table_detector_preserves_automotive_tyre_spec():
    """Verify that BorderlessTableDetector does not discard standard 28-character tyre spec rows."""
    from src.ingestion.layout_parser import BorderlessTableDetector

    # Simulate 2-column spec table:
    # Column 0: Tyre spec (28 chars, 200pt width)
    # Column 1: Config flag (2 chars, 50pt width)
    page_dict = {
        "blocks": [
            {
                "bbox": [50.0, 100.0, 500.0, 200.0],
                "lines": [
                    {
                        "bbox": [50.0, 100.0, 250.0, 115.0],
                        "spans": [{"text": "标配 Michelin 255/50 R20 静音低滚阻轮胎"}],
                    },
                    {
                        "bbox": [300.0, 100.0, 350.0, 115.0],
                        "spans": [{"text": "标配"}],
                    },
                    {
                        "bbox": [50.0, 120.0, 220.0, 135.0],
                        "spans": [{"text": "智能空气悬架系统带 CDC 动态阻尼"}],
                    },
                    {
                        "bbox": [300.0, 120.0, 350.0, 135.0],
                        "spans": [{"text": "标配"}],
                    },
                ],
            }
        ]
    }

    tables = BorderlessTableDetector.detect_tables_from_dict(
        page_dict, page_num=1, page_width=595.0, page_height=842.0
    )
    assert len(tables) >= 1
    t_md = tables[0].to_markdown()
    assert "Michelin" in t_md
    assert "空气悬架" in t_md


def test_chroma_vector_store_real_upsert_and_delete_contract(tmp_path):
    """Test ChromaVectorStore real implementation of upsert_document and delete_document."""
    vs = ChromaVectorStore(persist_directory=str(tmp_path / "chroma_real"), collection_name="test_contract")
    assert hasattr(vs, "upsert_document")
    assert hasattr(vs, "delete_document")

    # Real upsert
    vs.upsert_document(
        doc_id="model_real_1",
        text="这是小米SU7 Max的参数内容",
        metadata={"car_model": "小米SU7", "trim": "Max版", "price": "29.99万"},
        embedding=[0.1] * 1024,
    )
    assert vs.collection.count() == 1

    # Overwrite / idempotent upsert
    vs.upsert_document(
        doc_id="model_real_1",
        text="这是小米SU7 Max更新后的参数内容",
        metadata={"car_model": "小米SU7", "trim": "Max版", "price": "29.99万"},
        embedding=[0.2] * 1024,
    )
    assert vs.collection.count() == 1

    # Delete
    vs.delete_document("model_real_1")
    assert vs.collection.count() == 0


def test_vector_store_missing_contract_triggers_saga_rollback(tmp_path):
    """If vector store fails to implement upsert_document contract, pipeline MUST fail downstream and rollback."""
    test_db = VehicleDB(db_path=str(tmp_path / "saga_contract_fail.db"))

    # Object without upsert_document
    class IncompleteVectorStore:
        pass

    mock_retriever = MagicMock()
    mock_retriever.vector_store = IncompleteVectorStore()
    mock_hybrid = MagicMock()
    mock_hybrid.retriever = mock_retriever

    pipeline = IncrementalIngestionPipeline(db=test_db, hybrid_pipeline=mock_hybrid)
    v_new = {"car_model": "Model_Contract_Fail", "brand": "Brand", "price": "20万"}

    summary = pipeline.ingest_batch([v_new])
    assert summary.created_count == 0  # Rolled back
    assert test_db.get_by_model("Model_Contract_Fail") is None
    assert len(pipeline.dlq) == 1
    assert "does not implement required 'upsert_document' contract" in pipeline.dlq[0]["error"]
    assert "Model_Contract_Fail" not in pipeline.checksum_store


def test_multi_trim_doc_id_deterministic_and_no_collision(tmp_path):
    """Different trims of same car model must produce distinct doc_ids and never overwrite each other."""
    from src.models.vehicle import PreciseLabels, Vehicle

    id_std = generate_vehicle_doc_id("小米SU7", trim="标准版")
    id_pro = generate_vehicle_doc_id("小米SU7", trim="Pro版")
    id_max = generate_vehicle_doc_id("小米SU7", trim="Max版")

    assert id_std != id_pro
    assert id_pro != id_max
    assert id_std != id_max

    vs = ChromaVectorStore(persist_directory=str(tmp_path / "chroma_trims"), collection_name="test_trims")
    v1 = Vehicle(
        car_model="小米SU7",
        trim="标准版",
        precise_labels=PreciseLabels(brand="小米", price="21.59万"),
    )
    v2 = Vehicle(
        car_model="小米SU7",
        trim="Pro版",
        precise_labels=PreciseLabels(brand="小米", price="24.59万"),
    )
    v3 = Vehicle(
        car_model="小米SU7",
        trim="Max版",
        precise_labels=PreciseLabels(brand="小米", price="29.99万"),
    )

    vs.add_vehicles([v1, v2, v3], embeddings=[[0.1] * 1024, [0.2] * 1024, [0.3] * 1024])
    assert vs.collection.count() == 3


def test_pipeline_ingest_multi_trim_upserts_distinct_vector_docs(tmp_path):
    """Verify IncrementalIngestionPipeline passes unique deterministic trim doc_ids to downstream vector store."""
    test_db = VehicleDB(db_path=str(tmp_path / "test_pipeline_trims.db"))
    mock_vs = MagicMock(spec=ChromaVectorStore)
    mock_retriever = MagicMock()
    mock_retriever.vector_store = mock_vs
    mock_retriever.embedding_model = None
    mock_hybrid = MagicMock()
    mock_hybrid.retriever = mock_retriever

    pipeline = IncrementalIngestionPipeline(db=test_db, hybrid_pipeline=mock_hybrid)

    v1 = {"car_model": "小米SU7", "trim": "标准版", "brand": "小米", "price": "21.59万"}
    pipeline.ingest_batch([v1])

    assert mock_vs.upsert_document.called
    call_kwargs = mock_vs.upsert_document.call_args[1]
    expected_doc_id = generate_vehicle_doc_id("小米SU7", trim="标准版")
    assert call_kwargs["doc_id"] == expected_doc_id
    assert call_kwargs["metadata"]["trim"] == "标准版"




