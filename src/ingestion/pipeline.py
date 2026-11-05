"""
Incremental data ingestion and multi-store update pipeline for AutoVend.

Synchronizes vehicle records and document chunks across SQLite, vector store,
and cache/search indices with SAGA rollback compensation and persistent checksums.
"""

import hashlib
import json
import logging
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from src.filter.vehicle_db import VehicleDB
from src.retrieval.hybrid_pipeline import HybridPipeline

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    """Type of vehicle data change."""

    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    UNCHANGED = "unchanged"


class VehicleDataPatch(BaseModel):
    """Represents a patch for a single vehicle record."""

    car_model: str
    change_type: ChangeType
    data: Dict[str, Any] = Field(default_factory=dict)
    checksum: str = ""


class IngestionSummary(BaseModel):
    """Summary report of an ingestion pipeline run."""

    timestamp: float = Field(default_factory=time.time)
    created_count: int = 0
    updated_count: int = 0
    deleted_count: int = 0
    unchanged_count: int = 0
    total_processed: int = 0
    elapsed_seconds: float = 0.0
    affected_models: List[str] = Field(default_factory=list)


def compute_vehicle_checksum(data: Dict[str, Any]) -> str:
    """Compute SHA256 checksum of vehicle dictionary data."""
    # Exclude transient runtime control flags to ensure deterministic hashing
    clean_data = {
        k: v for k, v in data.items()
        if not k.startswith("_") and k not in ("is_deleted", "change_type")
    }
    raw_str = json.dumps(clean_data, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


class IncrementalIngestionPipeline:
    """
    Manages incremental ingestion & index updates for vehicle data.
    UPSERTS into SQLite, ChromaDB vector store, and BM25 index with SAGA rollback compensation,
    Transactional Outbox / DLQ tracking, and SQLite-persistent checksums.
    """

    def __init__(
        self,
        db: Optional[VehicleDB] = None,
        hybrid_pipeline: Optional[HybridPipeline] = None,
        freshness_engine: Optional[Any] = None,
        parent_child_retriever: Optional[Any] = None,
    ):
        self.db = db or VehicleDB()
        self.hybrid_pipeline = hybrid_pipeline
        self.freshness_engine = freshness_engine
        self.parent_child_retriever = parent_child_retriever
        self.checksum_store: Dict[str, str] = {}
        self._initialize_checksums()

    @property
    def dlq(self) -> List[Dict[str, Any]]:
        """Persistent Dead-Letter Queue queried directly from SQLite outbox_events table."""
        if hasattr(self.db, "get_outbox_events"):
            events = self.db.get_outbox_events()
            result: List[Dict[str, Any]] = []
            for ev in events:
                try:
                    payload = json.loads(ev["payload"]) if isinstance(ev["payload"], str) else ev["payload"]
                except Exception:
                    payload = {}
                result.append({
                    "id": ev["id"],
                    "car_model": payload.get("car_model", ""),
                    "operation": ev.get("event_type", ""),
                    "error": ev.get("error_message", "") or payload.get("error", ""),
                    "payload": payload.get("payload", payload),
                    "status": ev.get("status", ""),
                    "timestamp": ev.get("created_at", 0.0),
                })
            return result
        return []

    @property
    def pending_sync_queue(self) -> List[Dict[str, Any]]:
        """Persistent pending sync queue queried directly from SQLite outbox_events table."""
        return self.dlq

    def _initialize_checksums(self) -> None:
        """Load initial checksums from persistent SQLite database."""
        try:
            # 1. Load persisted checksums from SQLite checksum_store
            if hasattr(self.db, "get_all_checksums"):
                persisted = self.db.get_all_checksums()
                self.checksum_store.update(persisted)

            # 2. Backfill vehicle model checksums if not yet recorded in checksum_store
            records = self.db.get_all_models()
            for car_model in records:
                if car_model not in self.checksum_store:
                    rec = self.db.get_by_model(car_model)
                    if rec:
                        d = rec.to_dict() if hasattr(rec, "to_dict") else dict(rec)
                        ck = compute_vehicle_checksum(d)
                        self.checksum_store[car_model] = ck
                        if hasattr(self.db, "set_checksum"):
                            self.db.set_checksum(car_model, ck)
        except Exception as e:
            logger.warning(f"Could not load initial checksums: {e}")

    def _set_checksum(self, key: str, checksum: str) -> None:
        """Update checksum in memory and SQLite persistent store."""
        self.checksum_store[key] = checksum
        if hasattr(self.db, "set_checksum"):
            try:
                self.db.set_checksum(key, checksum)
            except Exception as e:
                logger.warning(f"Failed to persist checksum for {key}: {e}")

    def _delete_checksum(self, key: str) -> None:
        """Delete checksum from memory and SQLite persistent store."""
        self.checksum_store.pop(key, None)
        if hasattr(self.db, "delete_checksum"):
            try:
                self.db.delete_checksum(key)
            except Exception as e:
                logger.warning(f"Failed to delete persistent checksum for {key}: {e}")

    def _get_vehicle_models_in_store(self) -> List[str]:
        """Return all car model keys in checksum store and SQLite database."""
        models = {
            k for k in self.checksum_store.keys()
            if not k.startswith("file:") and not k.startswith("doc:")
        }
        if hasattr(self.db, "get_all_models"):
            try:
                models.update(self.db.get_all_models())
            except Exception:
                pass
        return sorted(list(models))

    def _record_dlq(
        self,
        car_model: str,
        operation: str,
        error_msg: str,
        payload: Dict[str, Any],
    ) -> None:
        """Record failure event directly to persistent SQLite outbox_events table."""
        dlq_entry = {
            "car_model": car_model,
            "operation": operation,
            "error": error_msg,
            "payload": payload,
            "timestamp": time.time(),
        }
        if hasattr(self.db, "record_outbox_event"):
            try:
                import uuid
                event_id = f"outbox_{uuid.uuid4().hex[:12]}"
                payload_str = json.dumps(dlq_entry, ensure_ascii=False, default=str)
                self.db.record_outbox_event(
                    event_id=event_id,
                    event_type=f"vehicle_sync_{operation}",
                    payload_json=payload_str,
                    status="FAILED",
                    error_message=error_msg,
                )
            except Exception as e:
                logger.warning(f"Failed to record persistent outbox event: {e}")

    def detect_changes(
        self,
        new_vehicles: List[Dict[str, Any]],
        full_sync: bool = False,
    ) -> List[VehicleDataPatch]:
        """
        Compare incoming vehicle records against stored checksums to identify changes.
        
        Args:
            new_vehicles: List of vehicle dictionary records.
            full_sync: If True, performs full snapshot reconciliation (models missing from
                       new_vehicles are marked DELETED). If False (default incremental CDC),
                       models omitted from delta batches are strictly preserved and NEVER deleted.
        """
        patches: List[VehicleDataPatch] = []
        incoming_models = set()

        for v_data in new_vehicles:
            car_model = v_data.get("car_model") or v_data.get("model")
            if not car_model:
                continue

            incoming_models.add(car_model)

            # Check explicit deletion marker
            is_explicit_delete = bool(
                v_data.get("is_deleted")
                or str(v_data.get("change_type", "")).lower() == "deleted"
                or v_data.get("change_type") == ChangeType.DELETED
                or v_data.get("_deleted")
            )
            if is_explicit_delete:
                patches.append(
                    VehicleDataPatch(
                        car_model=car_model,
                        change_type=ChangeType.DELETED,
                        data=v_data,
                        checksum="",
                    )
                )
                continue

            new_checksum = compute_vehicle_checksum(v_data)
            old_checksum = self.checksum_store.get(car_model)

            if old_checksum is None:
                patches.append(
                    VehicleDataPatch(
                        car_model=car_model,
                        change_type=ChangeType.CREATED,
                        data=v_data,
                        checksum=new_checksum,
                    )
                )
            elif old_checksum != new_checksum:
                patches.append(
                    VehicleDataPatch(
                        car_model=car_model,
                        change_type=ChangeType.UPDATED,
                        data=v_data,
                        checksum=new_checksum,
                    )
                )
            else:
                patches.append(
                    VehicleDataPatch(
                        car_model=car_model,
                        change_type=ChangeType.UNCHANGED,
                        data=v_data,
                        checksum=old_checksum,
                    )
                )

        # Detect deleted / de-listed models ONLY when full snapshot reconciliation is explicitly requested
        if full_sync:
            for old_model in self._get_vehicle_models_in_store():
                if old_model not in incoming_models:
                    patches.append(
                        VehicleDataPatch(
                            car_model=old_model,
                            change_type=ChangeType.DELETED,
                            checksum="",
                        )
                    )

        return patches

    def ingest_batch(
        self,
        new_vehicles: List[Dict[str, Any]],
        full_sync: bool = False,
    ) -> IngestionSummary:
        """
        Execute incremental ingestion and multi-index synchronization with SAGA compensation
        and Outbox DLQ consistency guarantees.

        Args:
            new_vehicles: List of vehicle dictionary data.
            full_sync: If True, performs snapshot reconciliation (missing items deleted).

        Returns:
            IngestionSummary report.
        """
        start_time = time.time()
        patches = self.detect_changes(new_vehicles, full_sync=full_sync)

        created = [p for p in patches if p.change_type == ChangeType.CREATED]
        updated = [p for p in patches if p.change_type == ChangeType.UPDATED]
        deleted = [p for p in patches if p.change_type == ChangeType.DELETED]
        unchanged = [p for p in patches if p.change_type == ChangeType.UNCHANGED]

        actually_created = 0
        actually_updated = 0
        actually_deleted = 0
        affected_models: List[str] = []

        # 1. Process CREATED & UPDATED patches with SAGA compensation
        for patch in created + updated:
            prev_record = self.db.get_by_model(patch.car_model)
            expected_version = prev_record.get("version") if prev_record else None

            # Step 1: Write to SQLite with optimistic concurrency check
            try:
                written_version = self.db.upsert_vehicle(patch.data, expected_version=expected_version)
            except Exception as e:
                logger.error(f"SQLite upsert failed for {patch.car_model}: {e}")
                self._record_dlq(patch.car_model, patch.change_type.value, str(e), patch.data)
                continue

            # Step 2: Downstream sync (Vector store & Cache / Freshness eviction)
            downstream_ok = True
            downstream_err = None
            try:
                # 2a. Update Vector Store (ChromaDB)
                if self.hybrid_pipeline and getattr(self.hybrid_pipeline, "retriever", None):
                    retriever = self.hybrid_pipeline.retriever
                    vector_store = getattr(retriever, "vector_store", None)
                    if vector_store and hasattr(vector_store, "upsert_document"):
                        vector_store.upsert_document(
                            doc_id=patch.car_model,
                            text=str(patch.data.get("key_details", "")),
                            metadata=patch.data.get("metadata", {}),
                        )

                # 2b. Evict / Invalidate Freshness Cache
                if self.freshness_engine and hasattr(self.freshness_engine, "invalidate_and_evict"):
                    if patch.change_type == ChangeType.UPDATED:
                        self.freshness_engine.invalidate_and_evict(
                            patch.car_model, reason="Incremental spec/price update", is_tombstone=False
                        )
            except Exception as sync_exc:
                downstream_ok = False
                downstream_err = sync_exc
                logger.error(
                    f"Downstream sync failed for {patch.car_model}: {sync_exc}. "
                    f"Executing SAGA rollback compensation on SQLite."
                )

            # Step 3: Consistency arbitration with concurrency verification
            if not downstream_ok:
                # SAGA Rollback SQLite write
                try:
                    curr = self.db.get_by_model(patch.car_model)
                    if curr and curr.get("version") == written_version:
                        if prev_record:
                            self.db.upsert_vehicle(prev_record, expected_version=written_version)
                        else:
                            self.db.delete_vehicle(patch.car_model, expected_version=written_version)
                    else:
                        logger.warning(
                            f"Skipping SAGA rollback for {patch.car_model}: record was concurrently modified "
                            f"(current version {curr.get('version') if curr else None} != written {written_version})"
                        )
                except Exception as rb_exc:
                    logger.critical(f"SAGA rollback failed for {patch.car_model}: {rb_exc}")

                # Record to persistent DLQ / outbox without advancing checksum
                self._record_dlq(
                    patch.car_model,
                    patch.change_type.value,
                    str(downstream_err),
                    patch.data,
                )
            else:
                # All stores acknowledged successfully: advance persistent checksum
                self._set_checksum(patch.car_model, patch.checksum)
                affected_models.append(patch.car_model)
                if patch.change_type == ChangeType.CREATED:
                    actually_created += 1
                else:
                    actually_updated += 1

        # 2. Process DELETED patches with SAGA compensation
        for patch in deleted:
            prev_record = self.db.get_by_model(patch.car_model)
            expected_version = prev_record.get("version") if prev_record else None

            # Step 1: Delete from SQLite with optimistic concurrency check
            try:
                self.db.delete_vehicle(patch.car_model, expected_version=expected_version)
            except Exception as e:
                logger.error(f"SQLite deletion failed for {patch.car_model}: {e}")
                self._record_dlq(patch.car_model, "deleted", str(e), {})
                continue

            # Step 2: Downstream deletion sync
            downstream_ok = True
            downstream_err = None
            try:
                if self.freshness_engine and hasattr(self.freshness_engine, "invalidate_and_evict"):
                    self.freshness_engine.invalidate_and_evict(
                        patch.car_model, reason="Incremental deletion", is_tombstone=True
                    )
                if self.hybrid_pipeline and getattr(self.hybrid_pipeline, "retriever", None):
                    retriever = self.hybrid_pipeline.retriever
                    vector_store = getattr(retriever, "vector_store", None)
                    if vector_store and hasattr(vector_store, "delete_document"):
                        vector_store.delete_document(patch.car_model)
            except Exception as sync_exc:
                downstream_ok = False
                downstream_err = sync_exc
                logger.error(
                    f"Downstream deletion sync failed for {patch.car_model}: {sync_exc}. "
                    f"Executing SAGA rollback compensation on SQLite."
                )

            # Step 3: Consistency arbitration
            if not downstream_ok:
                try:
                    curr = self.db.get_by_model(patch.car_model)
                    if curr is None:
                        if prev_record:
                            self.db.upsert_vehicle(prev_record)
                    else:
                        logger.warning(
                            f"Skipping SAGA rollback of deletion for {patch.car_model}: record re-created concurrently"
                        )
                except Exception as rb_exc:
                    logger.critical(f"SAGA rollback of deletion failed for {patch.car_model}: {rb_exc}")

                self._record_dlq(
                    patch.car_model,
                    "deleted",
                    str(downstream_err),
                    prev_record or {},
                )
            else:
                self._delete_checksum(patch.car_model)
                affected_models.append(patch.car_model)
                actually_deleted += 1

        elapsed = time.time() - start_time
        summary = IngestionSummary(
            created_count=actually_created,
            updated_count=actually_updated,
            deleted_count=actually_deleted,
            unchanged_count=len(unchanged),
            total_processed=len(patches),
            elapsed_seconds=round(elapsed, 3),
            affected_models=affected_models,
        )

        logger.info(
            f"Ingestion completed in {elapsed:.3f}s: +{actually_created} created, "
            f"~{actually_updated} updated, -{actually_deleted} deleted, {len(unchanged)} unchanged."
        )

        return summary

    def ingest_file(
        self,
        file_path: Union[str, Path],
        parser: Optional[Any] = None,
    ) -> IngestionSummary:
        """
        Incrementally ingest documents (PDF, Excel, Word, PPTX, Image, CSV).
        Identifies updates using SHA-256 checksums keyed by canonical path to avoid
        name collisions across different directories.
        """
        p = Path(file_path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")

        start_time = time.time()
        hasher = hashlib.sha256()
        with open(p, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        file_checksum = hasher.hexdigest()
        canonical_path = str(p)
        path_hash = hashlib.sha256(canonical_path.encode("utf-8")).hexdigest()
        store_key = f"file:{path_hash}:{p.name}"
        old_checksum = self.checksum_store.get(store_key)

        if old_checksum == file_checksum:
            logger.info(f"Document {p.name} unchanged (checksum match). Skipping.")
            return IngestionSummary(
                unchanged_count=1,
                total_processed=1,
                elapsed_seconds=round(time.time() - start_time, 3),
                affected_models=[],
            )

        # File is new or updated
        if parser is None:
            from src.ingestion.multiformat_parser import MultiFormatParser

            parser = MultiFormatParser()

        parsed_doc = parser.parse(p)
        model_name = parsed_doc.vehicle_model or p.stem

        # Chunk document
        from src.ingestion.hierarchical_chunker import HierarchicalChunker

        chunker = HierarchicalChunker()
        chunk_dict = chunker.chunk_document(parsed_doc)

        indexing_failed = False
        indexing_error = None

        # Index into ParentChildRetriever if configured
        if self.parent_child_retriever and hasattr(self.parent_child_retriever, "index_chunks"):
            try:
                self.parent_child_retriever.index_chunks(chunk_dict)
            except Exception as e:
                logger.warning(f"ParentChildRetriever indexing warning: {e}")
                indexing_failed = True
                indexing_error = e

        # Index into vector store if configured
        if self.hybrid_pipeline and getattr(self.hybrid_pipeline, "retriever", None):
            retriever = self.hybrid_pipeline.retriever
            vector_store = getattr(retriever, "vector_store", None)
            if vector_store and hasattr(vector_store, "upsert_document"):
                for parent in chunk_dict.get("parents", []):
                    try:
                        vector_store.upsert_document(
                            doc_id=parent.chunk_id,
                            text=parent.content,
                            metadata=parent.metadata,
                        )
                    except Exception as e:
                        logger.warning(f"Vector store upsert failed for chunk {parent.chunk_id}: {e}")
                        indexing_failed = True
                        indexing_error = e

        # Invalidate / update freshness engine if present
        if self.freshness_engine and hasattr(self.freshness_engine, "register_document_freshness"):
            try:
                self.freshness_engine.register_document_freshness(
                    doc_id=p.name,
                    file_path=p,
                    metadata={
                        "vehicle_model": model_name,
                        "format": parsed_doc.metadata.get("format", "unknown"),
                        "table_count": len(parsed_doc.tables),
                        "section_count": len(parsed_doc.sections),
                    },
                )
            except Exception as e:
                logger.warning(f"Freshness registration failed for {p.name}: {e}")

        # Update checksum store only if critical downstream indexing succeeded
        is_created = old_checksum is None
        if not indexing_failed:
            self._set_checksum(store_key, file_checksum)
        else:
            self._record_dlq(model_name, "file_ingest", str(indexing_error), {"file_path": str(p)})

        elapsed = time.time() - start_time
        return IngestionSummary(
            created_count=1 if is_created else 0,
            updated_count=0 if is_created else 1,
            unchanged_count=0,
            total_processed=1,
            elapsed_seconds=round(elapsed, 3),
            affected_models=[model_name],
        )

    def ingest_document(
        self,
        doc: Any,
        source_id: Optional[str] = None,
    ) -> IngestionSummary:
        """
        Incrementally ingest a pre-parsed ParsedDocument.
        """
        start_time = time.time()
        doc_id = source_id or getattr(doc, "title", "unnamed_document")
        store_key = f"doc:{doc_id}"

        # Hash doc representation
        doc_content = doc.get_full_markdown() if hasattr(doc, "get_full_markdown") else str(doc)
        doc_checksum = hashlib.sha256(doc_content.encode("utf-8")).hexdigest()
        old_checksum = self.checksum_store.get(store_key)

        if old_checksum == doc_checksum:
            return IngestionSummary(
                unchanged_count=1,
                total_processed=1,
                elapsed_seconds=round(time.time() - start_time, 3),
                affected_models=[],
            )

        from src.ingestion.hierarchical_chunker import HierarchicalChunker

        chunker = HierarchicalChunker()
        chunk_dict = chunker.chunk_document(doc)

        indexing_failed = False
        indexing_error = None

        # Index into ParentChildRetriever if configured
        if self.parent_child_retriever and hasattr(self.parent_child_retriever, "index_chunks"):
            try:
                self.parent_child_retriever.index_chunks(chunk_dict)
            except Exception as e:
                logger.warning(f"ParentChildRetriever indexing warning: {e}")
                indexing_failed = True
                indexing_error = e

        # Index into vector store if configured
        if self.hybrid_pipeline and getattr(self.hybrid_pipeline, "retriever", None):
            retriever = self.hybrid_pipeline.retriever
            vector_store = getattr(retriever, "vector_store", None)
            if vector_store and hasattr(vector_store, "upsert_document"):
                for parent in chunk_dict.get("parents", []):
                    try:
                        vector_store.upsert_document(
                            doc_id=parent.chunk_id,
                            text=parent.content,
                            metadata=parent.metadata,
                        )
                    except Exception as e:
                        logger.warning(f"Vector store upsert failed for chunk {parent.chunk_id}: {e}")
                        indexing_failed = True
                        indexing_error = e

        model_name = getattr(doc, "vehicle_model", None) or getattr(doc, "title", "unknown")

        # Invalidate / update freshness engine if present
        if self.freshness_engine and hasattr(self.freshness_engine, "register_document_freshness"):
            try:
                self.freshness_engine.register_document_freshness(
                    doc_id=doc_id,
                    file_path=None,
                    metadata={
                        "vehicle_model": model_name,
                        "format": getattr(doc, "metadata", {}).get("format", "unknown"),
                        "table_count": len(getattr(doc, "tables", [])),
                        "section_count": len(getattr(doc, "sections", [])),
                    },
                )
            except Exception as e:
                logger.warning(f"Freshness registration failed for {doc_id}: {e}")

        is_created = old_checksum is None
        if not indexing_failed:
            self._set_checksum(store_key, doc_checksum)
        else:
            self._record_dlq(model_name, "doc_ingest", str(indexing_error), {"doc_id": doc_id})

        elapsed = time.time() - start_time
        return IngestionSummary(
            created_count=1 if is_created else 0,
            updated_count=0 if is_created else 1,
            unchanged_count=0,
            total_processed=1,
            elapsed_seconds=round(elapsed, 3),
            affected_models=[model_name],
        )
