"""
Unified Data Schemas for Universal Automotive Crawler Subsystem.
Supports Brand/Serial metadata, raw multi-tiered trims, task queues, and diff detection.
"""

import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Execution status of a crawler job."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class DiffType(str, Enum):
    """Classification of detected vehicle data changes."""
    NEW_MODEL = "new_model"
    PRICE_CHANGED = "price_changed"
    SPEC_MODIFIED = "spec_modified"
    DISCONTINUED = "discontinued"
    UNCHANGED = "unchanged"


class BrandMeta(BaseModel):
    """Metadata for an automotive brand."""
    master_id: Optional[int] = None
    name: str  # e.g., "比亚迪", "特斯拉"
    slug: str  # e.g., "byd", "tesla"
    pinyin: Optional[str] = None
    logo_url: Optional[str] = None
    country: Optional[str] = None


class SerialMeta(BaseModel):
    """Metadata for a vehicle series/model line."""
    serial_id: Optional[str] = None
    master_id: Optional[int] = None
    brand_name: str
    brand_slug: str
    serial_name: str  # e.g., "汉", "Model Y"
    serial_slug: str  # e.g., "han", "modely"
    maker_name: Optional[str] = None  # e.g., "比亚迪·新能源"
    price_range: Optional[str] = None
    category: Optional[str] = None  # e.g., "中大型车", "SUV"


class RawVehicleTrim(BaseModel):
    """Represents a specific vehicle model trim with 300+ full-spectrum parameters."""
    car_id: Optional[str] = None
    brand: str
    brand_slug: str = ""
    serial: str
    serial_slug: str = ""
    trim_name: str  # e.g., "2026款 EV 智驾版 705km 闪充尊贵型"
    year: Optional[str] = None
    price_guide: Optional[str] = None
    price_reference: Optional[str] = None
    category_bottom: Optional[str] = None
    powertrain_type: Optional[str] = None
    specs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    raw_api_payload: Optional[Dict[str, Any]] = None
    crawled_at: float = Field(default_factory=time.time)


class RawSerialSpecSheet(BaseModel):
    """Full specification comparison sheet for an entire vehicle series."""
    brand: str
    brand_slug: str = ""
    serial: str
    serial_slug: str
    total_trims: int = 0
    categories: List[str] = Field(default_factory=list)
    trims: List[RawVehicleTrim] = Field(default_factory=list)
    crawled_at: float = Field(default_factory=time.time)


class CrawlJob(BaseModel):
    """Persistent job unit in the task queue."""
    job_id: str
    site: str = "yiche"
    brand_name: str
    brand_slug: str
    serial_name: str
    serial_slug: str
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class DiffRecord(BaseModel):
    """Individual vehicle configuration change record."""
    car_id: str
    brand: str
    serial: str
    trim_name: str
    diff_type: DiffType
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    details: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


class DiffSummary(BaseModel):
    """Summary of changes across a crawl run."""
    timestamp: float = Field(default_factory=time.time)
    total_checked: int = 0
    new_models_count: int = 0
    price_changed_count: int = 0
    spec_modified_count: int = 0
    discontinued_count: int = 0
    records: List[DiffRecord] = Field(default_factory=list)


class CrawlSummary(BaseModel):
    """Execution summary of a crawl run."""
    brand: str
    total_serials: int = 0
    total_trims: int = 0
    failed_serials: List[str] = Field(default_factory=list)
    elapsed_seconds: float = 0.0
    output_directory: str = ""
