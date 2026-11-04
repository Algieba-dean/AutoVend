"""
Standard MCP (Model Context Protocol) Client for automotive CRM and DMS integration.
"""

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseMCPClient(ABC):
    """Abstract interface for communicating with external Dealership Management Systems."""

    @abstractmethod
    def query_inventory(
        self,
        model_name: Optional[str] = None,
        series: Optional[str] = None,
        store_id: str = "BYD_FLAGSHIP_001",
    ) -> List[Dict[str, Any]]:
        """Query real-time DMS inventory."""
        raise NotImplementedError

    @abstractmethod
    def create_reservation(
        self,
        customer_name: str,
        phone_number: str,
        car_model: str,
        date_time: str,
        store_id: str = "BYD_FLAGSHIP_001",
    ) -> Dict[str, Any]:
        """Submit test drive appointment to CRM."""
        raise NotImplementedError

    @abstractmethod
    def cancel_reservation(self, booking_id: str) -> bool:
        """Cancel test drive booking in CRM."""
        raise NotImplementedError


class MockBYDMCPServer(BaseMCPClient):
    """In-memory reference MCP server simulating BYD Dealer Management System (DMS) & CRM."""

    def __init__(self):
        self._inventory = [
            {
                "vin": "LGXCE4C89R000101",
                "brand": "BYD",
                "series": "Dynasty",
                "car_model": "BYD-Han EV",
                "trim": "605KM 尊贵型",
                "color": "玄空黑 / 藕丝灰内饰",
                "stock_count": 3,
                "showroom_display": True,
                "price": 20.98,
                "status": "AVAILABLE",
            },
            {
                "vin": "LGXCE4C89R000102",
                "brand": "BYD",
                "series": "Dynasty",
                "car_model": "BYD-Han EV",
                "trim": "715KM 旗舰型",
                "color": "时光灰 / 麒麟棕内饰",
                "stock_count": 2,
                "showroom_display": True,
                "price": 24.98,
                "status": "AVAILABLE",
            },
            {
                "vin": "LGXCE4C89R000201",
                "brand": "BYD",
                "series": "Dynasty",
                "car_model": "BYD-Tang DM-i",
                "trim": "112KM 尊贵型",
                "color": "银釉白 / 赤兔棕内饰",
                "stock_count": 4,
                "showroom_display": True,
                "price": 17.98,
                "status": "AVAILABLE",
            },
            {
                "vin": "LGXCE4C89R000301",
                "brand": "BYD",
                "series": "Dynasty",
                "car_model": "BYD-Song Pro DM-i",
                "trim": "110KM 卓越型",
                "color": "雪域白 / 净月米内饰",
                "stock_count": 6,
                "showroom_display": False,
                "price": 13.98,
                "status": "AVAILABLE",
            },
            {
                "vin": "LGXCE4C89R000401",
                "brand": "BYD",
                "series": "Dynasty",
                "car_model": "BYD-Qin Plus DM-i",
                "trim": "荣耀版 55KM 领先型",
                "color": "白釉青 / 暖阳棕内饰",
                "stock_count": 8,
                "showroom_display": True,
                "price": 7.98,
                "status": "AVAILABLE",
            },
            {
                "vin": "LGXCE4C89R000501",
                "brand": "BYD",
                "series": "Dynasty",
                "car_model": "BYD-Yuan Plus",
                "trim": "荣耀版 510KM 卓越型",
                "color": "冲浪蓝 / 律动米内饰",
                "stock_count": 5,
                "showroom_display": True,
                "price": 13.98,
                "status": "AVAILABLE",
            },
            {
                "vin": "LGXCE4C89R000601",
                "brand": "BYD",
                "series": "Ocean",
                "car_model": "BYD-SEAL EV",
                "trim": "荣耀版 700KM 性能版",
                "color": "极光白 / 塔希提蓝内饰",
                "stock_count": 3,
                "showroom_display": True,
                "price": 21.98,
                "status": "AVAILABLE",
            },
            {
                "vin": "LGXCE4C89R000701",
                "brand": "BYD",
                "series": "Ocean",
                "car_model": "BYD-Dolphin",
                "trim": "荣耀版 420KM 自由版",
                "color": "芝士黄 / 噗噗粉内饰",
                "stock_count": 7,
                "showroom_display": True,
                "price": 9.98,
                "status": "AVAILABLE",
            },
        ]
        self._reservations: Dict[str, Dict[str, Any]] = {}

    def query_inventory(
        self,
        model_name: Optional[str] = None,
        series: Optional[str] = None,
        store_id: str = "BYD_FLAGSHIP_001",
    ) -> List[Dict[str, Any]]:
        results = self._inventory
        if series:
            results = [item for item in results if item["series"].lower() == series.lower()]
        if model_name:
            alias_map = {
                "汉": "han",
                "唐": "tang",
                "宋": "song",
                "秦": "qin",
                "元": "yuan",
                "海豹": "seal",
                "海豚": "dolphin",
                "海鸥": "atto",
            }
            target = model_name.lower().replace(" ", "").replace("-", "")
            for zh, en in alias_map.items():
                if zh in target:
                    target = en
                    break
            results = [
                item
                for item in results
                if target in item["car_model"].lower().replace(" ", "").replace("-", "")
            ]
        return results

    def create_reservation(
        self,
        customer_name: str,
        phone_number: str,
        car_model: str,
        date_time: str,
        store_id: str = "BYD_FLAGSHIP_001",
    ) -> Dict[str, Any]:
        booking_id = f"BYD_TD_{uuid.uuid4().hex[:8].upper()}"
        record = {
            "booking_id": booking_id,
            "store_id": store_id,
            "customer_name": customer_name,
            "phone_number": phone_number,
            "car_model": car_model,
            "date_time": date_time,
            "status": "CONFIRMED",
        }
        self._reservations[booking_id] = record
        logger.info(f"DMS/CRM test drive reservation confirmed: {booking_id}")
        return record

    def cancel_reservation(self, booking_id: str) -> bool:
        if booking_id in self._reservations:
            self._reservations[booking_id]["status"] = "CANCELLED"
            logger.info(f"DMS/CRM test drive reservation cancelled: {booking_id}")
            return True
        return False
