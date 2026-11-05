"""
Comprehensive Automated Unit and Integration Tests for Automotive Data Freshness,
Lifecycle Management, and Multi-Index Invalidation Pipeline (tests/test_data_freshness_pipeline.py).

Covers:
1. Freshness SLA assessment (FRESH, STALE, EXPIRED, UNVERIFIED).
2. Time-based degradation (30d STALE, 90d EXPIRED, 180d spec re-verification).
3. Promotion expiration strict gating.
4. Tombstone & Discontinuation lifecycle states (HiPhi X, WM EX5).
5. Generation succession & upgrade redirection (2023 Han EV -> 2025 Han EV, Old M7 -> M7 Pro).
6. Atomic multi-index synchronization (SQLite, ChromaDB, BM25, Cache hooks).
7. Batch freshness auditing and scheduled eviction.
8. Recommendation filter guard (preventing dead stock recommendation).
9. Incremental ingestion pipeline integration with lifecycle engine.
"""

import time
import pytest

from src.filter.vehicle_db import VehicleDB
from src.ingestion.freshness import (
    DEFAULT_LIFECYCLE_MAPPINGS,
    DataFreshnessEngine,
    FreshnessSLAConfig,
    FreshnessStatus,
    LifecycleStatus,
    ModelLifecycleRecord,
    MultiIndexInvalidationReport,
)
from src.ingestion.pipeline import ChangeType, IncrementalIngestionPipeline


# =============================================================================
# 1. Lifecycle Registry and Record Tests
# =============================================================================

class TestLifecycleRegistry:
    def test_default_lifecycle_mappings_seeded(self, tmp_path):
        db = VehicleDB(db_path=str(tmp_path / "freshness_test.db"))
        engine = DataFreshnessEngine(db=db)

        # Tombstone vehicles
        hiphi = engine.get_lifecycle_record("高合HiPhi X")
        assert hiphi is not None
        assert hiphi.is_tombstone is True
        assert hiphi.lifecycle_status == LifecycleStatus.DISCONTINUED

        weima = engine.get_lifecycle_record("威马ex5")
        assert weima is not None
        assert weima.is_tombstone is True

        # Superseded vehicles
        han = engine.get_lifecycle_record("2023款比亚迪汉EV")
        assert han is not None
        assert han.lifecycle_status == LifecycleStatus.SUPERSEDED
        assert han.superseded_by == "2025款比亚迪汉EV"

        m7 = engine.get_lifecycle_record("老款问界M7")
        assert m7 is not None
        assert m7.superseded_by == "问界M7 Pro"

    def test_register_custom_lifecycle_record(self, tmp_path):
        db = VehicleDB(db_path=str(tmp_path / "freshness_test.db"))
        engine = DataFreshnessEngine(db=db)

        rec = ModelLifecycleRecord(
            car_model="旧款小鹏P7",
            lifecycle_status=LifecycleStatus.SUPERSEDED,
            superseded_by="小鹏P7+",
            generation="2020款",
            price_verified_at=time.time(),
            last_verified_at=time.time(),
        )
        engine.register_lifecycle_record(rec)

        retrieved = engine.get_lifecycle_record("旧款小鹏p7")
        assert retrieved is not None
        assert retrieved.superseded_by == "小鹏P7+"
        assert retrieved.lifecycle_status == LifecycleStatus.SUPERSEDED


# =============================================================================
# 2. Freshness SLA Assessment Tests
# =============================================================================

class TestFreshnessSLAAssessment:
    @pytest.fixture
    def engine(self, tmp_path):
        db = VehicleDB(db_path=str(tmp_path / "freshness_test.db"))
        return DataFreshnessEngine(db=db)

    def test_unverified_model(self, engine):
        status, diag = engine.assess_freshness("完全未知车型XYZ")
        assert status == FreshnessStatus.UNVERIFIED
        assert "未登记" in diag.get("reason", "")

    def test_fresh_model(self, engine):
        now = time.time()
        rec = ModelLifecycleRecord(
            car_model="测试全新车",
            lifecycle_status=LifecycleStatus.ACTIVE,
            price_verified_at=now - 5 * 86400,  # 5 days ago
            last_verified_at=now - 10 * 86400,  # 10 days ago
        )
        engine.register_lifecycle_record(rec)

        status, diag = engine.assess_freshness("测试全新车", now_ts=now)
        assert status == FreshnessStatus.FRESH
        assert diag["price_age_days"] == 5.0
        assert "保鲜期内" in diag.get("reason", "")

    def test_stale_price_threshold(self, engine):
        now = time.time()
        rec = ModelLifecycleRecord(
            car_model="测试轻度陈旧车",
            lifecycle_status=LifecycleStatus.ACTIVE,
            price_verified_at=now - 35 * 86400,  # 35 days ago (SLA: 30 days)
            last_verified_at=now - 35 * 86400,
        )
        engine.register_lifecycle_record(rec)

        status, diag = engine.assess_freshness("测试轻度陈旧车", now_ts=now)
        assert status == FreshnessStatus.STALE
        assert diag["price_age_days"] == 35.0
        assert "SLA" in diag.get("reason", "") or "核验" in diag.get("reason", "")

    def test_expired_price_threshold(self, engine):
        now = time.time()
        rec = ModelLifecycleRecord(
            car_model="测试超期车",
            lifecycle_status=LifecycleStatus.ACTIVE,
            price_verified_at=now - 95 * 86400,  # 95 days ago (SLA: 90 days)
            last_verified_at=now - 95 * 86400,
        )
        engine.register_lifecycle_record(rec)

        status, diag = engine.assess_freshness("测试超期车", now_ts=now)
        assert status == FreshnessStatus.EXPIRED
        assert diag["price_age_days"] == 95.0
        assert "超期" in diag.get("reason", "")

    def test_promotion_expiry_strict_gating(self, engine):
        now = time.time()
        # Expired promotion
        rec_expired_promo = ModelLifecycleRecord(
            car_model="促销过期车",
            lifecycle_status=LifecycleStatus.ACTIVE,
            price_verified_at=now - 5 * 86400,
            promotion_expiry_date="2020-01-01",  # Past date
        )
        engine.register_lifecycle_record(rec_expired_promo)

        status, diag = engine.assess_freshness("促销过期车", now_ts=now)
        assert status == FreshnessStatus.EXPIRED
        assert diag["is_promo_expired"] is True
        assert "促销" in diag.get("reason", "")

        # Future promotion stays fresh
        rec_valid_promo = ModelLifecycleRecord(
            car_model="促销进行车",
            lifecycle_status=LifecycleStatus.ACTIVE,
            price_verified_at=now - 5 * 86400,
            promotion_expiry_date="2099-12-31",
        )
        engine.register_lifecycle_record(rec_valid_promo)

        status_valid, diag_valid = engine.assess_freshness("促销进行车", now_ts=now)
        assert status_valid == FreshnessStatus.FRESH
        assert diag_valid["is_promo_expired"] is False

    def test_tombstone_always_expired(self, engine):
        status, diag = engine.assess_freshness("高合HiPhi X")
        assert status == FreshnessStatus.EXPIRED
        assert "Tombstone" in diag.get("reason", "") or "停产" in diag.get("reason", "")


# =============================================================================
# 3. Atomic Multi-Index Invalidation Tests
# =============================================================================

class MockVectorStore:
    def __init__(self):
        self.deleted_docs = []

    def delete_document(self, doc_id: str):
        self.deleted_docs.append(doc_id)


class MockBM25Index:
    def __init__(self):
        self.invalidated_docs = []

    def invalidate_document(self, doc_id: str):
        self.invalidated_docs.append(doc_id)


class TestMultiIndexInvalidation:
    def test_atomic_invalidation_and_eviction(self, tmp_path):
        db = VehicleDB(db_path=str(tmp_path / "freshness_test.db"))
        # Seed a vehicle in DB
        db.upsert_vehicle({"car_model": "淘汰老车A", "brand": "测试品牌", "price": "15万"})
        assert db.get_by_model("淘汰老车A") is not None

        mock_vs = MockVectorStore()
        mock_bm25 = MockBM25Index()
        evicted_cache_keys = []

        def cache_hook(key: str):
            evicted_cache_keys.append(key)

        engine = DataFreshnessEngine(
            db=db,
            vector_store=mock_vs,
            bm25_index=mock_bm25,
            cache_eviction_hooks=[cache_hook],
        )

        # Invalidate as tombstone
        report = engine.invalidate_and_evict(
            car_model="淘汰老车A",
            reason="车企停产清退",
            is_tombstone=True,
        )

        # 1. Verify report metrics
        assert report.total_audited == 1
        assert report.tombstoned_count == 1
        assert report.sqlite_updated == 1
        assert report.chromadb_evicted == 1
        assert report.bm25_invalidated == 1
        assert report.cache_keys_purged == 1
        assert "淘汰老车A" in report.affected_models
        assert len(report.action_log) >= 3

        # 2. Verify downstream effects
        assert db.get_by_model("淘汰老车A") is None
        assert "淘汰老车A" in mock_vs.deleted_docs
        assert "淘汰老车A" in mock_bm25.invalidated_docs
        assert "淘汰老车A" in evicted_cache_keys

        # 3. Verify lifecycle store marked as tombstone
        rec = engine.get_lifecycle_record("淘汰老车A")
        assert rec is not None
        assert rec.is_tombstone is True
        assert rec.lifecycle_status == LifecycleStatus.TOMBSTONE

    def test_invalidation_with_superseded_mapping(self, tmp_path):
        db = VehicleDB(db_path=str(tmp_path / "freshness_test.db"))
        db.upsert_vehicle({"car_model": "改款前车型X", "brand": "测试品牌", "price": "20万"})

        engine = DataFreshnessEngine(db=db)
        report = engine.invalidate_and_evict(
            car_model="改款前车型X",
            reason="全新换代车型上市",
            is_tombstone=False,
            superseded_by="改款后车型X Pro",
        )

        assert report.superseded_redirects == 1
        rec = engine.get_lifecycle_record("改款前车型X")
        assert rec.lifecycle_status == LifecycleStatus.SUPERSEDED
        assert rec.superseded_by == "改款后车型X Pro"

        # SQLite vehicle was updated
        assert report.sqlite_updated == 1
        stored = db.get_by_model("改款前车型X")
        assert stored is not None


# =============================================================================
# 4. Batch Freshness Audit Tests
# =============================================================================

class TestBatchFreshnessAudit:
    def test_batch_audit_reporting(self, tmp_path):
        db = VehicleDB(db_path=str(tmp_path / "freshness_test.db"))
        engine = DataFreshnessEngine(db=db)
        now = time.time()

        # Seed records with different ages
        engine.register_lifecycle_record(
            ModelLifecycleRecord(
                car_model="新鲜车型",
                price_verified_at=now - 2 * 86400,
            )
        )
        engine.register_lifecycle_record(
            ModelLifecycleRecord(
                car_model="陈旧车型",
                price_verified_at=now - 40 * 86400,
            )
        )
        engine.register_lifecycle_record(
            ModelLifecycleRecord(
                car_model="过期车型",
                price_verified_at=now - 100 * 86400,
            )
        )

        candidates = ["新鲜车型", "陈旧车型", "过期车型", "高合HiPhi X"]
        report = engine.run_batch_freshness_audit(candidate_models=candidates)

        assert report.total_audited == 4
        assert report.fresh_count == 1
        assert report.stale_count == 1
        assert report.expired_count == 2
        assert "陈旧车型" in report.affected_models
        assert "过期车型" in report.affected_models
        assert "高合HiPhi X" in report.affected_models


# =============================================================================
# 5. Recommendation Filtering Guard Tests
# =============================================================================

class TestRecommendationFilteringGuard:
    def test_filter_removes_tombstones_and_redirects_superseded(self, tmp_path):
        db = VehicleDB(db_path=str(tmp_path / "freshness_test.db"))
        engine = DataFreshnessEngine(db=db)

        candidates = [
            {"car_model": "小米SU7", "price": "21.59万"},
            {"car_model": "高合HiPhi X", "price": "57.00万"},     # Tombstone
            {"car_model": "2023款比亚迪汉EV", "price": "20.98万"}, # Superseded
            {"car_model": "老款问界M7", "price": "24.98万"},       # Superseded
            {"car_model": "威马EX5", "price": "14.98万"},          # Tombstone
        ]

        # Mode A: allow_superseded=False (Production default: strict replacement)
        filtered, advisories = engine.filter_recommendable_vehicles(candidates, allow_superseded=False)

        retained_models = [v["car_model"] for v in filtered]
        # Only Xiaomi SU7 should remain
        assert retained_models == ["小米SU7"]
        assert "高合HiPhi X" not in retained_models
        assert "威马EX5" not in retained_models
        assert "2023款比亚迪汉EV" not in retained_models
        assert "老款问界M7" not in retained_models

        # Advisory notes generated for superseded models
        assert len(advisories) == 2
        assert any("2025款比亚迪汉EV" in note for note in advisories)
        assert any("问界M7 Pro" in note for note in advisories)

    def test_filter_allows_superseded_with_annotations(self, tmp_path):
        db = VehicleDB(db_path=str(tmp_path / "freshness_test.db"))
        engine = DataFreshnessEngine(db=db)

        candidates = [
            {"car_model": "2023款比亚迪汉EV", "price": "20.98万"},
            {"car_model": "高合HiPhi X", "price": "57.00万"},
        ]

        # Mode B: allow_superseded=True (Advisory notes retained, tombstone still stripped)
        filtered, advisories = engine.filter_recommendable_vehicles(candidates, allow_superseded=True)
        retained_models = [v["car_model"] for v in filtered]

        assert retained_models == ["2023款比亚迪汉EV"]
        assert "高合HiPhi X" not in retained_models
        assert len(advisories) == 1
        assert "2025款比亚迪汉EV" in advisories[0]


# =============================================================================
# 6. Incremental Ingestion Pipeline Integration Tests
# =============================================================================

class TestPipelineWithFreshnessEngine:
    def test_ingestion_updates_and_deletes_trigger_eviction(self, tmp_path):
        db = VehicleDB(db_path=str(tmp_path / "freshness_test.db"))
        mock_vs = MockVectorStore()
        mock_bm25 = MockBM25Index()

        freshness_engine = DataFreshnessEngine(
            db=db,
            vector_store=mock_vs,
            bm25_index=mock_bm25,
        )

        pipeline = IncrementalIngestionPipeline(
            db=db,
            freshness_engine=freshness_engine,
        )

        # Batch 1: Create Model A and Model B
        v_a = {"car_model": "Model_Alpha", "brand": "AlphaBrand", "price": "25万"}
        v_b = {"car_model": "Model_Beta", "brand": "BetaBrand", "price": "35万"}
        summary1 = pipeline.ingest_batch([v_a, v_b])
        assert summary1.created_count == 2

        # Batch 2: Update Model A price, Delete Model B via snapshot reconciliation (full_sync=True)
        v_a_new = {"car_model": "Model_Alpha", "brand": "AlphaBrand", "price": "22万"}
        summary2 = pipeline.ingest_batch([v_a_new], full_sync=True)
        assert summary2.updated_count == 1
        assert summary2.deleted_count == 1

        # Model A update triggered invalidation
        rec_a = freshness_engine.get_lifecycle_record("Model_Alpha")
        assert rec_a is not None
        assert "update" in rec_a.deprecation_reason.lower() or "incremental" in rec_a.deprecation_reason.lower()

        # Model B deletion triggered tombstone invalidation and index eviction
        rec_b = freshness_engine.get_lifecycle_record("Model_Beta")
        assert rec_b is not None
        assert rec_b.is_tombstone is True
        assert "Model_Beta" in mock_vs.deleted_docs
        assert "Model_Beta" in mock_bm25.invalidated_docs


# =============================================================================
# 7. Fuzzy Lifecycle Resolution & Polymorphic Candidate Guard Tests
# =============================================================================

class TestFuzzyLifecycleAndPolymorphicCandidates:
    def test_fuzzy_lifecycle_matching_for_model_variants(self, tmp_path):
        """Model variants and trim levels must match canonical lifecycle records."""
        db = VehicleDB(db_path=str(tmp_path / "freshness_test.db"))
        engine = DataFreshnessEngine(db=db)

        # 1. Trims of tombstone car
        hiphi_trim = engine.get_lifecycle_record("高合HiPhi X 旗舰四座版")
        assert hiphi_trim is not None
        assert hiphi_trim.is_tombstone is True
        assert hiphi_trim.lifecycle_status == LifecycleStatus.DISCONTINUED

        # 2. Trims of superseded car
        han_trim = engine.get_lifecycle_record("2023款比亚迪汉EV 创世版")
        assert han_trim is not None
        assert han_trim.superseded_by == "2025款比亚迪汉EV"

    def test_filter_polymorphic_candidate_structures(self, tmp_path):
        """Test candidate list containing dicts with diverse keys, Pydantic objects, and nulls."""
        from pydantic import BaseModel

        db = VehicleDB(db_path=str(tmp_path / "freshness_test.db"))
        engine = DataFreshnessEngine(db=db)

        class CustomCandidateModel(BaseModel):
            car_model: str
            brand: str
            price: float

        candidates = [
            None,
            {},
            {"name": "问界M9", "price": 46.98},                                  # key 'name'
            {"model_name": "小米SU7", "price": 21.59},                           # key 'model_name'
            {"car_model": "高合HiPhi X 旗舰版", "price": 57.0},                   # tombstone
            {"car_model": "2023款比亚迪汉EV 尊贵型", "price": 20.98},             # superseded
            CustomCandidateModel(car_model="理想L6 Pro", brand="理想", price=24.98),  # Pydantic model
        ]

        valid, advisories = engine.filter_recommendable_vehicles(candidates)

        # Tombstone (HiPhi X) and superseded (2023 Han EV) must be filtered out
        valid_names = []
        for v in valid:
            if isinstance(v, dict):
                valid_names.append(v.get("car_model") or v.get("name") or v.get("model_name"))
            else:
                valid_names.append(v.car_model)

        assert "问界M9" in valid_names
        assert "小米SU7" in valid_names
        assert "理想L6 Pro" in valid_names
        assert not any("高合" in name for name in valid_names)
        assert not any("2023款" in name for name in valid_names)

        # Advisory generated for superseded Han EV
        assert len(advisories) == 1
        assert "2025款比亚迪汉EV" in advisories[0]

    def test_deprecated_status_and_lifecycle_handling(self, tmp_path):
        """Verify DEPRECATED enum is supported and correctly triggers expiration and advisory."""
        db = VehicleDB(db_path=str(tmp_path / "freshness_test.db"))
        engine = DataFreshnessEngine(db=db)

        rec = ModelLifecycleRecord(
            car_model="已废弃老旧燃油车",
            lifecycle_status=LifecycleStatus.DEPRECATED,
            deprecation_reason="国四排放标准全面淘汰，停止销售支持",
            price_verified_at=time.time(),
            last_verified_at=time.time(),
        )
        engine.register_lifecycle_record(rec)

        assert FreshnessStatus.DEPRECATED.value == "deprecated"
        assert LifecycleStatus.DEPRECATED.value == "deprecated"

        status, diag = engine.assess_freshness("已废弃老旧燃油车")
        assert status == FreshnessStatus.EXPIRED
        assert "国四排放标准全面淘汰" in diag["reason"]


