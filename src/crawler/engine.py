"""
Universal Crawler Engine (src/crawler/engine.py).
Coordinates Site Adapters, Task Queue, Diff Engine, and Raw Data Lake Storage.
"""

import asyncio
import time
from typing import Dict, List, Optional

from src.crawler.adapters.yiche_adapter import CANONICAL_BRAND_SLUGS, YicheSiteAdapter
from src.crawler.schemas import BrandMeta, CrawlSummary, SerialMeta, TaskStatus
from src.crawler.scheduler.diff_engine import DiffEngine
from src.crawler.scheduler.task_queue import SQLiteTaskQueue
from src.crawler.storage import RawDataStorage
from src.utils.logger import get_logger

logger = get_logger(__name__)


class UniversalCrawlerEngine:
    """Enterprise-grade, extensible orchestrator for automotive data crawling."""

    def __init__(
        self,
        adapter: Optional[YicheSiteAdapter] = None,
        storage: Optional[RawDataStorage] = None,
        task_queue: Optional[SQLiteTaskQueue] = None,
        diff_engine: Optional[DiffEngine] = None,
        headless: bool = True,
    ):
        self.storage = storage or RawDataStorage()
        self.task_queue = task_queue or SQLiteTaskQueue(self.storage.db_path)
        self.diff_engine = diff_engine or DiffEngine(self.storage.db_path)
        self.adapter = adapter or YicheSiteAdapter(headless=headless)

    async def crawl_brand(
        self,
        brand_name: str,
        delay_seconds: float = 1.2,
        include_discontinued: bool = True,
    ) -> CrawlSummary:
        """
        Crawl all vehicle series under a given brand dynamically without hardcoded slugs.
        """
        start_time = time.time()
        await self.adapter.initialize()

        b_slug = CANONICAL_BRAND_SLUGS.get(brand_name, brand_name.lower().replace(" ", "_"))
        brand_meta = BrandMeta(name=brand_name, slug=b_slug)

        # 1. Discover all series dynamically
        serials = await self.adapter.discover_serials_by_brand(brand_meta)
        logger.info(f"Discovered {len(serials)} series for brand [{brand_name}] (slug: {b_slug})")

        # 2. Enqueue into task queue
        self.task_queue.enqueue_serials(site="yiche", serials=serials)

        total_trims = 0
        failed_serials = []

        # 3. Process jobs
        for serial in serials:
            job_id = f"yiche_{serial.brand_slug}_{serial.serial_slug}"
            self.task_queue.update_job_status(job_id, TaskStatus.RUNNING)

            try:
                sheet = await self.adapter.extract_serial_full_specs(
                    serial=serial,
                    include_discontinued=include_discontinued,
                )

                if sheet and sheet.total_trims > 0:
                    self.storage.save_serial_specs(sheet)
                    total_trims += sheet.total_trims
                    self.task_queue.update_job_status(job_id, TaskStatus.SUCCESS)
                    logger.info(f"✓ Succeeded [{serial.brand_name}] {serial.serial_name}: {sheet.total_trims} trims")
                else:
                    self.task_queue.update_job_status(job_id, TaskStatus.FAILED, error_message="Empty trims", increment_retry=True)
                    failed_serials.append(serial.serial_slug)

            except Exception as e:
                logger.error(f"Error crawling serial {serial.serial_slug}: {e}")
                self.task_queue.update_job_status(job_id, TaskStatus.FAILED, error_message=str(e), increment_retry=True)
                failed_serials.append(serial.serial_slug)

            await asyncio.sleep(delay_seconds)

        elapsed = time.time() - start_time
        return CrawlSummary(
            brand=brand_name,
            total_serials=len(serials) - len(failed_serials),
            total_trims=total_trims,
            failed_serials=failed_serials,
            elapsed_seconds=round(elapsed, 2),
            output_directory=str(self.storage.raw_dir),
        )

    async def crawl_multi_brands(
        self,
        brands: List[str],
        delay_seconds: float = 1.2,
    ) -> Dict[str, CrawlSummary]:
        """Batch crawl multiple automotive brands."""
        results = {}
        try:
            await self.adapter.initialize()
            for b in brands:
                summary = await self.crawl_brand(brand_name=b.strip(), delay_seconds=delay_seconds)
                results[b] = summary
        finally:
            await self.adapter.close()
        return results

    async def close(self) -> None:
        """Shutdown adapter."""
        await self.adapter.close()
