"""
车辆数据模型

基于TOML数据结构的Pydantic模型定义。
"""

import re
from typing import Any, Dict, Optional, Tuple

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class PreciseLabels(BaseModel):
    """精确标签数据 - 强类型 Pydantic V2 生产级规范"""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    # 规范强类型数值字段 (阶段四 P3: Data Schema Governance)
    price_min_wan: Optional[float] = Field(None, ge=0.0, le=5000.0, description="起售价(万元)")
    price_max_wan: Optional[float] = Field(None, ge=0.0, le=5000.0, description="顶配价(万元)")
    wheelbase_mm: Optional[int] = Field(None, ge=1000, le=5000, description="轴距(毫米)")
    horsepower_ps: Optional[int] = Field(None, ge=0, le=3000, description="最大马力(匹)")
    acceleration_0_100_s: Optional[float] = Field(None, ge=1.5, le=30.0, description="零百加速(秒)")
    electric_range_km: Optional[int] = Field(None, ge=0, le=2000, description="纯电CLTC续航(公里)")

    # 基础信息
    price: Optional[str] = None
    price_comments: Optional[str] = None

    vehicle_category_bottom: Optional[str] = None
    vehicle_category_bottom_comments: Optional[str] = None

    brand: Optional[str] = None
    brand_comments: Optional[str] = None

    powertrain_type: Optional[str] = None
    powertrain_type_comments: Optional[str] = None

    # 尺寸和空间
    passenger_space_volume: Optional[str] = None
    passenger_space_volume_comments: Optional[str] = None

    trunk_volume: Optional[str] = None
    trunk_volume_comments: Optional[str] = None

    wheelbase: Optional[str] = None
    wheelbase_comments: Optional[str] = None

    chassis_height: Optional[str] = None
    chassis_height_comments: Optional[str] = None

    # 外观和设计
    design_style: Optional[str] = None
    design_style_comments: Optional[str] = None

    body_line_smoothness: Optional[str] = None
    body_line_smoothness_comments: Optional[str] = None

    color: Optional[str] = None
    color_comments: Optional[str] = None

    interior_material_texture: Optional[str] = None
    interior_material_texture_comments: Optional[str] = None

    # 安全配置
    ABS: Optional[str] = None
    ABS_comments: Optional[str] = None

    ESP: Optional[str] = None
    ESP_comments: Optional[str] = None

    airbag_count: Optional[str] = None
    airbag_count_comments: Optional[str] = None

    seat_material: Optional[str] = None
    seat_material_comments: Optional[str] = None

    noise_insulation: Optional[str] = None
    noise_insulation_comments: Optional[str] = None

    # 智能化配置
    voice_interaction: Optional[str] = None
    voice_interaction_comments: Optional[str] = None

    ota_updates: Optional[str] = None
    ota_updates_comments: Optional[str] = None

    autonomous_driving_level: Optional[str] = None
    autonomous_driving_level_comments: Optional[str] = None

    adaptive_cruise_control: Optional[str] = None
    adaptive_cruise_control_comments: Optional[str] = None

    traffic_jam_assist: Optional[str] = None
    traffic_jam_assist_comments: Optional[str] = None

    automatic_emergency_braking: Optional[str] = None
    automatic_emergency_braking_comments: Optional[str] = None

    lane_keep_assist: Optional[str] = None
    lane_keep_assist_comments: Optional[str] = None

    remote_parking: Optional[str] = None
    remote_parking_comments: Optional[str] = None

    auto_parking: Optional[str] = None
    auto_parking_comments: Optional[str] = None

    blind_spot_detection: Optional[str] = None
    blind_spot_detection_comments: Optional[str] = None

    fatigue_driving_detection: Optional[str] = None
    fatigue_driving_detection_comments: Optional[str] = None

    # 动力系统
    engine_displacement: Optional[str] = None
    engine_displacement_comments: Optional[str] = None

    motor_power: Optional[str] = None
    motor_power_comments: Optional[str] = None

    battery_capacity: Optional[str] = None
    battery_capacity_comments: Optional[str] = None

    fuel_tank_capacity: Optional[str] = None
    fuel_tank_capacity_comments: Optional[str] = None

    horsepower: Optional[str] = None
    horsepower_comments: Optional[str] = None

    torque: Optional[str] = None
    torque_comments: Optional[str] = None

    zero_to_one_hundred_km_h_acceleration_time: Optional[str] = None
    zero_to_one_hundred_km_h_acceleration_time_comments: Optional[str] = None

    top_speed: Optional[str] = None
    top_speed_comments: Optional[str] = None

    fuel_consumption: Optional[str] = None
    fuel_consumption_comments: Optional[str] = None

    electric_consumption: Optional[str] = None
    electric_consumption_comments: Optional[str] = None

    driving_range: Optional[str] = None
    driving_range_comments: Optional[str] = None

    # 底盘和传动 (修复 passibility 错别字)
    drive_type: Optional[str] = None
    drive_type_comments: Optional[str] = None

    suspension: Optional[str] = None
    suspension_comments: Optional[str] = None

    passability: Optional[str] = None
    passability_comments: Optional[str] = None

    # 实用性
    seat_layout: Optional[str] = None
    seat_layout_comments: Optional[str] = None

    city_commuting: Optional[str] = None
    city_commuting_comments: Optional[str] = None

    highway_long_distance: Optional[str] = None
    highway_long_distance_comments: Optional[str] = None

    off_road_capability: Optional[str] = None
    off_road_capability_comments: Optional[str] = None

    cargo_capability: Optional[str] = None
    cargo_capability_comments: Optional[str] = None

    # 环境适应性
    cold_resistance: Optional[str] = None
    cold_resistance_comments: Optional[str] = None

    heat_resistance: Optional[str] = None
    heat_resistance_comments: Optional[str] = None

    @model_validator(mode="after")
    def _populate_numeric_fields(self) -> "PreciseLabels":
        if self.price and (self.price_min_wan is None or self.price_max_wan is None):
            p_min, p_max = self.price_range_wan
            if self.price_min_wan is None and p_min is not None:
                self.price_min_wan = p_min
            if self.price_max_wan is None and p_max is not None:
                self.price_max_wan = p_max

        if self.wheelbase_mm is None and self.wheelbase:
            m = re.search(r"(\d+)", str(self.wheelbase))
            if m:
                val = int(m.group(1))
                if 1000 <= val <= 5000:
                    self.wheelbase_mm = val

        if self.horsepower_ps is None and self.horsepower:
            m = re.search(r"(\d+)", str(self.horsepower))
            if m:
                val = int(m.group(1))
                if 0 <= val <= 3000:
                    self.horsepower_ps = val

        if self.acceleration_0_100_s is None and self.zero_to_one_hundred_km_h_acceleration_time:
            m = re.search(r"(\d+(?:\.\d+)?)", str(self.zero_to_one_hundred_km_h_acceleration_time))
            if m:
                val = float(m.group(1))
                if 1.5 <= val <= 30.0:
                    self.acceleration_0_100_s = val

        if self.electric_range_km is None and self.driving_range:
            m = re.search(r"(\d+)", str(self.driving_range))
            if m:
                val = int(m.group(1))
                if 0 <= val <= 2000:
                    self.electric_range_km = val

        return self

    # Strongly-typed parsed numeric accessors
    @property
    def price_range_wan(self) -> Tuple[Optional[float], Optional[float]]:
        """Return (min_wan, max_wan) parsed from price field."""
        if self.price_min_wan is not None and self.price_max_wan is not None:
            return self.price_min_wan, self.price_max_wan
        if not self.price:
            return None, None
        nums = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)", self.price)]
        if not nums:
            return None, None
        if len(nums) == 1:
            val = nums[0] / 10000.0 if nums[0] > 1000 else nums[0]
            return val, val
        p_min = nums[0] / 10000.0 if nums[0] > 1000 else nums[0]
        p_max = nums[1] / 10000.0 if nums[1] > 1000 else nums[1]
        return min(p_min, p_max), max(p_min, p_max)

    @property
    def acceleration_s(self) -> Optional[float]:
        """Parsed 0-100 acceleration time in seconds."""
        if self.acceleration_0_100_s is not None:
            return self.acceleration_0_100_s
        txt = self.zero_to_one_hundred_km_h_acceleration_time or ""
        m = re.search(r"(\d+(?:\.\d+)?)", txt)
        return float(m.group(1)) if m else None

    @property
    def driving_range_km(self) -> Optional[int]:
        """Parsed driving range in km."""
        if self.electric_range_km is not None:
            return self.electric_range_km
        txt = self.driving_range or ""
        m = re.search(r"(\d+)", txt)
        return int(m.group(1)) if m else None

    @property
    def top_speed_kmh(self) -> Optional[int]:
        """Parsed top speed in km/h."""
        txt = self.top_speed or ""
        m = re.search(r"(\d+)", txt)
        return int(m.group(1)) if m else None


class AmbiguousLabels(BaseModel):
    """模糊标签数据"""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    size: Optional[str] = None
    size_comments: Optional[str] = None

    vehicle_usability: Optional[str] = None
    vehicle_usability_comments: Optional[str] = None

    aesthetics: Optional[str] = None
    aesthetics_comments: Optional[str] = None

    energy_consumption_level: Optional[str] = None
    energy_consumption_level_comments: Optional[str] = None

    comfort_level: Optional[str] = None
    comfort_level_comments: Optional[str] = None

    smartness: Optional[str] = None
    smartness_comments: Optional[str] = None

    family_friendliness: Optional[str] = None
    family_friendliness_comments: Optional[str] = None


class KeyDetails(BaseModel):
    """关键详情"""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    key_details: Optional[str] = None
    key_details_comments: Optional[str] = None


class Vehicle(BaseModel):
    """车辆数据模型"""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    title: str = "CarLabels"
    car_model: str
    precise_labels: PreciseLabels = Field(
        ..., validation_alias=AliasChoices("precise_labels", "PriciseLabels")
    )
    ambiguous_labels: AmbiguousLabels = Field(
        default_factory=AmbiguousLabels,
        validation_alias=AliasChoices("ambiguous_labels", "AmbiguousLabels"),
    )
    key_details: KeyDetails = Field(
        default_factory=KeyDetails,
        validation_alias=AliasChoices("key_details", "KeyDetails"),
    )

    # 原始数据（用于调试）
    raw_data: Optional[Dict[str, Any]] = None

    def get_search_text(self) -> str:
        """
        生成用于检索的文本描述
        将结构化数据转换为自然语言描述
        """
        parts = []

        # 基础信息
        if self.precise_labels.brand:
            parts.append(f"品牌: {self.precise_labels.brand}")

        if self.car_model:
            parts.append(f"型号: {self.car_model}")

        if self.precise_labels.vehicle_category_bottom:
            parts.append(f"车型: {self.precise_labels.vehicle_category_bottom}")

        if self.precise_labels.price:
            parts.append(f"价格: {self.precise_labels.price}")

        if self.precise_labels.powertrain_type:
            parts.append(f"动力类型: {self.precise_labels.powertrain_type}")

        # 尺寸信息
        if self.precise_labels.wheelbase:
            parts.append(f"轴距: {self.precise_labels.wheelbase}")

        if self.ambiguous_labels.size:
            parts.append(f"尺寸: {self.ambiguous_labels.size}")

        # 性能信息
        if self.precise_labels.horsepower:
            parts.append(f"马力: {self.precise_labels.horsepower}")

        if self.precise_labels.fuel_consumption:
            parts.append(f"油耗: {self.precise_labels.fuel_consumption}")

        # 配置信息
        if self.precise_labels.seat_layout:
            parts.append(f"座位布局: {self.precise_labels.seat_layout}")

        if self.precise_labels.drive_type:
            parts.append(f"驱动方式: {self.precise_labels.drive_type}")

        # 智能化
        if self.precise_labels.autonomous_driving_level:
            parts.append(f"自动驾驶等级: {self.precise_labels.autonomous_driving_level}")

        # 用途
        if self.precise_labels.city_commuting == "Yes":
            parts.append("适合城市通勤")

        if self.precise_labels.highway_long_distance == "Yes":
            parts.append("适合长途高速")

        if self.precise_labels.cargo_capability == "Yes":
            parts.append("载物能力强")

        # 模糊标签
        if self.ambiguous_labels.family_friendliness:
            parts.append(f"家庭友好度: {self.ambiguous_labels.family_friendliness}")

        if self.ambiguous_labels.comfort_level:
            parts.append(f"舒适度: {self.ambiguous_labels.comfort_level}")

        # 关键详情
        if self.key_details.key_details:
            parts.append(f"描述: {self.key_details.key_details}")

        return " ".join(parts)

    def get_price_range(self) -> Optional[Tuple[int, int]]:
        """
        提取车辆价格区间 (元)。
        支持多种主流价格表示格式：
        - 中划线区间: '21.59-29.99万', '20-30万元', '21.59–29.99万起'
        - 中文'到'/'至'区间: '20万到30万', '15万至25万'
        - 波浪号区间: '30,000~40,000', '21.59~29.99万'
        - 上限/下限描述: 'Below 10,000', '10万以下', 'Above 100,000', '50万以上', '15.98万起'
        - 单一固定价格: '25万', '250000'
        """
        if not self.precise_labels or not self.precise_labels.price:
            return None

        price_str = str(self.precise_labels.price).strip()
        if not price_str:
            return None

        clean_str = price_str.replace(",", "").replace("，", "")

        # Extract numeric components first
        nums = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)", clean_str)]
        if not nums:
            return None

        # Case 1: Two or more numbers define an explicit price range (e.g. 21.59-29.99万, 21.59-29.99万起)
        # Even if '起' or '到' is present, having 2 numbers indicates a defined range
        if len(nums) >= 2:
            # Convert each number independently to RMB (元) before calculating min/max
            # to prevent inverted ranges when mixing units (e.g. '200000-25万')
            vals = [
                n * 10000 if n < 1000 else n
                for n in nums[:2]
            ]
            p_min = min(vals[0], vals[1])
            p_max = max(vals[0], vals[1])
            return (int(round(p_min)), int(round(p_max)))

        # Case 2: Exactly one number with directional qualifiers or fixed price
        val_raw = nums[0]
        val = val_raw * 10000 if val_raw < 1000 else val_raw

        # Check 'Below X' / 'X以下' / 'X以内'
        if any(w in clean_str.lower() for w in ["below", "以下", "以内"]):
            return (0, int(round(val)))

        # Check 'Above X' / 'X以上' / 'X起'
        if any(w in clean_str.lower() for w in ["above", "以上", "起"]):
            # For open-ended upper bounds, allow up to 100M RMB so luxury vehicles are not excluded
            return (int(round(val)), 100_000_000)

        # Single exact price
        ival = int(round(val))
        return (ival, ival)

    def matches_price_range(self, target_price: float, tolerance: float = 0.2) -> bool:
        """
        检查是否匹配目标价格范围。
        若车辆无有效价格区间，则无法通过价格过滤（返回 False，避免静默全部放行）。
        """
        if target_price <= 0:
            return False

        price_range = self.get_price_range()
        if not price_range:
            return False  # 修复静默失效兜底：无价格信息不可默认全部放行

        min_price, max_price = price_range
        # 兼容 target_price 以万元为单位（例如 25 或 25.0）
        norm_target = target_price * 10000 if target_price < 1000 else target_price
        price_tolerance = norm_target * tolerance

        return (min_price - price_tolerance) <= norm_target <= (max_price + price_tolerance)
