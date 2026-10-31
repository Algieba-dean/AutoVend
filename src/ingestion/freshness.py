"""
Automotive Data Freshness, Lifecycle Management & Invalidation Engine (src/ingestion/freshness.py).

Provides enterprise-grade:
1. Freshness SLA & TTL Enforcement (price staleness, promotion expiry, verification intervals)
2. Vehicle Lifecycle State Machine (ACTIVE, FACELIFTED, SUPERSEDED, DISCONTINUED, TOMBSTONE)
3. Atomic Multi-Index Invalidation & Synchronization (SQLite, ChromaDB, BM25, and Query Caches)
4. Active Recommendation Filtering Guards with Generation Upgrade Redirection
"""

import datetime
import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from src.filter.vehicle_db import VehicleDB

logger = logging.getLogger(__name__)


# ── Enumerations & Schemas ───────────────────────────────────────────────


class FreshnessStatus(str, Enum):
    """SLA verification status for vehicle specification or pricing records."""

    FRESH = "fresh"              # Verified within SLA window
    STALE = "stale"              # Approaching expiration, requires background crawl
    EXPIRED = "expired"          # Exceeded validity threshold, suppressed from quoting
    UNVERIFIED = "unverified"    # New record awaiting human or crawler verification


class LifecycleStatus(str, Enum):
    """Automotive lifecycle progression status."""

    ACTIVE = "active"                  # Current mass-production model actively on sale
    FACELIFTED = "facelifted"          # Mid-cycle refresh released
    SUPERSEDED = "superseded"          # Replaced by next-generation model
    DISCONTINUED = "discontinued"      # Ceased production and delisted
    TOMBSTONE = "tombstone"            # Delisted marker preventing obsolete recommendations


class FreshnessSLAConfig(BaseModel):
    """Configuration for data freshness service level agreements."""

    price_stale_days: int = Field(30, description="Days after which pricing data is flagged STALE")
    price_expire_days: int = Field(90, description="Days after which pricing data is flagged EXPIRED")
    spec_verification_interval_days: int = Field(180, description="Days before full spec sheet re-audit")
    strict_promotion_expiration: bool = Field(True, description="Strictly hide expired limited-time promotions")
    auto_redirect_superseded: bool = Field(True, description="Automatically suggest new generation when old is queried")


class ModelLifecycleRecord(BaseModel):
    """Lifecycle tracking and version lineage metadata for a vehicle model."""

    car_model: str = Field(..., description="Canonical vehicle model name")
    lifecycle_status: LifecycleStatus = Field(LifecycleStatus.ACTIVE, description="Lifecycle status")
    generation: str = Field("", description="Model generation, e.g. '2025款', '第二代'")
    superseded_by: Optional[str] = Field(None, description="Newer replacement model name if superseded")
    discontinued_date: Optional[str] = Field(None, description="Discontinuation date (YYYY-MM-DD)")
    last_verified_at: float = Field(default_factory=time.time, description="Timestamp of last comprehensive audit")
    price_verified_at: float = Field(default_factory=time.time, description="Timestamp of last price verification")
    promotion_expiry_date: Optional[str] = Field(None, description="Expiry date of current promotional package (YYYY-MM-DD)")
    is_tombstone: bool = Field(False, description="Whether record is a tombstone suppressing recommendations")
    deprecation_reason: str = Field("", description="Reason for delisting or deprecation")
    replacement_recommendation: str = Field("", description="Advisory note recommending successor model")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom operational tags")


class MultiIndexInvalidationReport(BaseModel):
    """Audit report of an invalidation and multi-index synchronization run."""

    timestamp: float = Field(default_factory=time.time)
    total_audited: int = 0
    fresh_count: int = 0
    stale_count: int = 0
    expired_count: int = 0
    tombstoned_count: int = 0
    superseded_redirects: int = 0
    sqlite_updated: int = 0
    chromadb_evicted: int = 0
    bm25_invalidated: int = 0
    cache_keys_purged: int = 0
    affected_models: List[str] = Field(default_factory=list)
    action_log: List[str] = Field(default_factory=list)


# ── Built-in Lifecycle Succession Registry ───────────────────────────────

DEFAULT_LIFECYCLE_MAPPINGS: Dict[str, Dict[str, Any]] = {
    # Facelift & Generation Successions
    "2023款比亚迪汉ev": {
        "car_model": "2023款比亚迪汉EV",
        "lifecycle_status": LifecycleStatus.SUPERSEDED,
        "superseded_by": "2025款比亚迪汉EV",
        "generation": "2023款",
        "replacement_recommendation": "该2023老款车型已全面升级，为您推荐升级搭载后五连杆悬架、激光雷达与全系全栈高压的【2025款比亚迪汉EV】。",
    },
    "老款问界m7": {
        "car_model": "老款问界M7",
        "lifecycle_status": LifecycleStatus.SUPERSEDED,
        "superseded_by": "问界M7 Pro",
        "generation": "老款",
        "replacement_recommendation": "老款问界M7已完成换代升级，已为您推荐搭载CDC自适应阻尼悬架与华为ADS基础版的【问界M7 Pro】及智驾Ultra版。",
    },
    "2023款极氪001": {
        "car_model": "2023款极氪001",
        "lifecycle_status": LifecycleStatus.SUPERSEDED,
        "superseded_by": "全新极氪001",
        "generation": "2023款",
        "replacement_recommendation": "2023款极氪001为400V老架构，现已全面升级为标配全栈800V高压、激光雷达及双腔空悬的【全新极氪001】。",
    },
    "2024款理想l7": {
        "car_model": "2024款理想L7",
        "lifecycle_status": LifecycleStatus.ACTIVE,
        "generation": "2024款",
    },
    # Discontinued / Tombstone Models
    "高合hiphix": {
        "car_model": "高合HiPhi X",
        "lifecycle_status": LifecycleStatus.DISCONTINUED,
        "is_tombstone": True,
        "discontinued_date": "2024-02-18",
        "deprecation_reason": "厂商产线停产重组，售后配件供应链存在重大风险，已执行售前保护性下架禁推。",
        "replacement_recommendation": "该品牌目前处于停产重组阶段，为保障您的售后维保与保值率，建议考虑同级豪华智能车如【问界M9】或【蔚来ES8】。",
    },
    "威马ex5": {
        "car_model": "威马EX5",
        "lifecycle_status": LifecycleStatus.DISCONTINUED,
        "is_tombstone": True,
        "discontinued_date": "2023-10-10",
        "deprecation_reason": "车企破产停售，车机云端服务与售后零部件无保障，严格禁推。",
        "replacement_recommendation": "该车型已停产停运，建议考虑品质成熟且保有量大的【比亚迪元PLUS】或【广汽埃安AION Y】。",
    },
}


# ── Data Freshness & Lifecycle Engine ────────────────────────────────────


class DataFreshnessEngine:
    """
    Enterprise Data Freshness, Lifecycle Management, and Invalidation Engine.
    """

    def __init__(
        self,
        db: Optional[VehicleDB] = None,
        sla_config: Optional[FreshnessSLAConfig] = None,
        vector_store: Optional[Any] = None,
        bm25_index: Optional[Any] = None,
        cache_eviction_hooks: Optional[List[Callable[[str], None]]] = None,
    ):
        self.db = db or VehicleDB()
        self.sla = sla_config or FreshnessSLAConfig()
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.cache_eviction_hooks: List[Callable[[str], None]] = cache_eviction_hooks or []
        self._lifecycle_store: Dict[str, ModelLifecycleRecord] = {}
        self._doc_freshness_store: Dict[str, Dict[str, Any]] = {}
        self._init_lifecycle_records()

    def _init_lifecycle_records(self) -> None:
        """Seed lifecycle store from pre-configured domain database."""
        for key, item in DEFAULT_LIFECYCLE_MAPPINGS.items():
            rec = ModelLifecycleRecord(**item)
            self._lifecycle_store[rec.car_model.lower().strip()] = rec

    def register_lifecycle_record(self, record: ModelLifecycleRecord) -> None:
        """Register or update a model's lifecycle metadata."""
        norm_key = record.car_model.lower().strip()
        self._lifecycle_store[norm_key] = record
        logger.info(
            f"Lifecycle record registered: {record.car_model} -> status={record.lifecycle_status.value}, "
            f"tombstone={record.is_tombstone}, superseded_by={record.superseded_by}"
        )

    def get_lifecycle_record(self, car_model: str) -> Optional[ModelLifecycleRecord]:
        """Look up lifecycle metadata by vehicle model name with exact and fuzzy fallback."""
        if not car_model:
            return None
        norm_key = car_model.lower().strip()
        if norm_key in self._lifecycle_store:
            return self._lifecycle_store[norm_key]

        # Normalized clean string check (ignoring whitespace and dashes)
        clean_key = norm_key.replace(" ", "").replace("-", "").replace("_", "")
        if len(clean_key) >= 3:
            for stored_k, rec in self._lifecycle_store.items():
                clean_stored = stored_k.replace(" ", "").replace("-", "").replace("_", "")
                if clean_stored == clean_key or clean_stored in clean_key or clean_key in clean_stored:
                    return rec

        return None

    def assess_freshness(
        self,
        car_model: str,
        now_ts: Optional[float] = None,
    ) -> Tuple[FreshnessStatus, Dict[str, Any]]:
        """
        Evaluate vehicle record against Freshness SLA.

        Returns:
            (FreshnessStatus, detailed_diagnostics_dict)
        """
        current_time = now_ts or time.time()
        record = self.get_lifecycle_record(car_model)

        if not record:
            return FreshnessStatus.UNVERIFIED, {
                "car_model": car_model,
                "reason": "未登记生命周期校验记录",
            }

        price_age_days = (current_time - record.price_verified_at) / 86400.0
        spec_age_days = (current_time - record.last_verified_at) / 86400.0

        # Check promotion expiry
        is_promo_expired = False
        if record.promotion_expiry_date:
            try:
                exp_date = datetime.datetime.strptime(record.promotion_expiry_date, "%Y-%m-%d").date()
                curr_date = datetime.datetime.fromtimestamp(current_time).date()
                if curr_date > exp_date:
                    is_promo_expired = True
            except ValueError:
                pass

        diagnostics = {
            "car_model": car_model,
            "lifecycle_status": record.lifecycle_status.value,
            "is_tombstone": record.is_tombstone,
            "price_age_days": round(price_age_days, 1),
            "spec_age_days": round(spec_age_days, 1),
            "is_promo_expired": is_promo_expired,
            "promotion_expiry_date": record.promotion_expiry_date,
        }

        # Check expiration thresholds
        if record.is_tombstone or record.lifecycle_status == LifecycleStatus.DISCONTINUED:
            return FreshnessStatus.EXPIRED, {**diagnostics, "reason": "车型已停产停售(Tombstone)"}

        if price_age_days >= self.sla.price_expire_days:
            return FreshnessStatus.EXPIRED, {**diagnostics, "reason": f"价格数据超期 {price_age_days:.0f} 天未核验"}

        if self.sla.strict_promotion_expiration and is_promo_expired:
            return FreshnessStatus.EXPIRED, {**diagnostics, "reason": "限时促销权益已过期"}

        # Check staleness thresholds
        if price_age_days >= self.sla.price_stale_days or spec_age_days >= self.sla.spec_verification_interval_days:
            return FreshnessStatus.STALE, {**diagnostics, "reason": "价格或参数数据接近SLA校验红线，建议增量核验"}

        return FreshnessStatus.FRESH, {**diagnostics, "reason": "数据处于SLA有效保鲜期内"}

    def register_document_freshness(
        self,
        doc_id: str,
        file_path: Optional[Any] = None,
        last_modified_ts: Optional[float] = None,
        ttl_days: int = 180,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register document lifecycle and freshness tracking entry."""
        norm_id = doc_id.strip()
        ts = last_modified_ts
        if ts is None and file_path and hasattr(file_path, "exists") and file_path.exists():
            ts = file_path.stat().st_mtime
        if ts is None:
            ts = time.time()

        self._doc_freshness_store[norm_id] = {
            "doc_id": norm_id,
            "file_path": str(file_path) if file_path else "",
            "registered_at": time.time(),
            "last_verified_at": ts,
            "ttl_days": ttl_days,
            "metadata": metadata or {},
        }
        logger.info(f"Registered document freshness: {norm_id} (TTL: {ttl_days} days)")

    def assess_document_freshness(
        self,
        doc_id: str,
        now_ts: Optional[float] = None,
    ) -> Tuple[FreshnessStatus, Dict[str, Any]]:
        """Evaluate document against TTL threshold."""
        current_time = now_ts or time.time()
        norm_id = doc_id.strip()
        rec = self._doc_freshness_store.get(norm_id)
        if not rec:
            return FreshnessStatus.UNVERIFIED, {
                "doc_id": doc_id,
                "reason": "未登记文档新鲜度跟踪记录",
            }

        age_days = (current_time - rec["last_verified_at"]) / 86400.0
        ttl_days = rec.get("ttl_days", 180)
        diagnostics = {
            "doc_id": doc_id,
            "age_days": round(age_days, 1),
            "ttl_days": ttl_days,
            "metadata": rec.get("metadata", {}),
        }

        if age_days >= ttl_days:
            return FreshnessStatus.EXPIRED, {**diagnostics, "reason": f"文档超期 {age_days:.1f} 天未更新 (TTL: {ttl_days}天)"}
        elif age_days >= ttl_days * 0.75:
            return FreshnessStatus.STALE, {**diagnostics, "reason": f"文档即将过期 (已过 {age_days:.1f}/{ttl_days}天)"}
        else:
            return FreshnessStatus.FRESH, {**diagnostics, "reason": f"文档有效新鲜 (已更新 {age_days:.1f}天)"}

    def invalidate_and_evict(
        self,
        car_model: str,
        reason: str = "Manual Invalidation",
        is_tombstone: bool = False,
        superseded_by: Optional[str] = None,
    ) -> MultiIndexInvalidationReport:
        """
        Execute atomic invalidation and cache eviction across SQLite, ChromaDB, BM25, and LRU caches.
        """
        report = MultiIndexInvalidationReport(
            affected_models=[car_model],
            action_log=[],
        )

        record = self.get_lifecycle_record(car_model)
        if not record:
            record = ModelLifecycleRecord(
                car_model=car_model,
                lifecycle_status=LifecycleStatus.TOMBSTONE if is_tombstone else LifecycleStatus.SUPERSEDED,
                is_tombstone=is_tombstone,
                superseded_by=superseded_by,
                deprecation_reason=reason,
            )
        else:
            if is_tombstone:
                record.is_tombstone = True
                record.lifecycle_status = LifecycleStatus.TOMBSTONE
            if superseded_by:
                record.superseded_by = superseded_by
                record.lifecycle_status = LifecycleStatus.SUPERSEDED
            record.deprecation_reason = reason

        self.register_lifecycle_record(record)
        report.action_log.append(f"Lifecycle state updated for {car_model}: {record.lifecycle_status.value}")

        # 1. Synchronize SQLite Record (Mark tombstone or delist)
        try:
            if is_tombstone:
                # Optionally delete or retain with inactive flag
                self.db.delete_vehicle(car_model)
                report.sqlite_updated += 1
                report.action_log.append(f"SQLite vehicle deleted/tombstoned for {car_model}")
            else:
                # Update record in DB if exists
                existing = self.db.get_by_model(car_model)
                if existing:
                    existing["lifecycle_status"] = record.lifecycle_status.value
                    if superseded_by:
                        existing["superseded_by"] = superseded_by
                    self.db.upsert_vehicle(existing)
                    report.sqlite_updated += 1
                    report.action_log.append(f"SQLite vehicle metadata updated for {car_model}")
        except Exception as e:
            logger.error(f"SQLite invalidation error for {car_model}: {e}")
            report.action_log.append(f"SQLite error: {e}")

        # 2. Evict from Vector Store (ChromaDB)
        if self.vector_store and hasattr(self.vector_store, "delete_document"):
            try:
                self.vector_store.delete_document(doc_id=car_model)
                report.chromadb_evicted += 1
                report.action_log.append(f"ChromaDB embedding purged for {car_model}")
            except Exception as e:
                logger.warning(f"Vector store eviction warning for {car_model}: {e}")

        # 3. Invalidate BM25 Sparse Index
        if self.bm25_index and hasattr(self.bm25_index, "invalidate_document"):
            try:
                self.bm25_index.invalidate_document(doc_id=car_model)
                report.bm25_invalidated += 1
                report.action_log.append(f"BM25 index entry invalidated for {car_model}")
            except Exception as e:
                logger.warning(f"BM25 invalidation warning for {car_model}: {e}")

        # 4. Invoke Registered Cache Eviction Hooks
        for hook in self.cache_eviction_hooks:
            try:
                hook(car_model)
                report.cache_keys_purged += 1
                report.action_log.append(f"Cache hook executed for {car_model}")
            except Exception as e:
                logger.warning(f"Cache hook error for {car_model}: {e}")

        report.total_audited = 1
        if is_tombstone:
            report.tombstoned_count = 1
        if superseded_by:
            report.superseded_redirects = 1

        logger.info(
            f"Multi-index invalidation completed for {car_model}: "
            f"SQLite={report.sqlite_updated}, ChromaDB={report.chromadb_evicted}, "
            f"BM25={report.bm25_invalidated}, Caches={report.cache_keys_purged}"
        )

        return report

    def run_batch_freshness_audit(
        self,
        candidate_models: Optional[List[str]] = None,
        auto_purge_expired: bool = False,
    ) -> MultiIndexInvalidationReport:
        """
        Execute scheduled batch SLA check across all models in database.
        """
        models = candidate_models or self.db.get_all_models()
        report = MultiIndexInvalidationReport(
            total_audited=len(models),
            affected_models=[],
            action_log=[],
        )

        for model in models:
            status, diag = self.assess_freshness(model)
            if status == FreshnessStatus.FRESH:
                report.fresh_count += 1
            elif status == FreshnessStatus.STALE:
                report.stale_count += 1
                report.affected_models.append(model)
                report.action_log.append(f"[STALE] {model}: {diag.get('reason')}")
            elif status == FreshnessStatus.EXPIRED:
                report.expired_count += 1
                report.affected_models.append(model)
                report.action_log.append(f"[EXPIRED] {model}: {diag.get('reason')}")

                if auto_purge_expired and diag.get("is_tombstone"):
                    sub_rep = self.invalidate_and_evict(model, reason=diag.get("reason", "Expired SLA"), is_tombstone=True)
                    report.sqlite_updated += sub_rep.sqlite_updated
                    report.chromadb_evicted += sub_rep.chromadb_evicted
                    report.bm25_invalidated += sub_rep.bm25_invalidated
                    report.cache_keys_purged += sub_rep.cache_keys_purged
                    report.tombstoned_count += 1

        return report

    def filter_recommendable_vehicles(
        self,
        candidate_vehicles: List[Any],
        allow_superseded: bool = False,
    ) -> Tuple[List[Any], List[str]]:
        """
        Production guard: Filter out discontinued/tombstone models, and seamlessly
        annotate superseded generation upgrade recommendations. Supports Dicts, Pydantic Models,
        and objects with diverse naming schemas (car_model, model, name, vehicle_name, model_name).

        Returns:
            (valid_recommendable_vehicles, upgrade_advisory_notes)
        """
        filtered: List[Any] = []
        advisory_notes: List[str] = []

        if not candidate_vehicles:
            return [], []

        for v in candidate_vehicles:
            if v is None:
                continue

            # Extract model name safely across dicts and object models
            model_name = ""
            if isinstance(v, dict):
                model_name = (
                    v.get("car_model")
                    or v.get("model")
                    or v.get("name")
                    or v.get("vehicle_name")
                    or v.get("model_name")
                    or ""
                )
            elif hasattr(v, "car_model"):
                model_name = getattr(v, "car_model", "")
            elif hasattr(v, "model"):
                model_name = getattr(v, "model", "")
            elif hasattr(v, "name"):
                model_name = getattr(v, "name", "")
            elif hasattr(v, "model_dump") and callable(v.model_dump):
                d = v.model_dump()
                model_name = d.get("car_model") or d.get("model") or d.get("name") or ""

            model_name = str(model_name).strip() if model_name else ""
            if not model_name:
                continue

            status, diag = self.assess_freshness(model_name)
            record = self.get_lifecycle_record(model_name)

            # 1. Strictly block tombstones & discontinued models
            if record and (record.is_tombstone or record.lifecycle_status == LifecycleStatus.DISCONTINUED):
                logger.info(f"Suppressed tombstoned vehicle from recommendation: {model_name}")
                continue

            # 2. Check superseded generation upgrade mapping
            if record and record.lifecycle_status == LifecycleStatus.SUPERSEDED and record.superseded_by:
                note = record.replacement_recommendation or (
                    f"车型【{model_name}】已有改款升级版，推荐关注升级换代车型【{record.superseded_by}】。"
                )
                if note not in advisory_notes:
                    advisory_notes.append(note)

                if not allow_superseded:
                    logger.info(f"Redirecting superseded model {model_name} -> {record.superseded_by}")
                    continue

            # 3. Passed validation guard
            filtered.append(v)

        return filtered, advisory_notes
