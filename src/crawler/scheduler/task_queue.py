"""
Persistent Task Queue for Universal Automotive Crawler.
Uses SQLite database for job state persistence, checkpoint recovery, and retries.
"""

import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional

from src.crawler.schemas import CrawlJob, SerialMeta, TaskStatus
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SQLiteTaskQueue:
    """Manages persistent crawl jobs with status tracking and automatic resumption."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path("/home/algieba/projects/hackthon/AutoVend/data/crawled/yiche/yiche_catalog.db")
        self._init_queue_table()

    def _init_queue_table(self) -> None:
        """Initialize crawl_jobs table."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crawl_jobs (
                    job_id TEXT PRIMARY KEY,
                    site TEXT NOT NULL,
                    brand_name TEXT NOT NULL,
                    brand_slug TEXT NOT NULL,
                    serial_name TEXT NOT NULL,
                    serial_slug TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    error_message TEXT,
                    created_at REAL,
                    updated_at REAL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_status ON crawl_jobs (status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_brand ON crawl_jobs (brand_slug)")
            conn.commit()

    def enqueue_serials(self, site: str, serials: List[SerialMeta]) -> int:
        """Enqueue multiple car series for crawling, skipping already queued jobs."""
        added = 0
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            now = time.time()
            for s in serials:
                job_id = f"{site}_{s.brand_slug}_{s.serial_slug}"
                cursor.execute("""
                    INSERT OR IGNORE INTO crawl_jobs (
                        job_id, site, brand_name, brand_slug, serial_name, serial_slug,
                        status, retry_count, max_retries, error_message, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_id, site, s.brand_name, s.brand_slug, s.serial_name, s.serial_slug,
                    TaskStatus.PENDING.value, 0, 3, "", now, now,
                ))
                if cursor.rowcount > 0:
                    added += 1
            conn.commit()
        return added

    def get_pending_jobs(self, brand_slug: Optional[str] = None, limit: int = 50) -> List[CrawlJob]:
        """Fetch pending or failed jobs eligible for execution."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if brand_slug:
                cursor.execute("""
                    SELECT * FROM crawl_jobs 
                    WHERE brand_slug = ? AND status IN (?, ?) AND retry_count < max_retries
                    ORDER BY created_at ASC LIMIT ?
                """, (brand_slug, TaskStatus.PENDING.value, TaskStatus.FAILED.value, limit))
            else:
                cursor.execute("""
                    SELECT * FROM crawl_jobs 
                    WHERE status IN (?, ?) AND retry_count < max_retries
                    ORDER BY created_at ASC LIMIT ?
                """, (TaskStatus.PENDING.value, TaskStatus.FAILED.value, limit))

            rows = cursor.fetchall()
            return [CrawlJob(**dict(r)) for r in rows]

    def update_job_status(
        self,
        job_id: str,
        status: TaskStatus,
        error_message: Optional[str] = None,
        increment_retry: bool = False,
    ) -> None:
        """Update job status and error logs."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            now = time.time()
            if increment_retry:
                cursor.execute("""
                    UPDATE crawl_jobs 
                    SET status = ?, error_message = ?, retry_count = retry_count + 1, updated_at = ?
                    WHERE job_id = ?
                """, (status.value, error_message or "", now, job_id))
            else:
                cursor.execute("""
                    UPDATE crawl_jobs 
                    SET status = ?, error_message = ?, updated_at = ?
                    WHERE job_id = ?
                """, (status.value, error_message or "", now, job_id))
            conn.commit()

    def get_stats(self) -> Dict[str, int]:
        """Get summary statistics of the task queue."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) FROM crawl_jobs GROUP BY status")
            rows = cursor.fetchall()
            stats = {s.value: 0 for s in TaskStatus}
            for status_val, cnt in rows:
                stats[status_val] = cnt
            return stats
