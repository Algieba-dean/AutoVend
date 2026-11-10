"""
MIIT (工信部) Vehicle Declaration Platform & National Standards Deconstruction.
Ingests, structures, and provides parameter deconstructions against national standards (GB).
"""

from typing import Any, Dict, List, Optional

from src.truth_engine.models import MIITVehicleDeclaration

NATIONAL_STANDARDS_MAPPING: Dict[str, Dict[str, Any]] = {
    "GB 38031-2020": {
        "title": "电动汽车用动力蓄电池安全要求 (强制性国家标准)",
        "scope": "纯电动与混动车动力蓄电池单体及电池包系统级安全底线",
        "key_mandatory_clause": (
            "电池单体发生热失控后，电池系统在5分钟内不起火不爆炸，为乘员预留安全逃生时间，并发出热事件报警信号。"
        ),
        "engineering_reality_gap": (
            "【去魅说明】：5分钟安全逃生时间是国家法规的'底线及格线'，并不代表电池永远不起火或永不自燃。"
            "同时，现行强标尚未强制要求高速尖锐异物底盘穿刺或重度托底工况。日常高速行驶中若底盘遭遇尖锐角钢或石块直接穿透防护装甲，"
            "瞬间造成多个电芯物理撕裂内短路，仍可能绕过热蔓延隔离层引发快速起火。"
        ),
    },
    "GB 7258-2017": {
        "title": "机动车运行安全技术条件 (强制性国家标准)",
        "scope": "机动车行车制动系统效能、控制系统备份与被动碰撞安全",
        "key_mandatory_clause": (
            "行车制动系必须保证在行车制动管路任何一处失效时，剩余制动效能仍不低于原规定应急制动效能；"
            "线控制动系统必须具备机械、液压或电子备用控制模式。"
        ),
        "engineering_reality_gap": (
            "【去魅说明】：针对网传'刹车踏板踩断/线控刹车失灵踩不动'等恐慌，依据GB 7258标准，"
            "主流线控制动（如博世One-Box IPB）在ECU断电或传感器故障时，内置备用电磁阀会自动断电开启，"
            "将驾驶员脚踩踏板的推力直接通过机械推杆与液压主缸连通至卡钳进行液压制动；"
            "刹车踏板本身采用玻纤增强工程塑料（PA66-GF30）且带碰撞溃缩剪切设计，是国际通行的正面碰撞腿部保护安全设计，并非偷工减料。"
        ),
    },
    "GB/T 18386.1-2021": {
        "title": "电动汽车能量消耗量和续驶里程试验方法 (推荐性国家标准·CLTC工况)",
        "scope": "纯电动轻型汽车CLTC-P工况续航里程与能耗测试基准",
        "key_mandatory_clause": (
            "采用中国汽车行驶工况（CLTC-P），由低速、中速和高速三个速度区间循环组成，累计测试时间1800秒。"
        ),
        "engineering_reality_gap": (
            "【去魅说明】：CLTC测试工况平均车速仅为28.96 km/h，最高车速仅114 km/h且持续仅数秒，"
            "更重要的是怠速/停车等待比例高达22.11%，且标准测试环境温度为23℃±3℃、关闭空调制热。"
            "这导致电车在我国北方冬季（-10℃开暖风）和高速120km/h巡航时，与CLTC标称续航存在巨大物理鸿沟（实测达成率通常仅为50%~65%）。"
        ),
    },
    "GB/T 31498-2021": {
        "title": "电动汽车碰撞后安全要求 (推荐性国家标准)",
        "scope": "纯电/混动车正面、侧面和追尾碰撞后的高压电安全",
        "key_mandatory_clause": (
            "碰撞后高压电路电压必须在4秒内泄放至安全电压（60V以下），绝缘阻抗不低于100Ω/V，电解液无泄漏至乘员舱。"
        ),
        "engineering_reality_gap": (
            "【去魅说明】：碰撞瞬间高压互锁（HVIL）毫秒级切断高压回路是主流合规电车标配，"
            "但用户在选车时还应重点查看防撞梁下部防卷入副防撞梁以及电池包侧向挤压吸能铝合金门槛梁厚度。"
        ),
    },
}


# TOY IMPLEMENTATION: Hardcoded static dictionary of 15 handpicked electric/hybrid models.
# Does NOT connect to any real-time MIIT (工信部) regulatory database or public API.
# In production, replace with real-time web crawlers or official MIIT homologation data feeds.
MIIT_VEHICLE_DATABASE: Dict[str, MIITVehicleDeclaration] = {
    "小米SU7 Ultra": MIITVehicleDeclaration(
        car_model="小米SU7 Ultra",
        product_model_code="BJ7000MBEVP1",
        manufacturer="北京汽车集团越野车有限公司 / 小米汽车",
        curb_weight_kg=2360.0,
        gross_weight_kg=2810.0,
        battery_net_weight_kg=688.0,
        battery_mass_ratio=0.292,
        battery_chemistry="三元锂 (CATL 宁德时代麒麟II代高倍率赛道电芯)",
        battery_system_energy_density_wh_kg=165.0,
        motor_type="前置V6s + 后置双V8s三电机全驱",
        motor_peak_power_kw=1138.0,
        motor_rated_power_kw=350.0,
        rated_to_peak_power_ratio=0.308,
        cltc_energy_consumption_kwh_per_100km=16.5,
        top_speed_kmh=350.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017", "GB/T 18386.1-2021", "GB/T 31498-2021"],
    ),
    "小米SU7 Max": MIITVehicleDeclaration(
        car_model="小米SU7 Max",
        product_model_code="BJ7000MBEVA1",
        manufacturer="北京汽车集团越野车有限公司 / 小米汽车",
        curb_weight_kg=2205.0,
        gross_weight_kg=2655.0,
        battery_net_weight_kg=645.8,
        battery_mass_ratio=0.293,
        battery_chemistry="三元锂 (CATL 宁德时代麒麟电芯)",
        battery_system_energy_density_wh_kg=156.0,
        motor_type="前交流异步感应电机 + 后永磁同步电驱",
        motor_peak_power_kw=495.0,
        motor_rated_power_kw=170.0,
        rated_to_peak_power_ratio=0.343,
        cltc_energy_consumption_kwh_per_100km=13.7,
        top_speed_kmh=265.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017", "GB/T 18386.1-2021", "GB/T 31498-2021"],
    ),
    "小米SU7 Pro": MIITVehicleDeclaration(
        car_model="小米SU7 Pro",
        product_model_code="BJ7000MBEVR3",
        manufacturer="北京汽车集团越野车有限公司 / 小米汽车",
        curb_weight_kg=2090.0,
        gross_weight_kg=2540.0,
        battery_net_weight_kg=608.0,
        battery_mass_ratio=0.291,
        battery_chemistry="磷酸铁锂 (CATL 宁德时代神行电芯 94.3kWh)",
        battery_system_energy_density_wh_kg=138.0,
        motor_type="后置单永磁同步电机",
        motor_peak_power_kw=220.0,
        motor_rated_power_kw=70.0,
        rated_to_peak_power_ratio=0.318,
        cltc_energy_consumption_kwh_per_100km=12.8,
        top_speed_kmh=210.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017", "GB/T 18386.1-2021", "GB/T 31498-2021"],
    ),
    "小米SU7 标准版": MIITVehicleDeclaration(
        car_model="小米SU7 标准版",
        product_model_code="BJ7000MBEVR2",
        manufacturer="北京汽车集团越野车有限公司 / 小米汽车",
        curb_weight_kg=1980.0,
        gross_weight_kg=2430.0,
        battery_net_weight_kg=579.0,
        battery_mass_ratio=0.292,
        battery_chemistry="磷酸铁锂 (FinDreams 弗迪电池电芯 73.6kWh)",
        battery_system_energy_density_wh_kg=132.0,
        motor_type="后置单永磁同步电机",
        motor_peak_power_kw=220.0,
        motor_rated_power_kw=70.0,
        rated_to_peak_power_ratio=0.318,
        cltc_energy_consumption_kwh_per_100km=12.3,
        top_speed_kmh=210.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017", "GB/T 18386.1-2021", "GB/T 31498-2021"],
    ),
    "比亚迪汉EV": MIITVehicleDeclaration(
        car_model="比亚迪汉EV",
        product_model_code="BYD7000BEV1",
        manufacturer="比亚迪汽车工业有限公司",
        curb_weight_kg=2100.0,
        gross_weight_kg=2510.0,
        battery_net_weight_kg=592.0,
        battery_mass_ratio=0.282,
        battery_chemistry="磷酸铁锂 (BYD 刀片电池CTP)",
        battery_system_energy_density_wh_kg=140.0,
        motor_type="前驱永磁同步电机",
        motor_peak_power_kw=180.0,
        motor_rated_power_kw=65.0,
        rated_to_peak_power_ratio=0.361,
        cltc_energy_consumption_kwh_per_100km=13.5,
        top_speed_kmh=185.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017", "GB/T 18386.1-2021"],
    ),
    "比亚迪汉DM-i": MIITVehicleDeclaration(
        car_model="比亚迪汉DM-i",
        product_model_code="BYD7150PHEV1",
        manufacturer="比亚迪汽车工业有限公司",
        curb_weight_kg=1870.0,
        gross_weight_kg=2290.0,
        battery_net_weight_kg=215.0,
        battery_mass_ratio=0.115,
        battery_chemistry="磷酸铁锂 (专用功率型刀片电池)",
        battery_system_energy_density_wh_kg=125.0,
        motor_type="E-CVT插混单电机 + 骁云1.5T阿特金森发动机",
        motor_peak_power_kw=145.0,
        motor_rated_power_kw=70.0,
        rated_to_peak_power_ratio=0.483,
        cltc_energy_consumption_kwh_per_100km=4.2,  # 综合百公里油耗 (L)
        top_speed_kmh=185.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017"],
    ),
    "比亚迪秦PLUS DM-i": MIITVehicleDeclaration(
        car_model="比亚迪秦PLUS DM-i",
        product_model_code="BYD7152PHEV",
        manufacturer="比亚迪汽车工业有限公司",
        curb_weight_kg=1500.0,
        gross_weight_kg=1875.0,
        battery_net_weight_kg=168.0,
        battery_mass_ratio=0.112,
        battery_chemistry="磷酸铁锂 (DM-i功率型刀片电池)",
        battery_system_energy_density_wh_kg=120.0,
        motor_type="单电机插混电驱 + 1.5L阿特金森发动机",
        motor_peak_power_kw=132.0,
        motor_rated_power_kw=60.0,
        rated_to_peak_power_ratio=0.455,
        cltc_energy_consumption_kwh_per_100km=3.8,  # 百公里综合油耗 (L)
        top_speed_kmh=185.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017"],
    ),
    "比亚迪海豹EV": MIITVehicleDeclaration(
        car_model="比亚迪海豹EV",
        product_model_code="BYD7003BEV",
        manufacturer="比亚迪汽车工业有限公司",
        curb_weight_kg=2015.0,
        gross_weight_kg=2425.0,
        battery_net_weight_kg=560.0,
        battery_mass_ratio=0.278,
        battery_chemistry="磷酸铁锂 (CTB电池车身一体化刀片电池)",
        battery_system_energy_density_wh_kg=142.0,
        motor_type="后置永磁同步电驱",
        motor_peak_power_kw=230.0,
        motor_rated_power_kw=80.0,
        rated_to_peak_power_ratio=0.348,
        cltc_energy_consumption_kwh_per_100km=13.0,
        top_speed_kmh=190.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017", "GB/T 18386.1-2021"],
    ),
    "比亚迪海鸥": MIITVehicleDeclaration(
        car_model="比亚迪海鸥",
        product_model_code="BYD7008BEV",
        manufacturer="比亚迪汽车工业有限公司",
        curb_weight_kg=1160.0,
        gross_weight_kg=1535.0,
        battery_net_weight_kg=275.0,
        battery_mass_ratio=0.237,
        battery_chemistry="磷酸铁锂 (刀片电池 30.08kWh / 38.88kWh)",
        battery_system_energy_density_wh_kg=130.0,
        motor_type="前置永磁同步电机",
        motor_peak_power_kw=55.0,
        motor_rated_power_kw=25.0,
        rated_to_peak_power_ratio=0.455,
        cltc_energy_consumption_kwh_per_100km=9.6,
        top_speed_kmh=130.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017", "GB/T 18386.1-2021"],
    ),
    "问界M9 EV": MIITVehicleDeclaration(
        car_model="问界M9 EV",
        product_model_code="SGM7000MBEV",
        manufacturer="赛力斯汽车有限公司",
        curb_weight_kg=2560.0,
        gross_weight_kg=3010.0,
        battery_net_weight_kg=680.0,
        battery_mass_ratio=0.266,
        battery_chemistry="三元锂 (CATL 宁德时代高电压电芯)",
        battery_system_energy_density_wh_kg=152.0,
        motor_type="前交流异步 + 后华为巨鲸永磁同步电机",
        motor_peak_power_kw=390.0,
        motor_rated_power_kw=150.0,
        rated_to_peak_power_ratio=0.385,
        cltc_energy_consumption_kwh_per_100km=17.4,
        top_speed_kmh=200.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017", "GB/T 18386.1-2021"],
    ),
    "问界M9 增程版": MIITVehicleDeclaration(
        car_model="问界M9 增程版",
        product_model_code="SGM6520EREV",
        manufacturer="赛力斯汽车有限公司",
        curb_weight_kg=2560.0,
        gross_weight_kg=3010.0,
        battery_net_weight_kg=320.0,
        battery_mass_ratio=0.125,
        battery_chemistry="三元锂 (CATL 宁德时代 42kWh / 52kWh)",
        battery_system_energy_density_wh_kg=145.0,
        motor_type="前交流异步 + 后永磁同步 + 1.5T四缸增程器",
        motor_peak_power_kw=365.0,
        motor_rated_power_kw=140.0,
        rated_to_peak_power_ratio=0.384,
        cltc_energy_consumption_kwh_per_100km=6.9,  # 综合馈电油耗 (L)
        top_speed_kmh=200.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017"],
    ),
    "问界M7": MIITVehicleDeclaration(
        car_model="问界M7",
        product_model_code="SGM6501EREV",
        manufacturer="赛力斯汽车有限公司",
        curb_weight_kg=2370.0,
        gross_weight_kg=2860.0,
        battery_net_weight_kg=290.0,
        battery_mass_ratio=0.122,
        battery_chemistry="三元锂 / 磷酸铁锂 (CATL 40kWh)",
        battery_system_energy_density_wh_kg=140.0,
        motor_type="单/双电机增程电驱 + 1.5T四缸增程器",
        motor_peak_power_kw=330.0,
        motor_rated_power_kw=130.0,
        rated_to_peak_power_ratio=0.394,
        cltc_energy_consumption_kwh_per_100km=6.85,
        top_speed_kmh=190.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017"],
    ),
    "特斯拉Model 3": MIITVehicleDeclaration(
        car_model="特斯拉Model 3",
        product_model_code="TSL7000BEVBR0",
        manufacturer="特斯拉(上海)有限公司",
        curb_weight_kg=1823.0,
        gross_weight_kg=2255.0,
        battery_net_weight_kg=465.0,
        battery_mass_ratio=0.255,
        battery_chemistry="磷酸铁锂 (宁德时代LFP) / 三元锂 (LG)",
        battery_system_energy_density_wh_kg=128.0,
        motor_type="后置永磁同步电驱",
        motor_peak_power_kw=194.0,
        motor_rated_power_kw=88.0,
        rated_to_peak_power_ratio=0.454,
        cltc_energy_consumption_kwh_per_100km=11.3,
        top_speed_kmh=200.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017", "GB/T 18386.1-2021"],
    ),
    "特斯拉Model Y": MIITVehicleDeclaration(
        car_model="特斯拉Model Y",
        product_model_code="TSL7000BEVBA1",
        manufacturer="特斯拉(上海)有限公司",
        curb_weight_kg=1929.0,
        gross_weight_kg=2415.0,
        battery_net_weight_kg=472.0,
        battery_mass_ratio=0.245,
        battery_chemistry="磷酸铁锂 (宁德时代LFP 60kWh) / 三元锂 (LG 78.4kWh)",
        battery_system_energy_density_wh_kg=130.0,
        motor_type="后置单电机 / 前后双电机全轮驱动",
        motor_peak_power_kw=220.0,
        motor_rated_power_kw=90.0,
        rated_to_peak_power_ratio=0.409,
        cltc_energy_consumption_kwh_per_100km=12.5,
        top_speed_kmh=217.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017", "GB/T 18386.1-2021"],
    ),
    "极氪001": MIITVehicleDeclaration(
        car_model="极氪001",
        product_model_code="MR6500BEV01",
        manufacturer="浙江吉利汽车有限公司",
        curb_weight_kg=2385.0,
        gross_weight_kg=2800.0,
        battery_net_weight_kg=715.0,
        battery_mass_ratio=0.300,
        battery_chemistry="三元锂 (麒麟电池) / 磷酸铁锂 (神行电池)",
        battery_system_energy_density_wh_kg=160.0,
        motor_type="前后双永磁同步电机 (800V碳化硅)",
        motor_peak_power_kw=580.0,
        motor_rated_power_kw=190.0,
        rated_to_peak_power_ratio=0.328,
        cltc_energy_consumption_kwh_per_100km=15.2,
        top_speed_kmh=240.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017", "GB/T 18386.1-2021"],
    ),
    "极氪007": MIITVehicleDeclaration(
        car_model="极氪007",
        product_model_code="MR7000BEV02",
        manufacturer="浙江吉利汽车有限公司",
        curb_weight_kg=2150.0,
        gross_weight_kg=2590.0,
        battery_net_weight_kg=590.0,
        battery_mass_ratio=0.274,
        battery_chemistry="磷酸铁锂 (自研金砖电池 75kWh) / 三元锂 (麒麟 100kWh)",
        battery_system_energy_density_wh_kg=145.0,
        motor_type="全栈800V 高性能碳化硅电驱",
        motor_peak_power_kw=475.0,
        motor_rated_power_kw=160.0,
        rated_to_peak_power_ratio=0.337,
        cltc_energy_consumption_kwh_per_100km=12.5,
        top_speed_kmh=210.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017", "GB/T 18386.1-2021"],
    ),
    "理想L7": MIITVehicleDeclaration(
        car_model="理想L7",
        product_model_code="LXA6500EREV",
        manufacturer="北京理想汽车有限公司",
        curb_weight_kg=2460.0,
        gross_weight_kg=3010.0,
        battery_net_weight_kg=310.0,
        battery_mass_ratio=0.126,
        battery_chemistry="三元锂 (欣旺达/宁德时代 42.8kWh)",
        battery_system_energy_density_wh_kg=145.0,
        motor_type="前后双电机增程电驱 + 1.5T四缸增程器",
        motor_peak_power_kw=330.0,
        motor_rated_power_kw=130.0,
        rated_to_peak_power_ratio=0.394,
        cltc_energy_consumption_kwh_per_100km=7.4,  # 综合馈电油耗 (L)
        top_speed_kmh=180.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017"],
    ),
    "理想L8": MIITVehicleDeclaration(
        car_model="理想L8",
        product_model_code="LXA6510EREV",
        manufacturer="北京理想汽车有限公司",
        curb_weight_kg=2470.0,
        gross_weight_kg=3030.0,
        battery_net_weight_kg=315.0,
        battery_mass_ratio=0.128,
        battery_chemistry="三元锂 (宁德时代 42.8kWh / 52.3kWh)",
        battery_system_energy_density_wh_kg=145.0,
        motor_type="前后双电机增程电驱 + 1.5T四缸增程器",
        motor_peak_power_kw=330.0,
        motor_rated_power_kw=130.0,
        rated_to_peak_power_ratio=0.394,
        cltc_energy_consumption_kwh_per_100km=7.5,
        top_speed_kmh=180.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017"],
    ),
    "理想L9": MIITVehicleDeclaration(
        car_model="理想L9",
        product_model_code="LXA6520EREV",
        manufacturer="北京理想汽车有限公司",
        curb_weight_kg=2520.0,
        gross_weight_kg=3120.0,
        battery_net_weight_kg=360.0,
        battery_mass_ratio=0.143,
        battery_chemistry="三元锂 (宁德时代 52.3kWh)",
        battery_system_energy_density_wh_kg=150.0,
        motor_type="前后双电机智能四驱 + 1.5T增程器",
        motor_peak_power_kw=330.0,
        motor_rated_power_kw=130.0,
        rated_to_peak_power_ratio=0.394,
        cltc_energy_consumption_kwh_per_100km=7.8,
        top_speed_kmh=180.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017"],
    ),
    "小鹏G6": MIITVehicleDeclaration(
        car_model="小鹏G6",
        product_model_code="HMA7000W01BEV",
        manufacturer="广州小鹏汽车科技有限公司",
        curb_weight_kg=1995.0,
        gross_weight_kg=2415.0,
        battery_net_weight_kg=545.0,
        battery_mass_ratio=0.273,
        battery_chemistry="磷酸铁锂 (中创新航 66kWh) / 三元锂 (中创新航 87.5kWh)",
        battery_system_energy_density_wh_kg=145.0,
        motor_type="800V碳化硅高压后驱永磁同步电机",
        motor_peak_power_kw=218.0,
        motor_rated_power_kw=80.0,
        rated_to_peak_power_ratio=0.367,
        cltc_energy_consumption_kwh_per_100km=13.2,
        top_speed_kmh=202.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017", "GB/T 18386.1-2021"],
    ),
    "蔚来ET5": MIITVehicleDeclaration(
        car_model="蔚来ET5",
        product_model_code="NAL7000BSEV1",
        manufacturer="蔚来汽车(安徽)有限公司",
        curb_weight_kg=2160.0,
        gross_weight_kg=2600.0,
        battery_net_weight_kg=535.0,
        battery_mass_ratio=0.248,
        battery_chemistry="三元铁锂 (75kWh标准续航) / 三元锂 (100kWh长续航)",
        battery_system_energy_density_wh_kg=142.0,
        motor_type="前交流感应150kW + 后永磁同步210kW双电机",
        motor_peak_power_kw=360.0,
        motor_rated_power_kw=130.0,
        rated_to_peak_power_ratio=0.361,
        cltc_energy_consumption_kwh_per_100km=14.5,
        top_speed_kmh=200.0,
        relevant_national_standards=["GB 38031-2020", "GB 7258-2017", "GB/T 18386.1-2021"],
    ),
}


class MIITSpecsPlatform:
    """Platform query and parameter deconstructor for public MIIT declaration specs."""

    _instance: Optional["MIITSpecsPlatform"] = None

    @classmethod
    def get_instance(cls) -> "MIITSpecsPlatform":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def find_specs(self, car_model: str) -> Optional[MIITVehicleDeclaration]:
        """Find matching vehicle specs by loose car model name with disambiguation."""
        if not car_model or not isinstance(car_model, str):
            return None
        target = car_model.lower().replace(" ", "").replace("-", "").strip()
        if not target:
            return None

        # 1. Exact cleaned match
        for key, spec in MIIT_VEHICLE_DATABASE.items():
            k_clean = key.lower().replace(" ", "").replace("-", "")
            if target == k_clean:
                return spec

        # 2. Check specific trim tokens (Ultra, Pro, Standard/标准, Max)
        if "ultra" in target:
            for key, spec in MIIT_VEHICLE_DATABASE.items():
                if "ultra" in key.lower() and any(tok in target for tok in ("小米", "su7")):
                    return spec
        if "pro" in target:
            for key, spec in MIIT_VEHICLE_DATABASE.items():
                if "pro" in key.lower() and any(tok in target for tok in ("小米", "su7", "l7", "l8", "l9")):
                    return spec
        if "max" in target:
            for key, spec in MIIT_VEHICLE_DATABASE.items():
                if "max" in key.lower() and any(tok in target for tok in ("小米", "su7", "l7", "l8", "l9")):
                    return spec
        if "标准" in target or "standard" in target:
            for key, spec in MIIT_VEHICLE_DATABASE.items():
                if "标准" in key.lower() and any(tok in target for tok in ("小米", "su7", "3", "y")):
                    return spec

        # 3. Model family & series token matching
        series_tokens = [
            ("海鸥", "比亚迪海鸥"),
            ("海豹", "比亚迪海豹EV"),
            ("秦plus", "比亚迪秦PLUS DM-i"),
            ("秦", "比亚迪秦PLUS DM-i"),
            ("汉dm", "比亚迪汉DM-i"),
            ("汉ev", "比亚迪汉EV"),
            ("汉", "比亚迪汉EV"),
            ("modely", "特斯拉Model Y"),
            ("model3", "特斯拉Model 3"),
            ("m9ev", "问界M9 EV"),
            ("m9增程", "问界M9 增程版"),
            ("m9", "问界M9 EV"),
            ("m7", "问界M7"),
            ("007", "极氪007"),
            ("001", "极氪001"),
            ("l9", "理想L9"),
            ("l8", "理想L8"),
            ("l7", "理想L7"),
            ("su7", "小米SU7 Max"),
            ("g6", "小鹏G6"),
            ("et5", "蔚来ET5"),
        ]
        for token, matched_key in series_tokens:
            if token in target:
                return MIIT_VEHICLE_DATABASE.get(matched_key)

        # 4. Substring bidirectional match
        for key, spec in MIIT_VEHICLE_DATABASE.items():
            k_clean = key.lower().replace(" ", "").replace("-", "")
            if target in k_clean or k_clean in target:
                return spec

        return None

    def extract_model_name_from_text(self, text: str) -> Optional[str]:
        """Extract known vehicle model name from query text."""
        if not text or not isinstance(text, str):
            return None
        lower = text.lower().replace(" ", "").replace("-", "")

        candidates = [
            "小米su7ultra", "小米su7max", "小米su7pro", "小米su7标准版", "小米su7",
            "su7ultra", "su7max", "su7pro", "su7",
            "比亚迪汉dm-i", "比亚迪汉dmi", "比亚迪汉ev", "比亚迪汉", "汉ev", "汉dmi",
            "比亚迪秦plus", "比亚迪秦", "秦plus",
            "比亚迪海豹", "海豹ev", "海豹",
            "比亚迪海鸥", "海鸥",
            "特斯拉modely", "modely", "特斯拉model3", "model3",
            "问界m9ev", "问界m9增程", "问界m9", "问界m7",
            "极氪001", "极氪007",
            "理想l9", "理想l8", "理想l7",
            "小鹏g6", "蔚来et5",
        ]
        for candidate in candidates:
            if candidate in lower:
                spec = self.find_specs(candidate)
                if spec:
                    return spec.car_model
        return None

    def deconstruct_parameters(self, spec: MIITVehicleDeclaration) -> Dict[str, Any]:
        """
        Dismantle MIIT declaration specs:
        - Battery weight burden ratio
        - Peak vs Rated continuous power ratio
        - Regulatory limits vs advertising exaggerations
        """
        analysis = []

        # 1. Battery weight analysis
        battery_ratio = spec.battery_mass_ratio
        if battery_ratio > 0.28:
            analysis.append(
                f"【电池负重警告】：电池总重达 {spec.battery_net_weight_kg:.1f}kg，占整备质量的 {battery_ratio*100:.1f}%。"
                "高自重会导致惯性大、制动距离延长以及轮胎偏磨消耗加速，属于'堆电池换续航'的典型工况。"
            )
        else:
            analysis.append(
                f"【轻量化评估】：电池净重占比 {battery_ratio*100:.1f}%，整车轻量化控制良好。"
            )

        # 2. Motor Rated vs Peak Power
        ratio = spec.rated_to_peak_power_ratio
        if ratio < 0.35:
            analysis.append(
                f"【持续动力热衰减警示】：工信部申报额定持续功率仅为 {spec.motor_rated_power_kw:.1f}kW（仅占峰值功率 {spec.motor_peak_power_kw:.1f}kW 的 {ratio*100:.1f}%）。"
                "营销宣传中的'超跑级大马力'仅能维持数十秒，连续高速140km/h以上狂飙或赛道持续刷圈时，电驱必然因温升限制降额至持续功率。"
            )
        else:
            analysis.append(
                f"【持续动力储备】：持续额定功率占比达 {ratio*100:.1f}%，电机散热与中高速持续超车动力储备较扎实。"
            )

        # 3. National Standards Compliance
        std_notes = []
        for std in spec.relevant_national_standards:
            if std in NATIONAL_STANDARDS_MAPPING:
                info = NATIONAL_STANDARDS_MAPPING[std]
                std_notes.append(f"- **{std} ({info['title']})**: {info['engineering_reality_gap']}")

        return {
            "car_model": spec.car_model,
            "product_code": spec.product_model_code,
            "curb_weight_kg": spec.curb_weight_kg,
            "battery_net_weight_kg": spec.battery_net_weight_kg,
            "battery_mass_ratio_pct": round(spec.battery_mass_ratio * 100, 1),
            "battery_chemistry": spec.battery_chemistry,
            "motor_peak_power_kw": spec.motor_peak_power_kw,
            "motor_rated_power_kw": spec.motor_rated_power_kw,
            "rated_power_ratio_pct": round(spec.rated_to_peak_power_ratio * 100, 1),
            "cltc_energy_consumption": spec.cltc_energy_consumption_kwh_per_100km,
            "top_speed_kmh": spec.top_speed_kmh,
            "analysis_points": analysis,
            "standards_deconstruction": std_notes,
        }

    def format_deconstruction_markdown(self, car_model: str) -> str:
        """Format parameters deconstruction report in user-friendly Markdown."""
        spec = self.find_specs(car_model)
        if not spec:
            return f"⚠️ 暂未查询到【{car_model}】的工信部公示申报数据，建议通过工信部新车申报目录或合格证查阅真实整备质量与额定功率。"

        data = self.deconstruct_parameters(spec)
        lines = [
            f"### 📋 【工信部申报参数与国标拆解】: {data['car_model']} ({data['product_code']})",
            f"- **整备质量 / 电池总质量**: {data['curb_weight_kg']} kg / {data['battery_net_weight_kg']} kg (电池占比: **{data['battery_mass_ratio_pct']}%**)",
            f"- **动力蓄电池类型**: {data['battery_chemistry']}",
            f"- **电机功率标称 vs 真实额定**: 峰值 {data['motor_peak_power_kw']} kW vs 持续额定 **{data['motor_rated_power_kw']} kW** (持续率: **{data['rated_power_ratio_pct']}%**)",
            f"- **申报综合电耗/能耗**: {data['cltc_energy_consumption']} kWh/100km | **最高车速**: {data['top_speed_kmh']} km/h",
            "",
            "#### 🔍 参数抽丝剥茧与工程真相:",
        ]
        for pt in data["analysis_points"]:
            lines.append(f"- {pt}")

        lines.append("")
        lines.append("#### ⚖️ 对应国家标准底线与现实差距:")
        lines.extend(data["standards_deconstruction"])

        return "\n".join(lines)

    def get_national_standards(self) -> Dict[str, Dict[str, Any]]:
        """Return statutory national standards database and real-world engineering gaps."""
        return NATIONAL_STANDARDS_MAPPING

    def get_all_models(self) -> List[str]:
        """Return all cataloged vehicle models in the MIIT database."""
        return list(MIIT_VEHICLE_DATABASE.keys())
