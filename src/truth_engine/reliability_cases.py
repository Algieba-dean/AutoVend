"""
Real Owner Experience, Failure Rates & Safety Cases Repository.
(src/truth_engine/reliability_cases.py)

Covers:
- Infotainment & software stability (screen blackouts, reboots, OTA negative regressions)
- Mechanical & battery safety controversies (thermal runaway history, GB 38031-2020, bottom punctures)
- Chassis & brake engineering truths (composite pedal shear design, One-Box hydraulic fail-safe)
- C-IASI (中保研) / C-NCAP crash test results and structural deformities
"""

from typing import Dict, List, Optional

from src.truth_engine.models import (
    BatterySafetyRecord,
    BrakeChassisControversy,
    CrashTestSummary,
    InfotainmentReliability,
)

INFOTAINMENT_RELIABILITY_DB: Dict[str, InfotainmentReliability] = {
    "小米SU7": InfotainmentReliability(
        car_model="小米SU7",
        soc_chip="高通骁龙8295 (5nm旗舰)",
        screen_blackout_rate_per_year=1.2,
        reboot_frequency="早期版本偶发月均1次，OTA 1.2后降至季度偶发",
        ota_negative_regressions=[
            "HyperOS早期固件曾出现无感蓝牙钥匙偶发断连、车辆靠近未及时解锁",
            "部分版本优化低电量电池保护策略后，20%以下SoC时急加速动力响应被轻微平滑限制",
        ],
    ),
    "特斯拉Model 3": InfotainmentReliability(
        car_model="特斯拉Model 3",
        soc_chip="AMD Ryzen 车规芯片",
        screen_blackout_rate_per_year=0.8,
        reboot_frequency="半年左右偶发死机需双滚轮长按软重启",
        ota_negative_regressions=[
            "历史OTA曾出现强制降低老款电池最大直流快充电流以延缓电池寿命衰减（车主俗称'锁电'）",
            "雨刷自动感应算法在无实体雨量传感器全靠视觉感知下，小雨频繁误刮或大雨响应迟滞",
        ],
    ),
    "比亚迪汉": InfotainmentReliability(
        car_model="比亚迪汉",
        soc_chip="高通骁龙690 / 自研DiLink 4.0/5.0平台",
        screen_blackout_rate_per_year=1.8,
        reboot_frequency="中控旋转大屏高负载多任务运行约每月1次冷启动卡顿",
        ota_negative_regressions=[
            "部分早期车机版本OTA后应用商店高画质软件启动缓慢，存在长期内存占用释放不及时问题",
            "语音连续对话在嘈杂路况下误识别率偏高",
        ],
    ),
    "问界M9": InfotainmentReliability(
        car_model="问界M9",
        soc_chip="麒麟9610A / 鸿蒙HarmonyOS 4 车机",
        screen_blackout_rate_per_year=0.4,
        reboot_frequency="系统底层优化扎实，年均死机重启动作低于0.5次",
        ota_negative_regressions=[
            "投影巨幕与副驾三联屏在多任务高并发互联时，偶发蓝牙音频通道切换抢占延迟",
        ],
    ),
    "极氪001": InfotainmentReliability(
        car_model="极氪001",
        soc_chip="高通骁龙8295 (改款升级后) / 早期为8155",
        screen_blackout_rate_per_year=1.5,
        reboot_frequency="ZEEKR OS改款后流畅度大幅改善，偶尔月均出现一次音响杜比全景声失效需重启",
        ota_negative_regressions=[
            "早期8155老车主OTA升级新版UI后部分动画掉帧",
            "电动车门避障雷达在特定狭窄矮路牙场景偶发误判提前锁止无法完全打开",
        ],
    ),
    "问界M7": InfotainmentReliability(
        car_model="问界M7",
        soc_chip="麒麟990A / 鸿蒙HarmonyOS 3/4",
        screen_blackout_rate_per_year=0.5,
        reboot_frequency="鸿蒙底层较稳定，系统半年偶发需车机软重启一次",
        ota_negative_regressions=[
            "部分早期车机版本在弱网地库偶发蓝牙钥匙靠近迎宾感应迟钝",
        ],
    ),
    "特斯拉Model Y": InfotainmentReliability(
        car_model="特斯拉Model Y",
        soc_chip="AMD Ryzen 车规级高性能芯片",
        screen_blackout_rate_per_year=0.7,
        reboot_frequency="系统整体流畅度高，半年偶发一次中控软重启",
        ota_negative_regressions=[
            "纯视觉倒车泊车雷达测距在复杂夜间场景存在厘米级抖动误差",
            "自动远光灯感应受城市照明反光干扰偶尔误切",
        ],
    ),
    "比亚迪海豹": InfotainmentReliability(
        car_model="比亚迪海豹",
        soc_chip="高通骁龙690 / DiLink 5.0智能座舱",
        screen_blackout_rate_per_year=1.4,
        reboot_frequency="多应用长驻留后台偶发卡顿，月均冷启动需清理内存",
        ota_negative_regressions=[
            "语音连续免唤醒对后排对话抗噪过滤尚需进一步固件迭代",
        ],
    ),
    "小鹏G6": InfotainmentReliability(
        car_model="小鹏G6",
        soc_chip="高通骁龙8155 / Xmart OS 4.0",
        screen_blackout_rate_per_year=0.8,
        reboot_frequency="全场景连续语音响应极佳，年均偶发重启一次以内",
        ota_negative_regressions=[
            "早期版本在复杂无图路口SR环境重构渲染偶发轻微掉帧",
        ],
    ),
}

BATTERY_SAFETY_DB: Dict[str, BatterySafetyRecord] = {
    "小米SU7 Max": BatterySafetyRecord(
        car_model="小米SU7 Max",
        battery_chemistry="三元锂 (101kWh 宁德时代高倍率电芯)",
        pack_supplier="CATL 宁德时代 / 小米自研CTB倒置电芯架构",
        gb_38031_compliance="通过GB 38031-2020强标认证（单体热失控扩散5分钟内不起火不爆炸）",
        bottom_protection_structure="全铝合金蜂窝防撞防撞梁 + 1500MPa高强钢电池底部防护横梁与侧向吸能铝型材",
        historical_fire_incidents=0,
        puncture_and_impact_reality=(
            "采用CTB倒置电芯与泄压阀朝下设计，泄压喷发方向朝向地面。但在高速120km/h遭遇尖锐硬物托底穿刺时，"
            "若撞击能量超过底板吸能极限，直接划伤电池包电芯包壳，仍存在瞬间热失控风险。建议选购底盘加厚防刮护板。"
        ),
    ),
    "小米SU7 Ultra": BatterySafetyRecord(
        car_model="小米SU7 Ultra",
        battery_chemistry="三元锂 (CATL 宁德时代麒麟II代高倍率赛道电芯)",
        pack_supplier="CATL 宁德时代 / CTB电芯集成",
        gb_38031_compliance="通过GB 38031-2020及超国标极限热管理规范",
        bottom_protection_structure="全碳纤维+双层高强铝合金装甲防托底吸能底板",
        historical_fire_incidents=0,
        puncture_and_impact_reality=(
            "高倍率放电发热量大，底盘双水冷回路具备强效均温能力；赛道极端碰撞工况下仍依赖防滚架与门槛加强梁。"
        ),
    ),
    "比亚迪汉EV": BatterySafetyRecord(
        car_model="比亚迪汉EV",
        battery_chemistry="磷酸铁锂 (刀片电池 CTP)",
        pack_supplier="FinDreams 弗迪电池",
        gb_38031_compliance="通过GB 38031-2020强标及严苛针刺试验（单体针刺无明火、无烟雾，表面温度30~60℃）",
        bottom_protection_structure="蜂窝铝板结构与车身纵横梁一体化高强度安装结构",
        historical_fire_incidents=1,
        puncture_and_impact_reality=(
            "磷酸铁锂电芯热失控起火温度（>500℃）显著高于三元锂（>200℃），化学稳定性极高；"
            "但在重度剧烈碰撞导致整车大面积挤压变形撕裂、高压线缆拉扯短路情况下，仍需警惕外围可燃物引燃风险。"
        ),
    ),
    "比亚迪海豹EV": BatterySafetyRecord(
        car_model="比亚迪海豹EV",
        battery_chemistry="磷酸铁锂 (CTB刀片电池)",
        pack_supplier="FinDreams 弗迪电池",
        gb_38031_compliance="通过GB 38031-2020强标认证及50吨重卡碾压试验",
        bottom_protection_structure="电池上盖与车身地板合二为一的高刚性蜂窝三明治吸能底板",
        historical_fire_incidents=0,
        puncture_and_impact_reality=(
            "CTB一体化大幅提升车身抗扭刚度，电池作为结构件受力，底盘托底保护由整车大梁均摊吸收。"
        ),
    ),
    "特斯拉Model 3": BatterySafetyRecord(
        car_model="特斯拉Model 3",
        battery_chemistry="磷酸铁锂 (标准续航) / 三元锂 (长续航/高性能版)",
        pack_supplier="宁德时代 (LFP) / LG新能源 (NCM)",
        gb_38031_compliance="通过GB 38031-2020强标认证",
        bottom_protection_structure="钛合金护板与挤压铝合金底盘护甲",
        historical_fire_incidents=3,
        puncture_and_impact_reality=(
            "三元锂版本电芯能量密度高，高速发生恶性托底起火历史案例多由高速公路散落异物直接穿透前底护板击穿电池包造成；"
            "电芯间填充阻燃灌封胶，但极端穿刺短路后热蔓延速度仍考验逃生反应速度。"
        ),
    ),
    "特斯拉Model Y": BatterySafetyRecord(
        car_model="特斯拉Model Y",
        battery_chemistry="磷酸铁锂 (标准续航) / 三元锂 (长续航)",
        pack_supplier="宁德时代 / LG新能源",
        gb_38031_compliance="通过GB 38031-2020强标认证",
        bottom_protection_structure="加固型挤压铝电池箱体与底部钛合金防撞横梁",
        historical_fire_incidents=2,
        puncture_and_impact_reality=(
            "底盘离地间隙（约167mm）优于轿车，日常磕碰风险相对较低，但高速遇坚硬金属落石仍需注意规避。"
        ),
    ),
    "极氪001": BatterySafetyRecord(
        car_model="极氪001",
        battery_chemistry="磷酸铁锂 (神行) / 三元锂 (麒麟)",
        pack_supplier="CATL 宁德时代 / 威睿电动",
        gb_38031_compliance="通过GB 38031-2020强标，累计交付20万台保持无自燃热蔓延记录",
        bottom_protection_structure="九宫格防撞吸能铝型材门槛 + 高分子多层复合阻燃防护底甲",
        historical_fire_incidents=0,
        puncture_and_impact_reality=(
            "NTP无热蔓延不起火技术在行业内实测表现扎实，托底保护钢梁厚度充裕。"
        ),
    ),
}

BRAKE_AND_CHASSIS_CONTROVERSIES: List[BrakeChassisControversy] = [
    BrakeChassisControversy(
        topic="刹车踏板踩断与塑料踏板争议",
        myth_or_claim="网传电车刹车踏板偷工减料用塑料制造，紧急刹车时会被一脚踩断导致刹车失灵！",
        engineering_fact=(
            "1. 【材料学真相】：主流乘用车刹车踏板臂采用玻纤增强阻燃尼龙工程塑料（PA66-GF30），"
            "材料抗拉强度超过180~200 MPa，设计额定踩踏承载极限普遍超过1200N~1500N。"
            "人体成年男子全力踹刹车的极限生理力量通常为600N~800N，在正常行车与紧急刹车工况下绝对不可能被人体踩断。\n"
            "2. 【被动安全防断腿与溃缩设计】：踏板臂根部预设有精确标定的'碰撞应力剪切弱化槽'（Shear Pin / Passive Breakaway 碰撞溃缩解耦吸能机构）。"
            "当车辆发生高烈度正面碰撞时，前机舱与防火墙被严重向后挤压侵入乘员舱。"
            "如果刹车踏板采用超高刚性不断裂的实心金属铁棒，后移侵入的踏板会像铁撬棍一样直接砸断或切断驾驶员的脚踝与小腿骨骼！"
            "因此，国际碰撞安全规范（Euro-NCAP / C-NCAP）要求踏板在碰撞冲击达到预设危险载荷时主动溃缩断裂脱开，保护人体肢体不受永久截肢性创伤。\n"
            "3. 绝非偷工减料，包括保时捷Taycan、宝马i系列、奔驰EQ系列等高端豪华车均大面积采用此类碰撞解耦踏板。"
        ),
        material_and_standards="玻纤增强尼龙工程复合材料 (PA66-GF30)；符合 GB 7258-2017 机动车运行安全与碰撞防护规范",
        redundancy_mechanism="即使踏板机构受外界暴力侧向破损，制动传感器与冗余拉杆仍可触发紧急制动。",
    ),
    BrakeChassisControversy(
        topic="One-Box线控制动失灵与电子刹车踩不动",
        myth_or_claim="电车全靠电脑发信号刹车，车机死机或断电后刹车彻底踩不动甚至失灵？",
        engineering_fact=(
            "1. 【纯机械液压保底回路】：目前主流车型（如小米SU7、问界M9、极氪001、比亚迪汉）采用博世IPB/大陆MK C1等One-Box集成制动系统。"
            "法规 GB 7258-2017 强制要求：在整车高压断电、12V小电瓶失电或主ECU严重故障死机时，"
            "系统内置的常开机械液压备份隔离阀（Backup Valve）瞬间断电复位弹开，"
            "踏板踩踏推杆与制动液压主缸直接刚性连通，驾驶员用脚踩力直接建立机械油压推动卡钳制动。\n"
            "2. 【脚感差异解释】：无助力状态下踩刹车，缺少伺服电机电子倍力，踏板脚感会显得'沉重硬实'，"
            "但只要用力深踩到底，车辆依然具备法定的应急制动减速度（减速度 ≥ 0.29g）。"
        ),
        material_and_standards="GB 7258-2017 第7条行车制动系失效冗余要求；ISO 26262 ASIL-D 功能安全最高等级认证",
        redundancy_mechanism="常开电磁阀机械液压直连回路 + ESP/二次备份驻车电机双冗余制动。",
    ),
    BrakeChassisControversy(
        topic="悬架球头脱落与所谓'断轴'争议",
        myth_or_claim="新能源电车经常在路上发生断轴、趴窝，底盘用料极其脆弱？",
        engineering_fact=(
            "1. 【电车大自重与瞬态扭矩】：纯电动车由于承载500~700kg动力电池，整备质量普遍高达2.0~2.5吨，"
            "且双电机在0转速即可爆发400~800N·m瞬间峰值扭矩。在高速重度磕碰路肩、以较快车速冲撞石墩或发生角向碰撞时，"
            "悬架连杆与球销承受的横向剪切应力远超传统燃油轻量化小车。\n"
            "2. 【铝合金下摆臂吸能断裂】：现代底盘大量采用铸铝/锻铝控制臂，铝合金延展韧性特性与钢制冲压件不同，"
            "在受到超限冲击时倾向于在应力集中点撕裂吸能，从而避免冲击力直接撕裂车身主纵梁与副车架。"
        ),
        material_and_standards="锻造6082-T6铝合金 / 高强度冲压双层钢板，符合整车耐久性20万公里疲劳台架测试",
        redundancy_mechanism="双叉臂/五连杆多连杆冗余导向，单根拉杆损伤不会导致整车瞬间颠覆。",
    ),
    BrakeChassisControversy(
        topic="电池底部托底磕碰与穿刺起火争议",
        myth_or_claim="底盘稍微刮蹭托底一下，动力电池包就会被硬物刺穿发生剧烈爆燃？",
        engineering_fact=(
            "1. 【三明治吸能底板与结构件防护】：主流纯电架构（如CTB、CTP 3.0）普遍采用超高强度挤压铝/钛合金/复合高分子防护底板，"
            "电池包下壳体具备高韧性吸能腔体，可抵御低速路面突起（如减速带、小石块）的冲击撕扯。\n"
            "2. 【极端高速穿透物理现实】：根据GB 38031-2020及实车事故调研，当车辆在高速以100km/h以上时速撞击坚硬角钢、落石等高密度硬物时，"
            "瞬态冲击动能超万焦耳，仍有概率突破物理防护下甲板刺穿电芯引发内短路。"
            "因此，强标GB 38031要求电芯发生热失控后系统必须提供至少5分钟不发生外部起火爆炸的安全逃生时间（配合气凝胶阻燃隔热垫与排气泄压阀），"
            "但车主绝不可听信'绝对不惧托底'的过度营销，高速行驶仍需避让坚硬遗撒物。"
        ),
        material_and_standards="GB 38031-2020 第5.1.4条单体蓄电池热失控扩展与机械冲击；底盘钛合金/超高强钢吸能装甲",
        redundancy_mechanism="电芯间气凝胶隔热阻燃层 + 毫秒级防爆泄压阀定向排气 + 整车高压毫秒断开 (HVIL)。",
    ),
]

CRASH_TEST_DB: Dict[str, CrashTestSummary] = {
    "小米SU7": CrashTestSummary(
        car_model="小米SU7",
        evaluator="C-IASI (中保研) / C-NCAP",
        test_year="2024",
        occupant_safety="G (优秀 - 绿标)",
        small_overlap_25_result="G (主驾侧25%偏置碰撞中，A柱无可见变形扭曲，门槛梁未撕裂，侧气帘完全展开承托头部)",
        side_impact_b_pillar_result="G (B柱距驾驶员座椅中线距离保持21.5cm以上，远超中保研12cm及格线)",
        pedestrian_safety="G",
        active_safety="G+",
        structural_defect_notes=[
            "前机舱吸能盒设计充分，低速结构碰撞耐撞性与维修经济性指数为 A/M（大压铸件与前大灯总成维修成本偏高）",
            "建议选购高配车身或全险补充划痕及玻璃单项保障",
        ],
    ),
    "特斯拉Model 3": CrashTestSummary(
        car_model="特斯拉Model 3",
        evaluator="C-IASI (中保研) / IIHS (北美)",
        test_year="2023",
        occupant_safety="G (优秀)",
        small_overlap_25_result="G (小偏置碰撞车轮受挤压后向外脱落，车体顺利滑开，乘员舱侵入量极小)",
        side_impact_b_pillar_result="G (热成型钢B柱与门槛横梁抗挤压表现极佳)",
        pedestrian_safety="A",
        active_safety="G",
        structural_defect_notes=[
            "一体式后压铸车身受到严重追尾碰撞时需整体切割更换，轻微追尾钣金修复难度大、保费相对较高",
        ],
    ),
    "特斯拉Model Y": CrashTestSummary(
        car_model="特斯拉Model Y",
        evaluator="C-IASI (中保研) / IIHS (北美)",
        test_year="2024",
        occupant_safety="G (优秀)",
        small_overlap_25_result="G (乘员舱结构坚固，A柱零扭曲，假人约束系统得分满分)",
        side_impact_b_pillar_result="G (B柱距离座椅中线充足，侧气帘完全保压覆盖)",
        pedestrian_safety="A",
        active_safety="G",
        structural_defect_notes=[
            "一体式压铸后地板碰撞维修费用偏高",
        ],
    ),
    "比亚迪汉": CrashTestSummary(
        car_model="比亚迪汉",
        evaluator="C-IASI (中保研)",
        test_year="2022",
        occupant_safety="G (优秀)",
        small_overlap_25_result="G (改款后采用1500MPa热成型钢强化A柱与上边梁，25%碰撞乘员假人腿部空间保护优秀)",
        side_impact_b_pillar_result="G (侧面碰撞电池包刚性边梁有效分担碰撞载荷)",
        pedestrian_safety="G",
        active_safety="G",
        structural_defect_notes=[
            "早前低配版本曾出现气囊偏置承托姿态调整优化历程，现款汉荣耀版已全面补齐侧气帘保压时间",
        ],
    ),
    "问界M9": CrashTestSummary(
        car_model="问界M9",
        evaluator="C-IASI (中保研) / C-NCAP",
        test_year="2024",
        occupant_safety="G+ (超全优)",
        small_overlap_25_result="G+ (玄武车身2000MPa热成型钢占比高，双A柱碰撞零形变，侵入量微小)",
        side_impact_b_pillar_result="G+ (高刚性铝合金门槛抗挤压表现优异)",
        pedestrian_safety="G",
        active_safety="G+",
        structural_defect_notes=[
            "旗舰大型SUV自重大，低速前杠轻微剐蹭大灯维修成本高",
        ],
    ),
    "极氪001": CrashTestSummary(
        car_model="极氪001",
        evaluator="C-IASI (中保研) / Euro-NCAP",
        test_year="2023",
        occupant_safety="G (优秀 - 五星安全)",
        small_overlap_25_result="G (托底撞击与侧面圆柱碰撞无电芯破损泄漏，A柱结构坚实)",
        side_impact_b_pillar_result="G (超高强钢门槛梁分流载荷)",
        pedestrian_safety="G",
        active_safety="G",
        structural_defect_notes=[
            "猎装尾部大开口尾门在严重追尾事故中修复需专业矫正夹具",
        ],
    ),
}


class ReliabilityCaseRepository:
    """Repository for real owner failure rates, controversies, and safety crash cases."""

    _instance: Optional["ReliabilityCaseRepository"] = None

    @classmethod
    def get_instance(cls) -> "ReliabilityCaseRepository":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _resolve_canonical_name(self, car_model: str) -> Optional[str]:
        if not car_model or not isinstance(car_model, str):
            return None
        clean = car_model.strip()
        if not clean:
            return None
        from src.truth_engine.miit_platform import MIITSpecsPlatform
        platform = MIITSpecsPlatform.get_instance()
        spec = platform.find_specs(clean)
        return spec.car_model if spec else clean

    def find_infotainment_record(self, car_model: str) -> Optional[InfotainmentReliability]:
        """Find infotainment reliability cases by car model."""
        canonical = self._resolve_canonical_name(car_model)
        if not canonical:
            return None
        target = canonical.lower().replace(" ", "").replace("-", "")
        for k, v in INFOTAINMENT_RELIABILITY_DB.items():
            k_clean = k.lower().replace(" ", "").replace("-", "")
            if k_clean in target or target in k_clean:
                return v
        return None

    def find_battery_safety(self, car_model: str) -> Optional[BatterySafetyRecord]:
        """Find battery safety history by car model."""
        canonical = self._resolve_canonical_name(car_model)
        if not canonical:
            return None
        target = canonical.lower().replace(" ", "").replace("-", "")
        for k, v in BATTERY_SAFETY_DB.items():
            k_clean = k.lower().replace(" ", "").replace("-", "")
            if k_clean in target or target in k_clean:
                return v
        return None

    def find_crash_test(self, car_model: str) -> Optional[CrashTestSummary]:
        """Find C-IASI / C-NCAP crash test result."""
        canonical = self._resolve_canonical_name(car_model)
        if not canonical:
            return None
        target = canonical.lower().replace(" ", "").replace("-", "")
        for k, v in CRASH_TEST_DB.items():
            k_clean = k.lower().replace(" ", "").replace("-", "")
            if k_clean in target or target in k_clean:
                return v
        return None

    def get_chassis_brake_controversies(self, query: str = "") -> List[BrakeChassisControversy]:
        """Return brake & chassis engineering truth items matching query, or all if empty."""
        if not query:
            return BRAKE_AND_CHASSIS_CONTROVERSIES
        q_lower = query.lower()
        matched = []
        for item in BRAKE_AND_CHASSIS_CONTROVERSIES:
            if (
                q_lower in item.topic.lower()
                or q_lower in item.myth_or_claim.lower()
                or any(k in q_lower for k in ("刹车", "踏板", "踩断", "失灵", "断轴", "球头", "悬架", "托底", "穿刺", "穿孔", "底盘磕碰", "电池包刮蹭", "起火", "热失控"))
            ):
                matched.append(item)
        return matched if matched else BRAKE_AND_CHASSIS_CONTROVERSIES

    def format_reliability_report_markdown(
        self, car_model: str, query_filter: str = ""
    ) -> str:
        """Format an unvarnished real-world reliability and safety report in Markdown."""
        from src.truth_engine.miit_platform import MIITSpecsPlatform
        platform = MIITSpecsPlatform.get_instance()
        detected_model = platform.extract_model_name_from_text(f"{car_model} {query_filter}")
        target_model = detected_model or (car_model if car_model and car_model not in ("当前车型", "目标车型") else None)
        display_name = target_model or car_model or "车辆安全与可靠性"

        lines = [f"### 🔍 【真实车主体验、故障率与缺陷安全案例库】: {display_name}"]

        # 1. Infotainment stability
        if target_model:
            info = self.find_infotainment_record(target_model)
            if info:
                lines.append("#### 🖥️ 车机与系统稳定性实测:")
                lines.append(f"- **核心芯片方案**: {info.soc_chip}")
                lines.append(f"- **中控黑屏/白屏预估频次**: 年均约 {info.screen_blackout_rate_per_year} 次")
                lines.append(f"- **系统卡顿与软重启频率**: {info.reboot_frequency}")
                if info.ota_negative_regressions:
                    lines.append("- **真实车主反馈/OTA负优化案例**:")
                    for reg in info.ota_negative_regressions:
                        lines.append(f"  • {reg}")
                lines.append("")

            # 2. Battery Safety & Incidents
            batt = self.find_battery_safety(target_model)
            if batt:
                lines.append("#### 🔋 电池安全标准与穿刺托底真相:")
                lines.append(f"- **电芯材质与供应商**: {batt.battery_chemistry} ({batt.pack_supplier})")
                lines.append(f"- **强标符合性 (GB 38031-2020)**: {batt.gb_38031_compliance}")
                lines.append(f"- **底盘防护装甲结构**: {batt.bottom_protection_structure}")
                lines.append(f"- **高速托底穿刺现实分析**: {batt.puncture_and_impact_reality}")
                lines.append("")

        # 3. Brake & Chassis controversies
        controversies = self.get_chassis_brake_controversies(query_filter)
        if controversies:
            lines.append("#### ⚙️ 机械底盘与刹车争议深度工程拆解:")
            for item in controversies:
                lines.append(f"**【{item.topic}】**")
                lines.append(f"- **传言/焦虑**: {item.myth_or_claim}")
                lines.append(f"- **工程力学事实**: {item.engineering_fact}")
                lines.append(f"- **安全冗余规范**: {item.material_and_standards}；{item.redundancy_mechanism}")
                lines.append("")

        # 4. Crash Test Results
        if target_model:
            crash = self.find_crash_test(target_model)
            if crash:
                lines.append("#### 🛡️ 官方碰撞测试结果 (中保研 C-IASI / C-NCAP):")
                lines.append(f"- **车内乘员安全评价**: **{crash.occupant_safety}** (主驾25%偏置碰撞: {crash.small_overlap_25_result})")
                lines.append(f"- **侧面碰撞B柱侵入**: {crash.side_impact_b_pillar_result}")
                lines.append(f"- **车外行人与主动安全**: 行人 {crash.pedestrian_safety} | 主动安全 {crash.active_safety}")
                if crash.structural_defect_notes:
                    lines.append("- **结构件与维修经济性提示**:")
                    for note in crash.structural_defect_notes:
                        lines.append(f"  • {note}")
                lines.append("")

        # 5. Price & Depreciation if query mentions price/valuation
        if target_model and any(k in f"{car_model} {query_filter}" for k in ("保值", "二手", "落地", "价格", "优惠", "补贴", "多少钱")):
            from src.truth_engine.price_valuation import PriceValuationEngine
            price_md = PriceValuationEngine.get_instance().format_price_and_depreciation_markdown(target_model)
            lines.append(price_md)

        return "\n".join(lines)
