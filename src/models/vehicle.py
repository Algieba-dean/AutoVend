"""
车辆数据模型

基于TOML数据结构的Pydantic模型定义。
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PreciseLabels(BaseModel):
    """精确标签数据"""

    # 基础信息
    prize: Optional[str] = None
    prize_comments: Optional[str] = None

    vehicle_category_bottom: Optional[str] = None
    vehicle_category_bottom_comments: Optional[str] = None

    brand: Optional[str] = None
    brand_comments: Optional[str] = None

    powertrain_type: Optional[str] = None
    powertrain_type_comments: Optional[str] = None

    # 尺寸和空间
    passenger_sapce_volume: Optional[str] = None
    passenger_sapce_volume_comments: Optional[str] = None

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
    voice_interfaction: Optional[str] = None
    voice_interfaction_comments: Optional[str] = None

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

    # 底盘和传动
    drive_type: Optional[str] = None
    drive_type_comments: Optional[str] = None

    suspension: Optional[str] = None
    suspension_comments: Optional[str] = None

    passibility: Optional[str] = None
    passibility_comments: Optional[str] = None

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
    clod_resistance: Optional[str] = None
    clod_resistance_comments: Optional[str] = None

    heat_resistance: Optional[str] = None
    heat_resistance_comments: Optional[str] = None


class AmbiguousLabels(BaseModel):
    """模糊标签数据"""

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

    key_details: Optional[str] = None
    key_details_comments: Optional[str] = None


class Vehicle(BaseModel):
    """车辆数据模型"""

    title: str = "CarLabels"
    car_model: str
    precise_labels: PreciseLabels = Field(alias="PriciseLabels")
    ambiguous_labels: AmbiguousLabels = Field(alias="AmbiguousLabels")
    key_details: KeyDetails = Field(alias="KeyDetails")

    # 原始数据（用于调试）
    raw_data: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True
        extra = "allow"

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

        if self.precise_labels.prize:
            parts.append(f"价格: {self.precise_labels.prize}")

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

    def get_price_range(self) -> Optional[tuple]:
        """提取价格区间"""
        if not self.precise_labels.prize:
            return None

        price_str = self.precise_labels.prize
        # 简单的价格解析逻辑，可以根据实际情况调整
        if "~" in price_str:
            try:
                parts = price_str.split("~")
                if len(parts) == 2:
                    # 移除非数字字符
                    min_price = "".join(filter(str.isdigit, parts[0].strip()))
                    max_price = "".join(filter(str.isdigit, parts[1].strip()))
                    if min_price and max_price:
                        return (int(min_price), int(max_price))
            except (ValueError, IndexError):
                pass

        return None

    def matches_price_range(self, target_price: int, tolerance: float = 0.2) -> bool:
        """检查是否匹配目标价格范围"""
        price_range = self.get_price_range()
        if not price_range:
            return True  # 如果没有价格信息，默认匹配

        min_price, max_price = price_range
        price_tolerance = int(target_price * tolerance)

        return (min_price - price_tolerance) <= target_price <= (max_price + price_tolerance)
