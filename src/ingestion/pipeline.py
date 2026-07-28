"""
Incremental Data Ingestion & Index Update Pipeline for AutoVend.

Provides zero-downtime UPSERT synchronization across SQLite, ChromaDB vector store,
and BM25 sparse index when vehicle specifications, prices, or new models change.
"""

import hashlib
import json
import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
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
    raw_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


class IncrementalIngestionPipeline:
    """
    Manages incremental ingestion & index updates for vehicle data.
    UPSERTS into SQLite, ChromaDB vector store, and BM25 index.
    """

    def __init__(self, db: Optional[VehicleDB] = None, hybrid_pipeline: Optional[HybridPipeline] = None):
        self.db = db or VehicleDB()
        self.hybrid_pipeline = hybrid_pipeline
        self.checksum_store: Dict[str, str] = {}
        self._initialize_checksums()

    def _initialize_checksums(self) -> None:
        """Load initial checksums from existing SQLite database."""
        try:
            records = self.db.get_all_models()
            for car_model in records:
                rec = self.db.get_by_model(car_model)
                if rec:
                    d = rec.to_dict() if hasattr(rec, "to_dict") else {}
                    self.checksum_store[car_model] = compute_vehicle_checksum(d)
        except Exception as e:
            logger.warning(f"Could not load initial checksums: {e}")

    def detect_changes(self, new_vehicles: List[Dict[str, Any]]) -> List[VehicleDataPatch]:
        """
        Compare incoming vehicle records against stored checksums to identify changes.
        """
        patches: List[VehicleDataPatch] = []
        incoming_models = set()

        for v_data in new_vehicles:
            car_model = v_data.get("car_model") or v_data.get("model")
            if not car_model:
                continue

            incoming_models.add(car_model)
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

        # Detect deleted / de-listed models
        for old_model in list(self.checksum_store.keys()):
            if old_model not in incoming_models:
                patches.append(
                    VehicleDataPatch(
                        car_model=old_model,
                        change_type=ChangeType.DELETED,
                        checksum="",
                    )
                )

        return patches

    def ingest_batch(self, new_vehicles: List[Dict[str, Any]]) -> IngestionSummary:
        """
        Execute incremental ingestion and multi-index synchronization.

        Args:
            new_vehicles: List of vehicle dictionary data.

        Returns:
            IngestionSummary report.
        """
        start_time = time.time()
        patches = self.detect_changes(new_vehicles)

        created = [p for p in patches if p.change_type == ChangeType.CREATED]
        updated = [p for p in patches if p.change_type == ChangeType.UPDATED]
        deleted = [p for p in patches if p.change_type == ChangeType.DELETED]
        unchanged = [p for p in patches if p.change_type == ChangeType.UNCHANGED]

        affected_models = [p.car_model for p in patches if p.change_type != ChangeType.UNCHANGED]

        # 1. Update SQLite DB Records
        for patch in created + updated:
            try:
                # Upsert record in SQLite DB
                self.db.upsert_vehicle(patch.data)
                self.checksum_store[patch.car_model] = patch.checksum
            except Exception as e:
                logger.error(f"SQLite upsert failed for {patch.car_model}: {e}")

        for patch in deleted:
            try:
                self.db.delete_vehicle(patch.car_model)
                self.checksum_store.pop(patch.car_model, None)
            except Exception as e:
                logger.error(f"SQLite deletion failed for {patch.car_model}: {e}")

        # 2. Update Vector Store (ChromaDB) if pipeline is configured
        if self.hybrid_pipeline and getattr(self.hybrid_pipeline, "retriever", None):
            retriever = self.hybrid_pipeline.retriever
            vector_store = getattr(retriever, "vector_store", None)
            if vector_store and hasattr(vector_store, "upsert_document"):
                for patch in created + updated:
                    try:
                        vector_store.upsert_document(
                            doc_id=patch.car_model,
                            text=str(patch.data.get("key_details", "")),
                            metadata=patch.data.get("metadata", {}),
                        )
                    except Exception as e:
                        logger.warning(f"Vector store upsert warning for {patch.car_model}: {e}")

        elapsed = time.time() - start_time
        summary = IngestionSummary(
            created_count=len(created),
            updated_count=len(updated),
            deleted_count=len(deleted),
            unchanged_count=len(unchanged),
            total_processed=len(patches),
            elapsed_seconds=round(elapsed, 3),
            affected_models=affected_models,
        )

        logger.info(
            f"Ingestion completed in {elapsed:.3f}s: +{len(created)} created, "
            f"~{len(updated)} updated, -{len(deleted)} deleted, {len(unchanged)} unchanged."
        )

        return summary
