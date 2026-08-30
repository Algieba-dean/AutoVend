"""
Unit Tests for Refactored Universal Automotive Crawler Subsystem.
Tests Site Adapters, SQLite Task Queue, Diff Engine, Storage, and Engine Orchestration.
"""

import json
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.crawler.schemas import (
    BrandMeta,
    CrawlJob,
    DiffType,
    RawSerialSpecSheet,
    RawVehicleTrim,
    SerialMeta,
    TaskStatus,
)
from src.crawler.adapters.yiche_adapter import YicheSiteAdapter
from src.crawler.scheduler.task_queue import SQLiteTaskQueue
from src.crawler.scheduler.diff_engine import DiffEngine, compute_trim_hash
from src.crawler.storage import RawDataStorage
from src.crawler.engine import UniversalCrawlerEngine


@pytest.fixture
def temp_crawler_env(tmp_path: Path):
    """Fixture providing isolated temporary storage, db, and queue."""
    db_file = tmp_path / "test_catalog.db"
    raw_dir = tmp_path / "raw"
    storage = RawDataStorage(base_dir=tmp_path)
    queue = SQLiteTaskQueue(db_path=db_file)
    diff = DiffEngine(db_path=db_file)
    return {
        "tmp_path": tmp_path,
        "db_file": db_file,
        "raw_dir": raw_dir,
        "storage": storage,
        "queue": queue,
        "diff": diff,
    }


class TestTaskQueue:
    """Tests for SQLiteTaskQueue state machine and checkpointing."""

    def test_enqueue_and_get_pending(self, temp_crawler_env):
        queue: SQLiteTaskQueue = temp_crawler_env["queue"]
        serials = [
            SerialMeta(brand_name="特斯拉", brand_slug="tesla", serial_name="Model Y", serial_slug="modely"),
            SerialMeta(brand_name="特斯拉", brand_slug="tesla", serial_name="Model 3", serial_slug="model3"),
        ]

        added = queue.enqueue_serials("yiche", serials)
        assert added == 2

        # Duplicate enqueue should be ignored
        added_again = queue.enqueue_serials("yiche", serials)
        assert added_again == 0

        pending = queue.get_pending_jobs(brand_slug="tesla")
        assert len(pending) == 2
        assert pending[0].serial_slug == "modely"
        assert pending[0].status == TaskStatus.PENDING

    def test_update_status_and_retry(self, temp_crawler_env):
        queue: SQLiteTaskQueue = temp_crawler_env["queue"]
        serials = [SerialMeta(brand_name="理想", brand_slug="li_auto", serial_name="理想L7", serial_slug="lixiangl7")]
        queue.enqueue_serials("yiche", serials)

        job_id = "yiche_li_auto_lixiangl7"
        queue.update_job_status(job_id, TaskStatus.RUNNING)
        stats = queue.get_stats()
        assert stats[TaskStatus.RUNNING.value] == 1

        queue.update_job_status(job_id, TaskStatus.FAILED, error_message="Network timeout", increment_retry=True)
        jobs = queue.get_pending_jobs()
        assert len(jobs) == 1
        assert jobs[0].retry_count == 1
        assert jobs[0].error_message == "Network timeout"

        queue.update_job_status(job_id, TaskStatus.SUCCESS)
        stats = queue.get_stats()
        assert stats[TaskStatus.SUCCESS.value] == 1


class TestDiffEngine:
    """Tests for price changes and spec modification detection."""

    def test_compute_trim_hash(self):
        h1 = compute_trim_hash({"续航": "705km"}, "21.58万")
        h2 = compute_trim_hash({"续航": "705km"}, "21.58万")
        h3 = compute_trim_hash({"续航": "705km"}, "20.58万")
        assert h1 == h2
        assert h1 != h3

    def test_detect_new_and_price_changed(self, temp_crawler_env):
        diff: DiffEngine = temp_crawler_env["diff"]
        existing = [
            {"car_id": "c1", "brand": "比亚迪", "serial": "汉", "trim_name": "舒适型", "price_guide": "16.88万"}
        ]
        new_batch = [
            {"car_id": "c1", "brand": "比亚迪", "serial": "汉", "trim_name": "舒适型", "price_guide": "15.88万"},  # Price drop
            {"car_id": "c2", "brand": "比亚迪", "serial": "汉", "trim_name": "激光雷达旗舰版", "price_guide": "21.58万"},  # New model
        ]

        summary = diff.compare_and_log(new_batch, existing_trims=existing)
        assert summary.total_checked == 2
        assert summary.price_changed_count == 1
        assert summary.new_models_count == 1

        types = {r.diff_type for r in summary.records}
        assert DiffType.PRICE_CHANGED in types
        assert DiffType.NEW_MODEL in types


class TestYicheSiteAdapterParsing:
    """Tests for Yiche JSON API payload and HTML table fallback parser."""

    def test_parse_api_payload(self):
        adapter = YicheSiteAdapter()
        serial = SerialMeta(brand_name="比亚迪", brand_slug="byd", serial_name="汉", serial_slug="han")
        mock_payload = {
            "status": "1",
            "data": {
                "list": [
                    {
                        "name": "基本信息",
                        "items": [
                            {
                                "name": "车款名称",
                                "paramValues": [
                                    {"id": 1001, "value": "2026款 EV 智驾尊贵型", "baseInfoKey": '{"serialName":"汉"}'},
                                    {"id": 1002, "value": "2026款 DM-i 智驾领航版", "baseInfoKey": '{"serialName":"汉"}'},
                                ]
                            },
                            {
                                "name": "厂商指导价",
                                "paramValues": [
                                    {"id": 1001, "value": "17.98万"},
                                    {"id": 1002, "value": "20.18万"},
                                ]
                            }
                        ]
                    }
                ]
            }
        }

        sheet = adapter._parse_api_payload(mock_payload, serial)
        assert sheet.total_trims == 2
        assert sheet.serial == "汉"
        assert sheet.trims[0].price_guide == "17.98万"
        assert sheet.trims[1].price_guide == "20.18万"
        assert "基本信息" in sheet.categories

    def test_parse_multiple_api_payloads_multi_year(self):
        adapter = YicheSiteAdapter()
        serial = SerialMeta(brand_name="零跑", brand_slug="leapmotor", serial_name="零跑T03", serial_slug="lingpaot03")
        
        payload_2025 = {
            "status": "1",
            "data": {
                "list": [
                    {
                        "name": "基本信息",
                        "items": [
                            {"name": "车款名称", "paramValues": [{"id": 20251, "value": "2025款 403舒享版", "baseInfoKey": '{"serialName":"零跑T03"}'}]},
                            {"name": "指导价", "paramValues": [{"id": 20251, "value": "6.99万"}]},
                            {"name": "年款", "paramValues": [{"id": 20251, "value": "2025"}]}
                        ]
                    }
                ]
            }
        }
        payload_2024 = {
            "status": "1",
            "data": {
                "list": [
                    {
                        "name": "基本信息",
                        "items": [
                            {"name": "车款名称", "paramValues": [{"id": 20241, "value": "2024款 310轻享版", "baseInfoKey": '{"serialName":"零跑T03"}'}]},
                            {"name": "指导价", "paramValues": [{"id": 20241, "value": "5.99万"}]},
                            {"name": "年款", "paramValues": [{"id": 20241, "value": "2024"}]}
                        ]
                    }
                ]
            }
        }

        sheet = adapter._parse_multiple_api_payloads([payload_2025, payload_2024], serial)
        assert sheet.total_trims == 2
        assert sheet.serial == "零跑T03"
        assert {t.year for t in sheet.trims} == {"2025", "2024"}
        assert {t.price_guide for t in sheet.trims} == {"6.99万", "5.99万"}

    def test_parse_html_table(self):
        adapter = YicheSiteAdapter()
        serial = SerialMeta(brand_name="蔚来", brand_slug="nio", serial_name="ET5", serial_slug="weilaiet5")
        mock_html = """
        <table>
            <tr>
                <th>参数</th>
                <th>2025款 75kWh 标准续航版<br>29.80万</th>
                <th>2025款 100kWh 长续航版<br>35.60万</th>
            </tr>
            <tr>
                <td>基本信息</td>
            </tr>
            <tr>
                <td>厂商指导价</td>
                <td>29.80万</td>
                <td>35.60万</td>
            </tr>
            <tr>
                <td>能源类型</td>
                <td>纯电</td>
                <td>纯电</td>
            </tr>
        </table>
        """
        sheet = adapter._parse_html_table(mock_html, serial)
        assert sheet.total_trims == 2
        assert sheet.trims[0].price_guide == "29.80万"
        assert sheet.trims[1].price_guide == "35.60万"
        assert sheet.trims[0].powertrain_type == "纯电"


@pytest.mark.asyncio
class TestUniversalCrawlerEngine:
    """Tests for engine orchestration."""

    async def test_crawl_brand_orchestration(self, temp_crawler_env):
        storage = temp_crawler_env["storage"]
        queue = temp_crawler_env["queue"]
        diff = temp_crawler_env["diff"]

        mock_adapter = MagicMock(spec=YicheSiteAdapter)
        mock_adapter.initialize = AsyncMock()
        mock_adapter.close = AsyncMock()
        mock_adapter.discover_serials_by_brand = AsyncMock(return_value=[
            SerialMeta(brand_name="小米", brand_slug="xiaomi", serial_name="小米SU7", serial_slug="xiaomisu7")
        ])
        mock_sheet = RawSerialSpecSheet(
            brand="小米",
            brand_slug="xiaomi",
            serial="小米SU7",
            serial_slug="xiaomisu7",
            total_trims=1,
            categories=["基本信息"],
            trims=[
                RawVehicleTrim(
                    car_id="9901",
                    brand="小米",
                    brand_slug="xiaomi",
                    serial="小米SU7",
                    serial_slug="xiaomisu7",
                    trim_name="2024款 后驱标准长续航智驾版",
                    price_guide="21.59万",
                    powertrain_type="纯电",
                    specs={"基本信息": {"厂商指导价": "21.59万"}},
                )
            ]
        )
        mock_adapter.extract_serial_full_specs = AsyncMock(return_value=mock_sheet)

        engine = UniversalCrawlerEngine(
            adapter=mock_adapter,
            storage=storage,
            task_queue=queue,
            diff_engine=diff,
        )

        summary = await engine.crawl_brand("小米", delay_seconds=0.01)
        assert summary.brand == "小米"
        assert summary.total_serials == 1
        assert summary.total_trims == 1
        assert len(summary.failed_serials) == 0

        # Check queue status
        stats = queue.get_stats()
        assert stats[TaskStatus.SUCCESS.value] == 1

        # Check storage
        trims = storage.get_all_trims()
        assert len(trims) >= 1
        assert any(t["car_id"] == "9901" for t in trims)
