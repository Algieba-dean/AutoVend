"""
Structured Data Builders for AutoVend Enterprise Benchmark.
Generates 7 CSV/TSV telemetry datasets and 5 Structured Text documents (JSON, TOML, MD, HTML, RTF).
"""

import json
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger("enterprise_dataset_gen.data")


# ── CSV & TSV Telemetry Datasets ──────────────────────────────────────────


# 1. BYD FinDreams Battery Degradation (CSV, 60 rows)
def generate_byd_degradation_csv(out_dir: Path) -> Path:
    file_path = out_dir / "BYD_FinDreams_Battery_Degradation_1000Cycles.csv"
    headers = "cycle_index,accumulated_ah,capacity_retention_pct,dcir_mohm,coulombic_efficiency_pct,cell_max_temp_c,charge_time_min,discharge_voltage_cutoff"
    lines = [headers]
    for i in range(1, 61):
        cycle = i * 20
        ah = round(cycle * 150.2, 1)
        retention = round(100.0 - (cycle * 0.012), 2)
        dcir = round(28.0 + (cycle * 0.008), 2)
        eff = round(99.85 - (cycle * 0.0008), 3)
        temp = round(32.5 + (i % 5) * 1.2, 1)
        chg_time = round(42.0 + (cycle * 0.005), 1)
        lines.append(f"{cycle},{ah},{retention},{dcir},{eff},{temp},{chg_time},2.50")
    file_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


# 2. Tesla Supercharger V4 Telemetry Log (CSV, 60 rows)
def generate_tesla_supercharger_csv(out_dir: Path) -> Path:
    file_path = out_dir / "Tesla_Supercharger_V4_Telemetry_Log.csv"
    headers = "timestamp_sec,pack_soc_pct,charging_voltage_v,charging_current_a,charging_power_kw,cable_coolant_temp_c,pack_inlet_coolant_temp_c,bms_target_current_a"
    lines = [headers]
    for i in range(1, 61):
        sec = i * 15
        soc = min(90, 10 + int(i * 1.3))
        v = round(720.0 + (soc * 1.2), 1)
        if soc < 50:
            pwr = 350.0 - (soc * 1.5)
        else:
            pwr = 275.0 - (soc * 2.5)
        curr = round((pwr * 1000.0) / v, 1)
        cable_t = round(28.0 + (i * 0.25), 1)
        pack_t = round(32.0 + (i * 0.15), 1)
        lines.append(f"{sec},{soc},{v},{curr},{round(pwr, 1)},{cable_t},{pack_t},{curr + 5.0}")
    file_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


# 3. Xiaomi SU7 Max Nurburgring Lap Telemetry (CSV, 60 rows)
def generate_xiaomi_lap_csv(out_dir: Path) -> Path:
    file_path = out_dir / "Xiaomi_SU7_Max_Nurburgring_Lap_Telemetry.csv"
    headers = "track_distance_m,vehicle_speed_kmh,motor_front_rpm,motor_rear_rpm,throttle_position_pct,brake_pressure_bar,lateral_accel_g,longitudinal_accel_g,inverter_temp_c"
    lines = [headers]
    for i in range(1, 61):
        dist = i * 340
        speed = round(120.0 + ((i * 17) % 180), 1)
        front_rpm = int(speed * 68)
        rear_rpm = int(speed * 72)
        throttle = 100 if speed > 180 else round(30 + (i % 7) * 10, 1)
        brake = 0.0 if throttle > 50 else round(45.0 + (i % 6) * 12.0, 1)
        lat_g = round(0.2 + (i % 5) * 0.32, 2)
        long_g = round(-1.2 if brake > 0 else 0.85, 2)
        inv_temp = round(45.0 + (i * 0.6), 1)
        lines.append(f"{dist},{speed},{front_rpm},{rear_rpm},{throttle},{brake},{lat_g},{long_g},{inv_temp}")
    file_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


# 4. National Highspeed Charging Station Network Stats (CSV, 50 rows)
def generate_charging_network_csv(out_dir: Path) -> Path:
    file_path = out_dir / "National_Highspeed_Charging_Station_Network_Stats.csv"
    headers = "province,expressway_code,service_area_name,operator,total_chargers,ultrafast_800v_chargers,max_power_kw,avg_utilization_rate_pct,fault_rate_pct"
    lines = [headers]
    provinces = ["北京", "上海", "广东", "江苏", "浙江", "山东", "湖北", "四川", "陕西", "河南"]
    operators = ["国家电网 (State Grid)", "特来电 (TELD)", "星星充电 (Star Charge)", "蔚来能源 (NIO Power)", "理想超充 (Li Power)"]
    for i in range(1, 51):
        prov = provinces[(i - 1) % len(provinces)]
        g_code = f"G{(i % 8) + 1}"
        s_name = f"{prov}第{(i % 5) + 1}枢纽服务区"
        op = operators[(i - 1) % len(operators)]
        total = 16 + (i % 8) * 4
        uf = 4 + (i % 4) * 2
        pwr = 480 if "超充" in op else 240
        util = round(42.5 + (i % 10) * 3.8, 1)
        fault = round(0.5 + (i % 4) * 0.3, 2)
        lines.append(f"{prov},{g_code},{s_name},{op},{total},{uf},{pwr},{util},{fault}")
    file_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


# 5. OBD2 DTC Diagnostic Fault Codes Database (CSV, 60 rows)
def generate_obd2_dtc_csv(out_dir: Path) -> Path:
    file_path = out_dir / "OBD2_DTC_Diagnostic_Fault_Codes_Database.csv"
    headers = "dtc_code,subsystem,fault_severity,fault_description_en,fault_description_zh,freeze_frame_trigger,mil_status"
    lines = [headers]
    dtcs = [
        ("P0A0F", "Hybrid Powertrain", "High", "Engine Failed to Start", "增程器起动失败故障", "Crank_RPM < 200 after 5s", "ON"),
        ("P0AA6", "High Voltage Battery", "Critical", "Hybrid Battery Voltage System Isolation Fault", "高压电池母线绝缘阻抗过低", "DC_Isolation < 500 Ohm/V", "FLASH"),
        ("P0C73", "Inverter Cooling", "Medium", "Motor Electronics Coolant Pump 'A' Control Performance", "电机逆变器电动水泵流量不足", "Pump_RPM < 500 when commanded 3000", "ON"),
        ("U0100", "CAN Bus Gateway", "High", "Lost Communication With ECM/PCM 'A'", "与发动机/整车控制器丢失CAN通信", "No_Frame_Received > 500ms", "ON"),
        ("C1203", "Chassis ESP", "Medium", "Steering Angle Sensor Circuit Malfunction", "转向角传感器电路信号超差", "Sensor_Signal_Jump > 45 deg/ms", "ON"),
        ("B1049", "Airbag SRS", "Critical", "Driver Airbag Module Open Circuit", "主驾驶安全气囊回路断路故障", "Squib_Resistance > 4.5 Ohm", "FLASH"),
    ]
    for i in range(1, 61):
        base = dtcs[(i - 1) % len(dtcs)]
        code = f"{base[0]}_{i:02d}"
        lines.append(f"{code},{base[1]},{base[2]},{base[3]} Index {i},{base[4]} 序列{i},{base[5]},{base[6]}")
    file_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


# 6. NIO 150kWh Semi-Solid Battery Discharge Curves (TSV, 40 rows)
def generate_nio_solid_battery_tsv(out_dir: Path) -> Path:
    file_path = out_dir / "NIO_150kWh_Semi_Solid_Battery_Discharge_Curves.tsv"
    headers = "ambient_temp_c\tdischarge_c_rate\tnominal_energy_kwh\tactual_discharge_kwh\tenergy_density_wh_kg\tinternal_resistance_mohm\tmax_temp_rise_c"
    lines = [headers]
    temps = [-20, -10, 0, 15, 25, 35, 45]
    rates = [0.2, 0.5, 1.0, 1.5, 2.0]
    for idx in range(1, 41):
        t = temps[(idx - 1) % len(temps)]
        c = rates[(idx - 1) % len(rates)]
        actual_kwh = round(150.0 * (0.82 if t < 0 else 0.98) * (1.0 - c * 0.03), 1)
        density = round(360.0 * (actual_kwh / 150.0), 1)
        dcir = round(45.0 + (25 - t) * 0.8, 1)
        temp_rise = round(c * 6.5, 1)
        lines.append(f"{t}\t{c}\t150.0\t{actual_kwh}\t{density}\t{dcir}\t{temp_rise}")
    file_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


# 7. Bosch iBooster Gen2 Pedal Force Displacement Map (TSV, 40 rows)
def generate_bosch_ibooster_tsv(out_dir: Path) -> Path:
    file_path = out_dir / "Bosch_iBooster_Gen2_Pedal_Force_Displacement_Map.tsv"
    headers = "pedal_travel_mm\tdriver_pedal_force_n\tbooster_assist_force_n\tmaster_cylinder_pressure_bar\tregen_deceleration_g\thydraulic_deceleration_g\ttime_to_active_ms"
    lines = [headers]
    for idx in range(1, 41):
        travel = round(idx * 1.5, 1)
        force = round(10.0 + idx * 6.2, 1)
        assist = round(force * 4.5, 1)
        press = round(idx * 2.8, 1)
        regen_g = round(min(0.3, idx * 0.015), 3)
        hydro_g = round(max(0.0, (idx - 15) * 0.035), 3)
        ms = round(120.0 - min(80.0, idx * 2.0), 1)
        lines.append(f"{travel}\t{force}\t{assist}\t{press}\t{regen_g}\t{hydro_g}\t{ms}")
    file_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


# ── Structured Text Datasets (JSON, TOML, MD, HTML, RTF) ─────────────────


# 8. Huawei ADS OTA Changelog (JSON)
def generate_huawei_ota_json(out_dir: Path) -> Path:
    file_path = out_dir / "Huawei_ADS_OTA_Changelog_v3_2.json"
    data = {
        "release_version": "ADS_3.2.0_Build_202602",
        "release_date": "2026-02-18",
        "supported_vehicles": ["AITO M9", "Luxeed S7", "Stelato S9", "Avatr 12"],
        "architecture_upgrade": {
            "perception_network": "GOD (General Obstacle Detection) 3.0 全维度通用障碍物网络",
            "planning_network": "PDP (Prediction Decision Planning) 端到端一体化大模型",
            "compute_platform": "MDC 810 (稠密算力 400 TOPS)",
        },
        "feature_enhancements": [
            {
                "module": "城市导航辅助巡航 (City NCA)",
                "enhancements": "全国环岛通行成功率提升至 99.2%，支持无保护左转与极窄机非混行穿行",
                "milestone": "318座城市全覆盖，实现全国有路就能开",
            },
            {
                "module": "代客泊车辅助 (AVP)",
                "enhancements": "支持跨楼层地下车库自主巡航找位，自动识别立体升降机械车位并自动折叠后视镜入库",
                "milestone": "车位到车位 (P-to-P) 领航全程零接管",
            },
            {
                "module": "主动安全主动避让 (eAES)",
                "enhancements": "在 130 km/h 极速下支持刹车与紧急转向边刹边绕行组合避障",
                "milestone": "倒车自适应紧急制动支持后方横穿儿童秒级响应",
            },
        ],
        "ota_update_package_size_mb": 4250.8,
        "md5_checksum": "9f82c3e4a5d6b7c8e9f0123456789abc",
    }
    file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


# 9. Continental Air Suspension ECU Config (TOML)
def generate_continental_suspension_toml(out_dir: Path) -> Path:
    file_path = out_dir / "Continental_Air_Suspension_ECU_Config.toml"
    content = """# 大陆集团 (Continental) 电子空气悬架控制单元 (ASU/ECU) 标定参数
[ecu_info]
module_part_number = "ASU-GEN3-CONT-2026"
software_release = "SW_2.8.1_RC"
supported_vehicle_weight_kg = 2800

[height_profiles]
ingress_egress_offset_mm = -40.0   # 便捷上下车与迎宾模式
normal_ride_height_mm = 0.0        # 标准日常行驶基准零位
sport_speed_lowered_mm = -20.0     # 高速 110km/h 自动下沉降风阻
offroad_high_lift_mm = +60.0       # 越野极限升举模式
max_reservoir_pressure_bar = 16.5  # 高压储气罐额定压力

[pid_damping_parameters]
kp_vertical_accel = 12.50
ki_body_heave = 0.45
kd_roll_pitch = 3.80
sampling_frequency_hz = 1000

[fail_safe_strategy]
leak_detection_threshold_bar_per_min = 0.15
compressor_thermal_shutdown_temp_c = 115.0
emergency_limp_mode_height_mm = -15.0
"""
    file_path.write_text(content.strip(), encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


# 10. Li Auto Owner Warranty Terms (Markdown)
def generate_li_warranty_md(out_dir: Path) -> Path:
    file_path = out_dir / "Li_Auto_Owner_Warranty_Terms_2026.md"
    content = """# 理想汽车 2026 年度整车及三电系统车主保修权益手册

## 1. 核心质量担保范围与有效期限
理想汽车为在中国大陆地区销售的正规授权车辆提供高标准质量保障：

| 担保部件分类 | 基础质保周期 | 终身质保权益专享 (首任车主) | 索赔判定标准 |
| :--- | :--- | :--- | :--- |
| **动力蓄电池总成** | 8 年或 160,000 公里 | 终身质保 (SOH衰减判定) | 质保期内电池容量衰减正常阈值不得低于 70% |
| **前/后驱动电机总成** | 8 年或 160,000 公里 | 终身质保 | 机械内部轴承异响、定子绕组击穿短路 |
| **增程发动机总成** | 5 年或 100,000 公里 | 8 年延长质保 | 气缸磨损、机油渗漏、涡轮增压器非外力损伤 |
| **整车电气及悬挂系统** | 5 年或 100,000 公里 | 5 年官方联保 | 空簧囊体老化漏气、CDC减振器电磁阀故障 |

## 2. 易损零部件明细清单与保修周期
以下易损耗零部件在保修期内出现非外力质量问题由授权零售网点免费更换：
- **雨刮片胶条**：6 个月或 10,000 公里
- **智能钥匙电池**：12 个月（免费上门或门店更换）
- **空气滤清器与空调滤芯**：随首保或 10,000 公里常规保养免费检测

## 3. 保修免责与约束条款
> 法律提示与免责约定：若车辆遭遇水浸事故未在官方 4S 店定损抢修、或经第三方非授权改装高压线束及动力电池者，该损坏部件将无法享受官方联保补偿。
"""
    file_path.write_text(content.strip(), encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


# 11. Tesla Emergency Response Guide (HTML)
def generate_tesla_html(out_dir: Path) -> Path:
    file_path = out_dir / "Tesla_Emergency_Response_Guide_Model_Y.html"
    content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Tesla Model Y First Responder Emergency Response Guide</title>
</head>
<body>
<h1>特斯拉 Model Y 消防员与紧急救援人员应急响应指南 (ERG)</h1>
<p>文件编号: TSLA-ERG-MY-2026 | 适用车型: Tesla Model Y 全系 (上海临港超级工厂制造)</p>

<h2>1. 快速识别与高压危险区域警示</h2>
<p>特斯拉 Model Y 采用 400V 纯电高压架构，高压电缆均包裹有高辨识度的鲜橙色绝缘护套。</p>
<blockquote>危险警告: 橙色高压电缆携带致命直流电压！在完成低压回路断开前，绝不可切割、刺穿或扭曲任何高压组件。</blockquote>

<h2>2. 紧急低压切断回路 (Emergency Low Voltage Cut Loop)</h2>
<p>切断低压回路即可自动切断高压动力电池与驱动电机的继电器吸合，释放蓄能：</p>
<table>
<caption>救援破拆禁区与安全切断位置表</caption>
<thead>
<tr><th>部件位置</th><th>识别标识</th><th>处置操作</th><th>安全确认要求</th></tr>
</thead>
<tbody>
<tr><td>前备箱盖板右侧</td><td>黄色急停剪刀标签</td><td>使用绝缘剪刀直接剪断低压回路硬线</td><td>剪下至少 5cm 线束防止虚接重合</td></tr>
<tr><td>主驾驶车顶B柱内侧</td><td>高压气囊触发线束</td><td>严禁直接切割气囊充气机总成</td><td>佩戴防爆面罩</td></tr>
<tr><td>底盘高压电池包</td><td>铝合金电池壳体</td><td>严禁使用液压顶杆直接顶升电池壳</td><td>举升臂必须对准车身四个圆形举升垫点</td></tr>
</tbody>
</table>

<h2>3. 现场灭火与持续电池水冷监控</h2>
<p>锂离子电池起火需要大量连续水流进行抑制。使用热成像仪持续监测整包温度，直到温度稳定低于 50℃ 并保持至少 24 小时以防二次阴燃。</p>
</body>
</html>
"""
    file_path.write_text(content.strip(), encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


# 12. BMW Workshop Safety Inspection Checklist (RTF)
def generate_bmw_rtf(out_dir: Path) -> Path:
    file_path = out_dir / "BMW_Workshop_Safety_Inspection_Checklist.rtf"
    content = r"""{\rtf1\ansi\ansicpg936\deff0
{\fonttbl{\f0\fnil\fcharset134 Arial;}}
\viewkind4\uc1\pard\lang2052\f0\fs24
BMW 4S Workshop Electric Vehicle Pre-Delivery Safety Inspection Checklist\par
宝马官方售后服务中心纯电车型新车交车前安全检查表 (PDI)\par
\par
文件编号: BMW-PDI-EV-2026-01 | 检验部门: 4S机电车间高压专修班组\par
\par
【检查项目与标准规范】\par
1. 高压动力互锁回路 (HVIL) 阻抗检测: 测量阻抗低于 2.0 Ohm，合格。\par
2. 四轮刹车盘端面圆跳动 (Brake Disc Runout): 前轮实测 < 0.035 mm，合格。\par
3. 车轮铝合金轮毂紧固力矩: 使用校准扭力扳手紧固至 140 N*m，合格。\par
4. 轮胎冷态出厂气压: 前轮 2.4 bar，后轮 2.5 bar，胎压监控复位完成。\par
5. 车载多媒体与高阶辅助驾驶摄像头清洁无污迹，校准完成。\par
\par
质检技师签字: 宝马认证高压技师 张工 | 检验日期: 2026年02月26日\par
}"""
    file_path.write_text(content.strip(), encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


def generate_all_new_data_datasets(out_dir: Path) -> List[Path]:
    """Generate all 7 CSV/TSV and 5 Structured Text documents (Total 12 files)."""
    generators = [
        generate_byd_degradation_csv,
        generate_tesla_supercharger_csv,
        generate_xiaomi_lap_csv,
        generate_charging_network_csv,
        generate_obd2_dtc_csv,
        generate_nio_solid_battery_tsv,
        generate_bosch_ibooster_tsv,
        generate_huawei_ota_json,
        generate_continental_suspension_toml,
        generate_li_warranty_md,
        generate_tesla_html,
        generate_bmw_rtf,
    ]
    results = []
    for g in generators:
        results.append(g(out_dir))
    return results
