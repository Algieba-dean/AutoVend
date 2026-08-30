"""
Unit tests for Yiche Crawler and Raw Data Storage (src/crawler/).
"""

import tempfile
from pathlib import Path
from src.crawler.schemas import RawSerialSpecSheet, RawVehicleTrim
from src.crawler.storage import RawDataStorage
from src.crawler.yiche_crawler import YichePlaywrightCrawler


def test_storage_save_and_query():
    """Test saving raw series specs to JSON and SQLite catalog."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = RawDataStorage(base_dir=Path(tmpdir))

        trim1 = RawVehicleTrim(
            car_id="188454",
            brand="比亚迪",
            serial="汉",
            serial_slug="han",
            trim_name="26款 EV 智驾版 705km 闪充尊贵型",
            price_guide="17.98万",
            powertrain_type="纯电",
            category_bottom="中大型车",
            specs={
                "基本信息": {"指导价": "17.98万", "能源类型": "纯电"},
                "电动机": {"总功率": "240kW"},
            },
        )
        trim2 = RawVehicleTrim(
            car_id="188999",
            brand="比亚迪",
            serial="汉",
            serial_slug="han",
            trim_name="26款 EV 智驾版 705km 闪充尊荣型",
            price_guide="18.78万",
            powertrain_type="纯电",
            category_bottom="中大型车",
            specs={
                "基本信息": {"指导价": "18.78万", "能源类型": "纯电"},
                "电动机": {"总功率": "240kW"},
            },
        )

        sheet = RawSerialSpecSheet(
            brand="比亚迪",
            serial="汉",
            serial_slug="han",
            total_trims=2,
            categories=["基本信息", "电动机"],
            trims=[trim1, trim2],
        )

        saved_path = storage.save_serial_specs(sheet)
        assert saved_path.exists()

        trims = storage.get_all_trims(brand="比亚迪")
        assert len(trims) == 2
        assert trims[0]["trim_name"] == "26款 EV 智驾版 705km 闪充尊贵型"
        assert trims[0]["price_guide"] == "17.98万"
        assert trims[0]["powertrain_type"] == "纯电"


def test_parse_api_payload():
    """Test parsing get_param_details JSON payload into RawSerialSpecSheet."""
    crawler = YichePlaywrightCrawler(headless=True)

    sample_api_payload = {
        "status": "1",
        "message": "success",
        "data": {
            "list": [
                {
                    "name": "基本信息",
                    "items": [
                        {
                            "name": "车款名称",
                            "paramValues": [
                                {
                                    "id": 101,
                                    "value": "2026款 EV 旗舰型",
                                    "baseInfoKey": '{"serialName":"海豹06"}',
                                },
                                {
                                    "id": 102,
                                    "value": "2026款 DM-i 尊贵型",
                                    "baseInfoKey": '{"serialName":"海豹06"}',
                                },
                            ],
                        },
                        {
                            "name": "厂商指导价",
                            "paramValues": [
                                {"id": 101, "value": "12.99万"},
                                {"id": 102, "value": "10.99万"},
                            ],
                        },
                        {
                            "name": "能源类型",
                            "paramValues": [
                                {"id": 101, "value": "纯电"},
                                {"id": 102, "value": "插电混动"},
                            ],
                        },
                    ],
                },
                {
                    "name": "电动机",
                    "items": [
                        {
                            "name": "电动机总功率[kW]",
                            "paramValues": [
                                {"id": 101, "value": "160"},
                                {"id": 102, "value": "120"},
                            ],
                        }
                    ],
                },
            ]
        },
    }

    sheet = crawler._parse_api_payload(
        payload=sample_api_payload,
        brand="比亚迪",
        serial_slug="haibao06",
        serial_name="海豹06",
    )

    assert sheet.total_trims == 2
    assert sheet.serial == "海豹06"
    assert len(sheet.categories) == 2
    assert sheet.trims[0].trim_name == "2026款 EV 旗舰型"
    assert sheet.trims[0].price_guide == "12.99万"
    assert sheet.trims[0].powertrain_type == "纯电"
    assert sheet.trims[0].specs["电动机"]["电动机总功率[kW]"] == "160"


def test_parse_html_table_fallback():
    """Test fallback parsing of HTML tables."""
    crawler = YichePlaywrightCrawler(headless=True)

    sample_html = """
    <table>
        <tr>
            <th>参数配置</th>
            <td>海豹06<br>2026款 530尊享型<br>12.99万</td>
        </tr>
        <tr><td>基本信息</td></tr>
        <tr>
            <th>厂商指导价</th>
            <td>12.99万</td>
        </tr>
        <tr>
            <th>能源类型</th>
            <td>纯电</td>
        </tr>
    </table>
    """

    sheet = crawler._parse_html_table(
        html=sample_html,
        brand="比亚迪",
        serial_slug="haibao06",
        serial_name="海豹06",
    )

    assert sheet.total_trims == 1
    assert "12.99万" in sheet.trims[0].price_guide
    assert sheet.trims[0].powertrain_type == "纯电"
