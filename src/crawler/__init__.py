"""
AutoVend Universal Automotive Web Crawler Subsystem.
Provides extensible site adapters, dynamic serial discovery, persistent task queue, and raw data lake storage.
"""

from src.crawler.schemas import BrandMeta, CrawlJob, CrawlSummary, RawSerialSpecSheet, RawVehicleTrim, SerialMeta, TaskStatus
from src.crawler.adapters.base_adapter import BaseSiteAdapter
from src.crawler.adapters.yiche_adapter import YicheSiteAdapter
from src.crawler.scheduler.task_queue import SQLiteTaskQueue
from src.crawler.scheduler.diff_engine import DiffEngine
from src.crawler.engine import UniversalCrawlerEngine
from src.crawler.storage import RawDataStorage

__all__ = [
    "BrandMeta",
    "SerialMeta",
    "RawVehicleTrim",
    "RawSerialSpecSheet",
    "CrawlJob",
    "TaskStatus",
    "CrawlSummary",
    "BaseSiteAdapter",
    "YicheSiteAdapter",
    "SQLiteTaskQueue",
    "DiffEngine",
    "UniversalCrawlerEngine",
    "RawDataStorage",
]
