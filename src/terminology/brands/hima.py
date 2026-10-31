"""
HIMA (Huawei / AITO / Luxeed / Stelato / Maextro) Proprietary Automotive Technology Registry
(src/terminology/brands/hima.py).
Contains 30 comprehensive proprietary technologies for Huawei / HIMA.
"""

from typing import List

from src.terminology.schemas import (
    EquivalenceDomain,
    TechCategory,
    TechMaturity,
    TechnologyEntity,
)

HIMA_TECHNOLOGIES: List[TechnologyEntity] = [
    # 1. 华为乾崑智驾 ADS 3.0 系统 (Original)
    TechnologyEntity(
        id="hima_ads",
        name="华为乾崑智驾 ADS 3.0 系统",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HUAWEI Qiankun ADS 3.0 Autonomous Driving System",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="端到端高阶智能驾驶网络",
        aliases=[
            "乾崑智驾",
            "乾崑",
            "乾昆",
            "乾昆智驾",
            "乾坤",
            "乾坤智驾",
            "华为ads",
            "ads3.0",
            "ads 3.0",
            "ads 2.0",
            "ads2.0",
            "huawei ads",
            "华为智驾",
            "无图智驾",
            "车位到车位",
            "泊车代驾",
            "god网络",
            "pdp网络",
        ],
        summary="华为全栈自研高阶智能驾驶系统，采用GOD感知网络与PDP预测决策规控端到端大模型架构，支持全国城市无图领航辅助与车位到车位全场景贯通。",
        description=(
            "乾崑智驾ADS 3.0（原HUAWEI ADS高阶智能驾驶系统）是行业公认的顶级智驾系统。采用领先的激光雷达、毫米波雷达与高清视觉多模态融合感知，"
            "首创GOD（General Obstacle Detection）通用障碍物网络，能识别并避开各类未知异形障碍物；PDP预测决策规控网络实现了类似人类老司机的防御性驾驶行为，"
            "支持环岛、掉头、狭窄闸机通行及跨楼层代客泊车（AVP）。"
        ),
        technical_principles=[
            "多传感器融合（192线高精激光雷达 + 4D毫米波 + 高清视觉）",
            "GOD大网完成未知异形物体精准体素化构建（不仅认得白名单，更认得白名单外的翻水马、滚石、落物）",
            "端到端类人智驾算法架构与全向防碰撞系统CAS 3.0（超强AEB紧急制动）",
        ],
        advantages=[
            "全国无图都能开，提车即可用，有路就能开",
            "全向防碰撞CAS 3.0刹停速度业界领先（最高支持120km/h甚至130km/h紧急刹停）",
            "支持车位到车位一键启动，全程无需接管地下地库闸机与园区通道",
        ],
        limitations=[
            "全套高阶硬件选装成本较高（激光雷达高阶包需选配或购车权益抵扣）",
            "在极端恶劣暴雨暴雪或浓雾天气下，系统传感器受物理遮挡仍提示驾驶员主动接管",
        ],
        sub_variants={
            "ADS SE (基础版)": "纯视觉方案，支持高速导航辅助驾驶与智能泊车",
            "ADS 高阶版 (ADS 3.0)": "配备激光雷达，支持全国城市领航NCA、代客泊车及全向防碰撞CAS 3.0",
        },
        representative_vehicles=["问界M9", "问界M7", "问界M5", "智界S7", "智界R7", "享界S9", "阿维塔11/12"],
        standard_labels=["全场景端到端智驾", "全国无图NCA", "激光雷达高阶智驾", "全向防碰撞CAS", "车位到车位智驾"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "安全是最大的豪华：向客户现场展示全向防碰撞AEB与倒车防穿插的真人实测成绩；",
            "对比其他需高精地图的竞品，强调华为在三四线城市及县道乡道同样具备成熟的领航接管率优势。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 2. 华为途灵智能底盘 (Original)
    TechnologyEntity(
        id="hima_tuling",
        name="华为途灵智能底盘",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HUAWEI Tuling Intelligent Chassis Platform",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="多模态感知预瞄与多域协同自适应底盘",
        aliases=[
            "途灵",
            "途灵底盘",
            "图灵底盘",
            "图灵",
            "华为途灵",
            "tuling",
            "tuling chassis",
            "dats",
            "xmotion",
        ],
        summary="华为自研的感知融合智能底盘，通过多模态路面预瞄、HUAWEI DATS动态自适应扭矩控制与xMotion智能车身协同控制，实现如履平地的魔毯般滤震。",
        description=(
            "途灵底盘以多维感知、智能控制和机械底盘三位一体构筑，集成全铝合金双叉臂五连杆悬架、闭式空气悬架与CDC电控减振器。"
            "利用前置激光雷达与双目摄像头提前扫描前方路面起伏（减速带、坑洼），提前数十毫秒主动调节阻尼硬度与扭矩分配，实现“颠簸不颠、过弯不晃”。"
        ),
        technical_principles=[
            "多模态路面预瞄：激光雷达/摄像头以每秒数十次刷新率预瞄前方15米路面微小高差",
            "HUAWEI DATS（动态自适应扭矩系统）：电机端毫秒级微调扭矩抑制打滑与纵向顿挫",
            "HUAWEI xMotion：智能车身协同调度电机、制动、悬架与转向多域联动",
        ],
        advantages=[
            "过减速带及坑洼路段车身起伏大幅减小，滤震细腻高级",
            "结冰或湿滑湿滑路面起步不甩尾、不打滑，过弯支撑性强",
            "闭式空簧升降速度比传统开式空簧快40%，能耗更低",
        ],
        limitations=[
            "夜间超远距离或完全无照明极端无反光路面，光学预瞄精度可能降低为惯性传感器响应",
        ],
        sub_variants={},
        representative_vehicles=["问界M9", "智界S7", "智界R7", "享界S9"],
        standard_labels=["智能预瞄底盘", "多模态路况识别", "HUAWEI DATS动态扭矩", "闭式空气悬架+CDC", "车身姿态协同调度"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "向追求豪华行政乘坐质感的客户推荐，重点说明“先知后觉”的预瞄调节：比传统车轮碾上坑洼后才被动减震的底盘高级得多。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 3. 华为巨鲸 800V 高压电池平台 (Original)
    TechnologyEntity(
        id="hima_whale_800v",
        name="华为巨鲸 800V 高压电池平台",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HUAWEI Whale 800V High-Voltage Battery Platform",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="高压碳化硅超充电池体系",
        aliases=[
            "巨鲸",
            "巨鲸800v",
            "巨鲸电池",
            "华为巨鲸",
            "whale 800v",
            "800v巨鲸",
            "800v",
            "800v架构",
            "800v高压平台",
            "华为800v",
        ],
        summary="鸿蒙智行纯电车搭载的超薄高安全800V高压电池平台，电芯具备超薄云母隔热层与超强底部防护，充电5分钟即可补能超215公里。",
        description=(
            "巨鲸800V高压电池平台采用业界顶尖的超薄电芯设计，电池包厚度仅为行业领先水平，有效释放轿车内部垂向空间。"
            "全栈支持华为全液冷超充网络（最大600kW），配备电池五星级热安全防护与底部超强玄武防撞装甲。"
        ),
        technical_principles=[
            "全高压碳化硅电驱与高能量密度三元锂/磷酸铁锂高压体系",
            "云母多层防火绝缘屏障与10层硬核物理防撞抗撕裂结构",
        ],
        advantages=[
            "补能速度极快，匹配华为液冷超充桩体验如加油般迅速",
            "极薄电池包设计，后排乘坐不顶头、不窝腿",
        ],
        limitations=[
            "需依赖高电压桩才能发挥超高功率充电曲线",
        ],
        sub_variants={},
        representative_vehicles=["智界S7", "享界S9", "智界R7"],
        standard_labels=["800V巨鲸高压平台", "超薄高安全电池包", "液冷超充", "极速补能"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "结合全国华为全液冷超充站布局（一秒一公里），打消长途跨省纯电出行顾虑。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 4. HarmonyOS 智能座舱系统 (Original)
    TechnologyEntity(
        id="hima_harmonyos",
        name="HarmonyOS 智能座舱系统",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HarmonyOS Smart Cockpit",
        category=TechCategory.COCKPIT_OS,
        subcategory="分布式全场景万物互联车机系统",
        aliases=[
            "鸿蒙座舱",
            "harmonyos",
            "鸿蒙系统",
            "harmonyos座舱",
            "华为车机",
            "超级桌面",
            "小艺助手",
        ],
        summary="被誉为行业车机天花板的智能座舱系统，依托鸿蒙分布式软总线，实现手机/手表/平板与车机的无缝无感流转、秒级响应和自然语音全车控。",
        description=(
            "HarmonyOS智能座舱具有行业领先的触控流畅度和UI美学设计。支持华为手机无感碰一碰导航接力、超级桌面无缝运行百万手机应用、"
            "后排HUAWEI MagLink拓展坞吸附平板自动变身为车载副驾/后排娱乐屏，配合盘古大模型驱动的小艺车载助手，支持多音区免唤醒拟人化交互。"
        ),
        technical_principles=[
            "分布式软总线与原子化服务框架",
            "零层级交互卡片设计与底层ArkCompiler方舟引擎极致优化",
        ],
        advantages=[
            "车机跟手度与帧率极其丝滑稳定，长期使用不卡顿",
            "手机应用生态与导航无缝上车，无需上车重新设置支架看手机",
            "多屏协同与后排儿童关怀生态极其完善",
        ],
        limitations=[
            "对苹果iOS或非华为生态手机用户而言，部分超级桌面互联功能体验略受限制",
        ],
        sub_variants={},
        representative_vehicles=["问界M5", "问界M7", "问界M9", "智界S7", "智界R7", "享界S9"],
        standard_labels=["鸿蒙智能座舱", "分布式多设备协同", "车机流畅度天花板", "超级桌面跨端流转"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "向科技数码用户现场演示手机导航靠近车辆自动转到大屏、后排平板协同看动画的温情场景。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 5. 尊界超豪华整车平台架构 (Maextro) (Original)
    TechnologyEntity(
        id="hima_maextro_platform",
        name="尊界超豪华整车平台架构 (Maextro)",
        brand="鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HIMA Maextro Ultra-Luxury Architecture",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="百万级超豪华行政底盘与整车平台",
        aliases=[
            "尊界",
            "尊界s800",
            "尊界平台",
            "途灵龙行底盘",
            "龙行底盘",
            "龙行平台",
            "龙行",
            "maextro",
            "尊界底盘",
            "鸿蒙智行尊界",
            "maextro s800",
            "江淮尊界",
        ],
        summary="华为与江淮联合打造的鸿蒙智行第四界（尊界 Maextro）百万级超豪华整车平台，搭载旗舰级途灵龙行全主动数字底盘、全轮线控转向与华为乾崑智驾ADS 3.0全维度安全矩阵。",
        description=(
            "尊界（Maextro）定位百万级超高端豪华行政旗舰（首款车型为尊界S800，车长超5.4米）。"
            "搭载鸿蒙智行顶规‘途灵龙行底盘’，集成了智能双腔空气悬架、超低延迟连续阻尼控制、全轮主动转向及全线控动力底盘一体化协调系统。"
            "车身采用高刚度潜艇级笼式太空舱，并配备全维主动防碰撞CAS 3.0，实现车位到车位全场景无缝端到端智能领航，"
            "在行政级乘坐舒适度、静谧性、防晕车与极致尊贵气场上全面对标迈巴赫与劳斯莱斯。"
        ),
        technical_principles=[
            "途灵龙行全数字智慧底盘与多传感器纳秒级预瞄主动阻尼与转角协调",
            "全向防碰撞CAS 3.0全场景主动避险算法（前后向、侧向、悬空目标全面拦截）",
            "全域全场景鸿蒙万物互联智舱与星环座舱多模态拟人感知交互",
        ],
        advantages=[
            "超5.4米宏伟行政车长具备媲美中型车的敏捷掉头与动态稳定性（全轮主动转向）",
            "国宾级平稳乘坐感：龙行底盘毫秒级吸收一切颠簸震动，后排贵宾如履平地",
            "顶级智驾与全向主动安全护航，提供极致尊贵、安全与尊荣感",
        ],
        limitations=[
            "定位百万级超豪华市场，整车售价与购置成本高，面向超高净值商务领袖群体",
        ],
        sub_variants={
            "尊界S800行政豪华版": "四座全景星空行政后舱旗舰",
        },
        representative_vehicles=["尊界S800"],
        standard_labels=["尊界", "Maextro", "途灵龙行底盘", "百万级旗舰", "全轮转向", "国宾级行政座驾"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "向追求顶奢地位、对标迈巴赫/劳斯莱斯的超高端商务领袖介绍：‘尊界S800是真正的中国汽车工业豪华天花板，5.4米车身气场非凡，途灵龙行底盘带来国宾级的从容平稳；’",
            "突出科技豪华与华为全栈黑科技（乾崑智驾+鸿蒙生态）带来的划时代尊享体验。",
        ],
        maturity=TechMaturity.PRE_RESEARCH,
    ),

    # 6. 鸿蒙智行玄武车身安全架构 (Original)
    TechnologyEntity(
        id="hima_xuanwu_body",
        name="鸿蒙智行玄武车身安全架构",
        brand="鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HIMA Xuanwu High-Strength Body Architecture",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="潜艇级超高强钢与一体化防护车身",
        aliases=[
            "玄武车身",
            "玄武架构",
            "鸿蒙玄武车身",
            "问界玄武车身",
            "xuanwu body",
            "玄武安全车身",
            "玄武结构",
        ],
        summary="鸿蒙智行旗舰车型采用的顶级车身被动安全架构，以2000MPa潜艇级超高热成型钢、一体化压铸后地板及五层安全防护体系构筑‘硬核堡垒’。",
        description=(
            "玄武车身架构以‘安全是最大的豪华’为宗旨打造。A柱、B柱、车门防撞梁等关键承载受力部位采用2000MPa潜艇级热成型高强钢，"
            "全车铝合金与高强钢占比达80%以上，整车扭转刚度突破40000 N·m/deg。"
            "后地板采用大型一体化高压铸造铝合金结构，减少数百个零部件与焊接点，消除断裂风险；"
            "并配合下车体十宫格吸能铝合金门槛梁与五层动力电池底部装甲防撞防护，抵御严重追尾或侧柱碰侵入。"
        ),
        technical_principles=[
            "2000MPa潜艇级热成型钢闭环笼式乘员舱骨架",
            "一体化高压压铸后地板结构与十宫格挤压铝防撞门槛梁",
            "多载荷路径协同分散碰撞力设计，保障乘员舱零结构侵入变形",
        ],
        advantages=[
            "顶级被动碰撞安全：在卡车前后夹击恶劣测试中A柱B柱零变形，全车车门自动解锁可正常打开",
            "高抗扭刚度彻底杜绝车身走烂路异响，极大改善底盘静谧性与操控一体感",
        ],
        limitations=[
            "超高强度钢与大型压铸件使用比例极高，生产制造成本与专用冲压模具成本极高",
        ],
        sub_variants={
            "玄武车身旗舰版": "问界M9、享界S9搭载的全铝一体压铸+2000MPa钢骨架",
        },
        representative_vehicles=["问界M9", "享界S9", "智界R7"],
        standard_labels=["玄武车身", "2000MPa高强钢", "一体化压铸", "安全是最大的豪华", "卡车夹击零变形", "五层防护"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "面对全家出行、最看重家人生命安全的父母客户：‘网上大量真实碰撞视频见证，大货车追尾夹击，问界M9的玄武车身硬扛两辆重卡，乘员舱A柱完好无损、车门一把拉开，买车买的就是家人的命！’",
            "强调潜艇级2000MPa钢材与全铝一体压铸带来的扎实质感，彻底打消对电车骨架单薄的传统偏见。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 7. HUAWEI DATS 动态自适应扭矩系统
    TechnologyEntity(
        id="hima_dats",
        name="华为 DATS 动态自适应扭矩系统",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HUAWEI DATS Dynamic Adaptive Torque System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="毫秒级电机端防滑与舒适减振控制",
        aliases=[
            "dats",
            "dats系统",
            "华为dats",
            "动态自适应扭矩",
            "防颠簸扭矩控制",
        ],
        summary="华为首创将防滑控制深度移至电机端内部，响应时延从传统ESP的100ms缩减至4ms，大幅消除颠簸与防晕车。",
        description=(
            "传统防滑系统依靠底盘ESP通过CAN总线发信号，链路长延迟大。DATS系统由电机控制器直接感知轮端转速微波动，"
            "4毫秒内自适应回调扭矩，实现过颠簸路面车身纵向晃动减小43%，转弯侧倾减小25%，极大提升家人防晕车舒适感。"
        ),
        technical_principles=[
            "电机转子旋变传感器闭环实时微步监测",
            "微秒级驱动电机正负双向力矩毫秒调节",
        ],
        advantages=[
            "响应速度比传统机械ESP快25倍，湿滑结冰路面起步丝滑不打滑",
            "颠簸路面如履平地，后排乘员晕车感大幅消除",
        ],
        limitations=[
            "依赖华为DriveONE高精度电驱动系统软硬件闭环支持",
        ],
        sub_variants={"DATS 2.0": "智界S7/问界M9搭载，增加纵横协同控制与舒适过弯模式"},
        representative_vehicles=["问界M5", "问界M7", "问界M9", "智界S7", "智界R7"],
        standard_labels=["DATS", "4ms极速响应", "防滑控制", "防晕车", "电机端控制"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "向怕晕车的乘客和家属介绍：‘DATS直接在电机里4毫秒调扭矩，过减速带车身不颠，刹车过弯不晃，老人坐车再也不晕车！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 8. 华为 DriveONE 全液冷超充与黄金动力总成
    TechnologyEntity(
        id="hima_driveone_800v",
        name="华为 DriveONE 高压碳化硅黄金动力总成",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HUAWEI DriveONE 800V SiC High-Efficiency Powertrain",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="高压碳化硅扁线油冷电驱总成",
        aliases=[
            "driveone",
            "华为driveone",
            "华为电机",
            "华为电驱",
            "碳化硅driveone",
            "22000转电机",
        ],
        summary="华为全栈自研高压碳化硅电驱动平台，电机最高转速突破22000rpm，最高效率高达98%，带来强劲推背感与极致超低电耗。",
        description=(
            "融合电机、MCU控制器、减速箱三合一设计，采用自研高耐压第三代SiC功率芯片与扁线绕组智能定子油冷。"
            "单电机功率高达390kW，前后双电机综合马力超496PS，百公里加速3秒级，高速120km/h以上再加速超车源源不断。"
        ),
        technical_principles=[
            "定子智能离心喷淋油冷与转子空心轴内冷",
            "低谐波高压脉宽调制SVPWM控制算法，电机静音NVH极优",
        ],
        advantages=[
            "电控综合效率达98%行业标杆，百公里电耗低至12-14kWh",
            "极致静谧，车速跑上120km/h几乎听不到传统电车的电机电磁高频啸叫",
        ],
        limitations=[
            "碳化硅高规格器件制造成本高于普通IGBT",
        ],
        sub_variants={},
        representative_vehicles=["智界S7", "问界M9纯电版", "享界S9", "阿维塔12"],
        standard_labels=["DriveONE", "22000rpm电机", "全栈SiC", "98%最高效率", "超低电耗", "静音电驱"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向追求动力与安静的用户推荐：‘华为造通信基站的顶级功力来造电驱，22000转超级电机，车里听不见一点电磁噪音，安静又有力！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 9. 华为 192 线超高精度车规级激光雷达
    TechnologyEntity(
        id="hima_laser_lidar_192",
        name="华为 192 线车规级超高精度激光雷达",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HUAWEI 192-Line Automotive-Grade Ultra-High Precision LiDAR",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="高线束远距离三维环境激光点云感知",
        aliases=[
            "192线激光雷达",
            "华为激光雷达",
            "192线雷达",
            "问界激光雷达",
            "超远距激光雷达",
        ],
        summary="业内量产最高线束车规级激光雷达，点频达180万点/秒，探测距离达250米，连掉落的轮胎碎皮和小纸箱都能毫秒看清。",
        description=(
            "由华为自主研发的192线混合固态激光雷达，线束密度和角分辨率达到业内顶尖水平。"
            "每秒发射180万个激光脉冲，能在250米外精准识别小狗、倒地树枝、黑色水马及夜间未开灯故障车，为高阶智驾提供全天候物理级三维眼睛。"
        ),
        technical_principles=[
            "1550nm/905nm混合固态高频扫描架构",
            "自研高灵敏度SPAD阵列光电探测芯片与微秒级时间数字转换",
        ],
        advantages=[
            "点云极其密集成像如照片般清晰，彻底消除视觉纯相机在强光逆光下的致盲风险",
            "夜间完全无路灯无月光极端黑暗下，感知能力不受丝毫影响",
        ],
        limitations=[
            "激光雷达位于车顶正上方，洗车时需注意避免硬刷毛猛烈刮擦镜头保护罩",
        ],
        sub_variants={},
        representative_vehicles=["问界M9", "智界S7", "享界S9", "智界R7"],
        standard_labels=["192线激光雷达", "180万点频", "250米探测距离", "夜间安全", "微小障碍物识别"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "对比友商百线雷达或纯视觉：‘普通车看路是近视眼，华为192线雷达相当于给车戴上了超高清夜视望远镜，哪怕200米外黑夜里掉了个轮胎皮都能提前刹停！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 10. 华为全向防碰撞系统 CAS 3.0
    TechnologyEntity(
        id="hima_cas_active_safety",
        name="华为全向防碰撞系统 (CAS 3.0)",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HUAWEI Collision Avoidance System (CAS 3.0)",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="前向侧向后向全维度主动紧急避险",
        aliases=[
            "cas3.0",
            "cas 3.0",
            "全向防碰撞",
            "华为aeb",
            "倒车防碰撞",
            "全向主动安全",
            "超强aeb",
        ],
        summary="全维度主动安全防碰撞体系，支持最高120km/h甚至130km/h静止车刹停，前向、侧向抗横穿、后向倒车防误踩油门全向守护。",
        description=(
            "CAS 3.0（Collision Avoidance System）将前向AEB制动时速上限推升至130km/h，首创ESA紧急转向避险辅助（制动无法刹停时自主借道绕行）；"
            "具备侧向主动避障防夹击，以及后向低速防误踩电门倒车撞人，实现360度全时主动被动闭环安全。"
        ),
        technical_principles=[
            "多传感器时空多维联合前向目标轨迹预估",
            "ESA紧急转向算法与途灵底盘ESP制动系统毫秒级联合介入",
        ],
        advantages=[
            "无数真实碰撞视频证实：大货车追尾、鬼探头行人、夜间故障车多次实战全自动成功避险",
            "彻底避免由于把油门当刹车误踩导致的惨烈事故",
        ],
        limitations=[
            "超出物理附着力极限（如极滑光冰路面或距离小于几米极端恶意切入）仍受物理制动极限约束",
        ],
        sub_variants={},
        representative_vehicles=["问界M9", "问界M7", "享界S9", "智界R7"],
        standard_labels=["CAS 3.0", "130km/h刹停AEB", "全向防碰撞", "ESA紧急避险", "安全天花板"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向每一个重视家庭安全的客户强调：‘网上无数行车记录仪实测视频，关键时刻华为全向防碰撞主动刹停避险，拯救了成百上千个家庭，买车买的就是家人的平安！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 11. HUAWEI SOUND 卓越级车载空间音频系统
    TechnologyEntity(
        id="hima_sound_system",
        name="HUAWEI SOUND 卓越级车载声学系统",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HUAWEI SOUND Premier Automotive Acoustic System",
        category=TechCategory.COCKPIT_OS,
        subcategory="25单元多声道全景声智慧声学",
        aliases=[
            "huawei sound",
            "华为音响",
            "卓越级音响",
            "星环散射体",
            "头枕独立音响",
            "空间音频",
        ],
        summary="配备最高25个专业声学单元、2080W超大功放与星环散射体，支持7.1.4杜比全景声与独立私密头枕音响。",
        description=(
            "由华为德国施密特声学实验室深度调校，配备中控台标志性‘星环散射体’高音发散单元，"
            "主驾头枕配备双独立私密扬声器，导航语音与车主电话仅司机一人能听见，后排家人听音乐互不干扰，空间音频算法如临国家大剧院现场。"
        ),
        technical_principles=[
            "施罗德声学散射体技术扩散全车高频声场",
            "独立双音区声场隔离算法与空间音频空间渲染引擎",
        ],
        advantages=[
            "主驾导航电话私密不外放，不打扰车内熟睡家人",
            "中低频震撼沉浸，2080W超强推力爆棚动感",
        ],
        limitations=[
            "高规格25扬声器版本多为中高配标配或选装",
        ],
        sub_variants={},
        representative_vehicles=["问界M9", "享界S9", "智界S7", "智界R7"],
        standard_labels=["HUAWEI SOUND", "星环散射体", "7.1.4全景声", "头枕独立音响", "空间音频", "歌剧院级音质"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "播放音乐并拨通电话演示：‘电话接通后只有主驾驶头枕能听见，旁边和后排完全听不到通话内容，隐私安全两不误！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 12. HUAWEI MagLink 车载魔吸扩展生态
    TechnologyEntity(
        id="hima_maglink",
        name="HUAWEI MagLink 车载平板魔吸互联接口",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HUAWEI MagLink Magnetic In-Car Tablet Ecosystem",
        category=TechCategory.COCKPIT_OS,
        subcategory="后排磁吸拓展接口与全车无感联控",
        aliases=[
            "maglink",
            "车载魔吸",
            "华为maglink",
            "后排吸附平板",
            "平板变车机",
        ],
        summary="前排座椅靠背磁吸接口，华为MatePad平板咔嗒一吸即刻化身车载控制娱乐屏，支持车机跨屏协同控车与熄火带走。",
        description=(
            "前排座椅背后配备标准MagLink磁吸接口，支持27W大功率无线充电与高速数据通信。"
            "平板吸附后立刻进入鸿蒙车载副屏模式，支持后排乘客调节座椅加热、空调风向、点播儿童动画，熄火一拔直接带走当作个人办公平板。"
        ),
        technical_principles=[
            "高强钕铁硼磁吸定位与Pogo-Pin低阻抗高速总线传输",
            "鸿蒙分布式软总线多设备端点即插即用自动组网",
        ],
        advantages=[
            "彻底告别传统车企固定的老旧后排大屏，硬件随平板升级代代更新不过时",
            "前排父母可一键锁屏后排平板，控制孩子看屏幕时间与音量",
        ],
        limitations=[
            "专属磁吸外壳与华为平板需按需配合使用",
        ],
        sub_variants={},
        representative_vehicles=["问界M9", "问界M7", "智界R7", "享界S9"],
        standard_labels=["HUAWEI MagLink", "平板变车机", "磁吸拓展", "后排娱乐屏", "儿童关怀"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "向带娃家庭强力安利：‘不用花几万选装死板的车载后排屏，自己的华为平板咔嗒一吸就是后排屏，孩子下车还能拿去上画画课，太机智了！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 13. HUAWEI XPIXEL 百万像素智慧双反射投影大灯
    TechnologyEntity(
        id="hima_smart_lights_xpixel",
        name="HUAWEI XPIXEL 百万像素智慧投影大灯",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HUAWEI XPIXEL Million-Pixel Smart Projection Headlights",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="高精微米级车灯投影与示宽光毯交互",
        aliases=[
            "xpixel",
            "百万像素大灯",
            "华为大灯",
            "智慧投影大灯",
            "车道示宽光毯",
            "户外露天投影",
        ],
        summary="集成了百万级微镜芯片的智慧大灯，不仅能在地面投射车宽动态光毯过窄道，还能在户外白墙投射百英寸电影户外放映。",
        description=(
            "采用双反空间光学系统与DLP数字微镜技术，照明分辨率达到百万像素级。在夜间过狭窄施工路段时，"
            "大灯在路面直接铺出与车身同宽的动态光毯，光毯能不能过车就能过；在野外露营更可作为高亮度户外投影仪放映大片。"
        ),
        technical_principles=[
            "DLP微镜阵列偏转高精度像素化控光",
            "前向避障传感器与车轮转向角联动动态光毯投影算法",
        ],
        advantages=[
            "夜间窄道窄桥‘看光毯就知道能不能过去’，杜绝剐蹭盲区",
            "支持投射斑马线礼让行人、变道光毯闪烁指引及节日专属迎宾灯语",
        ],
        limitations=[
            "仅配备于旗舰顶配车型（如问界M9）",
        ],
        sub_variants={},
        representative_vehicles=["问界M9", "享界S9"],
        standard_labels=["XPIXEL大灯", "百万像素投影", "示宽光毯", "礼让斑马线", "户外电影放映"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向客户演示大灯路面光毯：‘晚上过窄路最怕刮轮毂，大灯直接在地上投出两条车轮轨迹光毯，光毯不蹭路牙子车子绝对碰不到，新手开大车也安心！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 14. 华为 600kW 全液冷超快充架构
    TechnologyEntity(
        id="hima_megawatt_supercharger",
        name="华为 600kW 全液冷超快充体系",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HUAWEI 600kW Full Liquid-Cooled Supercharging System",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="兆瓦级液冷极速桩端补能体系",
        aliases=[
            "华为全液冷超充",
            "600kw超充",
            "一秒一公里",
            "液冷充电枪",
            "华为超充桩",
        ],
        summary="最大输出功率达600kW、最大电流600A的超快充体系，枪线仅重2公斤单手轻松提起，实现‘一秒一公里’极速补能。",
        description=(
            "彻底颠覆传统风冷充电桩笨重发热痛点。全模块全液冷循环带走巨大热量，充电电缆极细极轻，女生单手即可轻松插拔；"
            "在巨鲸800V高压车型上实现充电5分钟补能超200公里，喝口水的时间即可满电出发。"
        ),
        technical_principles=[
            "动力电源模块与充电终端全液冷循环散热架构",
            "大电流高耐压液冷电缆与智能热监控闭环",
        ],
        advantages=[
            "一秒一公里充电速度冠绝行业，极大提升长途通勤效率",
            "充电枪极其轻便，静音运行无传统风冷桩震耳欲聋的风扇轰鸣",
        ],
        limitations=[
            "需在已布局华为液冷超充站的高速与核心商圈网点使用",
        ],
        sub_variants={},
        representative_vehicles=["智界S7", "问界M9纯电", "享界S9", "智界R7"],
        standard_labels=["全液冷超充", "600kW功率", "一秒一公里", "单手轻便插枪", "极速补能"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "打消充电焦虑：‘全国都在加速铺设华为600kW全液冷超充，一秒充一公里，充一杯咖啡的时间就能跑几百公里，跟加油一样快！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 15. 鸿蒙座舱超级桌面与手机生态流转
    TechnologyEntity(
        id="hima_super_desktop",
        name="HarmonyOS 车机超级桌面与无缝流转",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HarmonyOS Super Desktop & Cross-Device App Streaming",
        category=TechCategory.COCKPIT_OS,
        subcategory="手机应用百万生态无缝投射车机",
        aliases=[
            "超级桌面",
            "手机应用上车",
            "鸿蒙流转",
            "碰一碰流转",
            "微信定位上车",
        ],
        summary="手机海量应用免安装直接上车，手机聊天、短视频、办公文档上车大屏无缝接力继续，双端数据安全隔离。",
        description=(
            "依托鸿蒙分布式软总线协议，手机里的数百万APP无需在车机上重新下载安装，上车直接显示在车机‘超级桌面’中。"
            "手机收到微信定位，手机贴一下中控屏立刻自动开启车机高德大屏导航；手机听了一半的歌，上车自动接力从车内扬声器播放。"
        ),
        technical_principles=[
            "分布式任务调度与虚拟外设抽象层（Virtual Hardware）",
            "点对点极低时延Wi-Fi 6并发视频流传输",
        ],
        advantages=[
            "车机APP永远最新，无需等待车机版APP缓慢的更新适配周期",
            "办公、娱乐、导航完全跨端连贯，体验极佳",
        ],
        limitations=[
            "主要针对华为鸿蒙智能手机平板生态设备",
        ],
        sub_variants={},
        representative_vehicles=["问界全系", "智界全系", "享界S9", "阿维塔全系"],
        standard_labels=["超级桌面", "无缝流转", "碰一碰导航", "分布式软总线", "海量APP"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "现场演示给客户看：‘朋友在微信里发了个聚会餐厅定位，手机在车机碰一下，大屏立刻开始导航，不用自己手忙脚乱在车机上打字搜地址！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 16. 华为零重力悬浮减压座椅系统
    TechnologyEntity(
        id="hima_zero_gravity_seat",
        name="华为智能双零重力舒享减压座椅",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HUAWEI Dual Zero-Gravity Suspension Seat System",
        category=TechCategory.COCKPIT_OS,
        subcategory="符合NASA人体工学的悬浮躺平座椅",
        aliases=[
            "零重力座椅",
            "问界零重力",
            "双零重力座椅",
            "零重力副驾",
            "一键躺平",
            "后排零重力",
        ],
        summary="符合NASA航天标准的零重力减压座椅，支持躯干大腿113度黄金夹角一键悬浮躺平，全身肌肉彻底放松卸力。",
        description=(
            "不同于普通汽车座椅的靠背放倒，零重力座椅通过多连杆电机让坐垫与靠背协同上扬后仰，使心脏与膝盖处于同一水平线，"
            "血液循环更畅快，压力均匀分散到整张座椅。配备双向电动腿托与SPA级十六点气动按摩，长途自驾如躺在太空舱。"
        ),
        technical_principles=[
            "NASA航天失重姿态人体工学曲线几何建模",
            "座椅安全气囊防下潜锁止与碰撞毫秒级自回复机构",
        ],
        advantages=[
            "全身骨骼和关节处于无压状态，中途服务区休息15分钟即可迅速恢复充沛精力",
            "副驾与第二排均可配备，给伴侣和长辈最极致的尊崇体验",
        ],
        limitations=[
            "零重力展开模式下会占用一定后排纵向腿部空间",
        ],
        sub_variants={},
        representative_vehicles=["问界M9", "问界M7", "智界R7", "享界S9"],
        standard_labels=["零重力座椅", "NASA航天减压", "一键躺平", "SPA气动按摩", "尊崇乘坐"],
        equivalence_group_id=None,
        sales_talking_points=[
            "邀请客户亲自躺上零重力座椅按下一键舒享：‘闭上眼睛感受一下，整个人就像浮在水面上一样完全不压腰，跑长途老婆孩子能在车里睡个香甜大觉！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 17. HUAWEI xHUD AR-HUD 增强现实抬头显示
    TechnologyEntity(
        id="hima_panoramic_hud",
        name="HUAWEI xHUD AR-HUD 增强现实抬头显示系统",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HUAWEI xHUD Augmented Reality Head-Up Display",
        category=TechCategory.COCKPIT_OS,
        subcategory="75英寸超大画幅三维车道级全息投影",
        aliases=[
            "xhud",
            "华为ar-hud",
            "75英寸hud",
            "临境抬头显示",
            "问界hud",
        ],
        summary="投影画幅高达75英寸的超大AR-HUD系统，12000nit强光自适应亮度，不仅显示车道级指引，驻车时还能投射巨幕看电影。",
        description=(
            "采用华为自研自适应局部调光算法与车规级成像模组，解决传统HUD重影、眩晕和阳光直射看不清的痛点。"
            "行车时将安全辅助信息、车道偏离、夜视行人框精准贴合在前方8.5米路面上；露营驻车时甚至可作为巨幕影院在挡风玻璃上看高清大片。"
        ),
        technical_principles=[
            "高对比度自研光机与抗眩光光学反射曲面镜组",
            "自研畸变校正算法与动态追踪IMU实时贴地渲染",
        ],
        advantages=[
            "画幅高达75英寸业界最大之一，科技感极度震撼",
            "强光烈日下清晰可见，戴偏光镜也能清晰识别",
        ],
        limitations=[
            "前风挡需特殊镀膜专用玻璃配合使用",
        ],
        sub_variants={},
        representative_vehicles=["问界M9", "享界S9"],
        standard_labels=["HUAWEI xHUD", "75英寸AR-HUD", "车道级贴地指引", "驻车观影", "防眩晕HUD"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "让客户体验75英寸超大画幅：‘前方8米处直接铺开一个75寸大屏幕，连周围车道的盲区障碍物都在上面标注得一清二楚，开车就像在开战斗机！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 18. 星闪 NearLink 超低时延无线车载连接技术
    TechnologyEntity(
        id="hima_nearlink_sparklink",
        name="华为星闪 NearLink 车载无线连接技术",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HUAWEI NearLink Ultra-Low Latency Automotive Wireless Tech",
        category=TechCategory.COCKPIT_OS,
        subcategory="短距微秒级高抗干扰无线通信架构",
        aliases=[
            "星闪",
            "nearlink",
            "华为星闪",
            "星闪车钥匙",
            "车载星闪",
            "低时延无线",
        ],
        summary="中国主导的新一代短距无线通信技术，时延低至蓝牙的三十分之一，抗干扰能力提升7dB，带来分米级无感测距钥匙体验。",
        description=(
            "星闪技术（NearLink）集成5G Polar码与短距微秒级调度，彻底解决传统车载蓝牙钥匙靠近不解锁、离车不落锁及多设备断连卡顿问题。"
            "在车内更可用于无线麦克风K歌零延迟对嘴、无线游戏手柄极速操作及车机高清音视频微秒级无损传输。"
        ),
        technical_principles=[
            "SLB基础接入与SLE低功耗接入双模式架构",
            "5G软技术下沉短距通信，高并发抗多径衰落",
        ],
        advantages=[
            "时延低至微秒级，车载K歌完全听不出耳返延迟",
            "数字钥匙精准度提升至分米级，走近车门秒开，绝不罚站",
        ],
        limitations=[
            "需搭配支持星闪协议的华为手机或车规外设终端",
        ],
        sub_variants={},
        representative_vehicles=["问界M9", "智界S7", "享界S9", "智界R7"],
        standard_labels=["星闪NearLink", "微秒级时延", "星闪钥匙", "K歌零延迟", "高抗干扰"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "对比传统老蓝牙钥匙：‘很多电车走近车门半天不开、在门外尴尬罚站，华为星闪钥匙靠近0.1秒瞬间解锁，车内无线麦克风K歌一点延迟都没有！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 19. 享界全铝智能底盘架构 (Stelato)
    TechnologyEntity(
        id="hima_stelato_platform",
        name="享界行政级豪华底盘与纯平座舱架构",
        brand="鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HIMA Stelato Executive Luxury Chassis & Flat-Floor Platform",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="5.16米豪华行政级轿车高端底盘",
        aliases=[
            "享界平台",
            "享界底盘",
            "享界s9底盘",
            "stelato",
            "享界纯平座舱",
        ],
        summary="北汽与华为联合打造的高端行政旗舰轿车平台，全铝合金前后悬架配合同级最大纯平乘员舱空间与双零重力后排。",
        description=(
            "专为高端商务行政行政座驾设计（首款车型享界S9）。前双叉臂+后多连杆均采用全铝锻造工艺，轻量化簧下质量优异；"
            "搭配华为巨鲸超薄高压电池，实现轿跑流线低风阻造型与同级别最优车内得房率，后排空间可舒坦翘起二郎腿。"
        ),
        technical_principles=[
            "高比例全铝合金轻量化前后轴副车架",
            "超薄电池下沉式布局释放纯平后排地板",
        ],
        advantages=[
            "车长5.16米但转弯灵活贴地，行政后舱得房率达67%行业顶级",
            "全系标配闭式空簧+CDC阻尼，静音与高级厚重感媲美奔驰S级",
        ],
        limitations=[
            "超长车身在紧凑老旧小区极窄路侧车位停车需借助自动泊车",
        ],
        sub_variants={},
        representative_vehicles=["享界S9"],
        standard_labels=["享界底盘", "全铝悬架", "行政座驾", "纯平座舱", "超高得房率"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "面向高端政企商务客户：‘买50万的享界S9，享受的是百万级奔驰S级和迈巴赫的后排乘坐空间与国宾级底盘静谧性！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 20. 华为盘古大模型小艺车载智能助手
    TechnologyEntity(
        id="hima_smart_cockpit_celia",
        name="华为盘古大模型小艺车载超级助手",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HUAWEI Pangu LLM-Powered Celia In-Car Assistant",
        category=TechCategory.COCKPIT_OS,
        subcategory="千亿大模型生成式拟人AI车控语音",
        aliases=[
            "小艺助手",
            "盘古大模型车机",
            "小艺大模型",
            "华为语音助手",
            "小艺懂车帝",
        ],
        summary="接入华为盘古大模型的车载智慧大脑，具备超强车辆全功能懂车问答、模糊意图理解与多意图一句话连环车控。",
        description=(
            "不只是简单的‘打开车窗’机械式命令识别。车主随口说一句‘有点热但别吹到头’，小艺自动调节避人出风口与合适温度；"
            "车主询问‘副驾后视镜怎么调’，小艺直接在大屏上弹出车辆3D动态说明书并高亮操作按钮，是车主的随行贴身汽车专家。"
        ),
        technical_principles=[
            "盘古千亿汽车领域专业知识大模型微调推理",
            "全车多模态感知意图理解与深层整车CAN总线动作编排",
        ],
        advantages=[
            "支持一句话说出5个复杂指令依次执行无卡顿",
            "百科知识浩瀚无所不知，陪孩子聊天讲故事活灵活现",
        ],
        limitations=[
            "深度专业知识生成依赖车机网络连接通畅",
        ],
        sub_variants={},
        representative_vehicles=["问界全系", "智界全系", "享界S9"],
        standard_labels=["小艺大模型", "盘古大模型", "模糊意图车控", "智能车载问答", "随车专家"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "现场随意说话测试小艺：‘跟小艺说一句“我抽根烟”，它会自动把天窗翘起一条缝、主驾车窗微开、空气净化器开启，这才是真正的懂你！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 21. 华为全天候热管理系统与跨域五合一集成
    TechnologyEntity(
        id="hima_thermal_cross_domain",
        name="华为整车跨域全气候集成热管理系统",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HUAWEI Cross-Domain All-Weather Integrated Thermal Management",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="座舱三电智驾全域余热高效调度体系",
        aliases=[
            "华为热管理",
            "五合一热管理",
            "跨域热管理",
            "智驾热管回收",
            "全气候热泵",
        ],
        summary="业内首创将高算力智驾域控芯片与激光雷达发热纳入全车热循环体系，冬季将芯片废热回收为座舱供暖与电池预热。",
        description=(
            "随着智驾芯片算力提升，激光雷达与域控制器运转时散发可观热量。华为将智能驾驶域、座舱域、电驱动域、电池域与空调回路五域打通，"
            "在冬天把原本直接排散到空气中的芯片发热回收为电池升温，降低全车冬季采暖电耗15%以上。"
        ),
        technical_principles=[
            "五域跨域多通冷却回路与集成多通道集成阀件",
            "智驾芯片与激光雷达热管高效热交换模块",
        ],
        advantages=[
            "把废热用到极致，冬季高速续航更扎实",
            "保证大算力智驾芯片在盛夏炎热工况下绝不因积热降频死机",
        ],
        limitations=[
            "冷却管路跨域集成度极高，冷却液保养需使用专用低导电配方",
        ],
        sub_variants={},
        representative_vehicles=["问界M9", "智界R7", "享界S9"],
        standard_labels=["华为热管理", "芯片余热回收", "五合一集成", "全天候热泵", "智驾散热"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "突出华为在通信设备散热领域的深厚底蕴：‘连激光雷达和超算芯片的热量都能回收来暖车，每一度电都不浪费，续航自然更扎实！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 22. 华为 C-V2X 车路协同与超视距安全预警
    TechnologyEntity(
        id="hima_v2x_fleet",
        name="华为 C-V2X 车路协同与超视距行车预警",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HUAWEI C-V2X Vehicle-to-Everything & NLOS Early Warning",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="蜂窝车联网超视距协同感知技术",
        aliases=[
            "v2x",
            "华为v2x",
            "车路协同",
            "红绿灯读秒",
            "超视距预警",
            "盲区会车预警",
        ],
        summary="通过车联网与智慧路口红绿灯、路侧雷达直连，在仪表盘上精准显示红绿灯读秒并在无保护盲区拐角提前预警来车。",
        description=(
            "突破车身传感器视距物理限制（遮挡死角、恶劣大雾）。通过蜂窝C-V2X网络直接与城市智慧交通信号机联动，"
            "车内仪表实时显示前方红绿灯剩余秒数与推荐通行绿波车速；在视野受阻的丁字路口提前数秒弹出‘对向有来车’超视距警示。"
        ),
        technical_principles=[
            "PC5直连与Uu蜂窝双模低时延V2X通信架构",
            "高精度微秒级时间同步与车道级拓扑地图空间匹配",
        ],
        advantages=[
            "过路口不用伸着脖子看红绿灯，车机直接读秒提示起步",
            "在鬼探头和遮挡路口极大降低由于盲区造成的突发碰撞危险",
        ],
        limitations=[
            "需所在城市智慧交通路侧设备数字化改造支持",
        ],
        sub_variants={},
        representative_vehicles=["问界M9", "问界M7", "阿维塔12"],
        standard_labels=["C-V2X", "红绿灯读秒", "超视距预警", "车路协同", "绿波车速"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "开到路口给客户看中控仪表：‘前面路口哪怕被大泥头车挡住了视线，仪表上红绿灯倒计时清清楚楚，还能告诉你保持多少时速能一路绿灯开过去！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 23. 华为双分区安全回滚无感 OTA 架构
    TechnologyEntity(
        id="hima_ota_dual_cell",
        name="华为双分区整车安全无感 OTA 架构",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HUAWEI Dual-Partition Seamless Rollback FOTA Architecture",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="全域A/B双镜像极速静默在线升级",
        aliases=[
            "双分区ota",
            "无感ota",
            "华为ota",
            "升级安全回滚",
            "后台静默升级",
        ],
        summary="采用电信级A/B双系统分区架构，行车时后台完全静默下载校验，升级中途即使断电也能一秒回滚绝不‘变砖’。",
        description=(
            "传统电车OTA升级往往需原地熄火停车等待三四十分钟，若遭遇断电可能死机趴窝。华为继承电信通信高可靠性标准，"
            "车机与全车数十个ECU采用双分区备份机制。升级在后台静默完成，锁车15分钟即可无声切换，升级失败自动回退，可靠性达99.999%。"
        ),
        technical_principles=[
            "A/B系统镜像双向热备与差分增量解压升级算法",
            "整车各域控制器安全证书校验与防篡改硬件根信任",
        ],
        advantages=[
            "升级过程完全不耽误车主日常用车，第二天上车就享用全新功能",
            "彻底杜绝系统升级‘变砖’拉板车的致命痛点",
        ],
        limitations=[
            "对整车存储芯片容量空间占用要求稍大",
        ],
        sub_variants={},
        representative_vehicles=["问界全系", "智界全系", "享界S9"],
        standard_labels=["双分区OTA", "无感升级", "安全回滚", "电信级可靠", "永不变砖"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向担心电车软件故障的传统车主保证：‘华为做通信基站几十年，电信级的安全标准做OTA，后台无感升级，即使升级一半拔掉电线也不会死机变砖！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 24. 享界 S9 旗舰纯平地台与行政四座系统
    TechnologyEntity(
        id="hima_executive_four_seats",
        name="享界 S9 首发后排零重力专属行政四座",
        brand="鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="Stelato S9 Executive Four-Seat Zero-Gravity System",
        category=TechCategory.COCKPIT_OS,
        subcategory="顶级国宾级后排行政奢享座舱",
        aliases=[
            "享界四座",
            "行政四座",
            "后排零重力",
            "电动遮阳帘",
            "行政中岛扶手",
        ],
        summary="首款配备量产后排零重力座椅的D级纯电轿车，配备后排扶手触控交互屏、专属车载冷暖冰箱与全车多向电动遮阳帘。",
        description=(
            "专为政商务顶峰领袖打造。后排行政座椅支持一键开启零重力模式，12向电动调节配合腰托腿托全面支撑；"
            "中央行政岛台集成冷暖双用压缩机冰箱（3℃-50℃恒温调节）与高精度触控屏，全车车窗配备双层遮阳隐私帘，营造极致私密尊贵国宾礼遇。"
        ),
        technical_principles=[
            "座椅水平滑移横向收折复合机械传动机构",
            "超静音微型直流变频车载压缩机制冷制热系统",
        ],
        advantages=[
            "后排尊贵舒适度完全越级对标迈巴赫S级与保时捷帕拉梅拉",
            "全车声学遮阳隐私闭环，隔绝一切外界窥探视线",
        ],
        limitations=[
            "四座版车型牺牲了后排中央第五个座位的应急载人能力",
        ],
        sub_variants={},
        representative_vehicles=["享界S9行政版"],
        standard_labels=["行政四座", "后排零重力", "车载冷暖冰箱", "电动隐私遮阳帘", "国宾礼遇"],
        equivalence_group_id=None,
        sales_talking_points=[
            "邀请商务老板坐进后排拉起遮阳帘打开按摩：‘把椅背放平、喝一杯冰镇香槟，外面完全看不见里面，这就是您移动的顶级商务会客厅！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 25. 问界 M9 超级三联屏与百万光瀑座舱
    TechnologyEntity(
        id="hima_triple_screen_cockpit",
        name="问界 M9 一体环宇三联屏与光瀑奢华座舱",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="AITO M9 Panoramic Triple-Screen & Starlight Ambient Cockpit",
        category=TechCategory.COCKPIT_OS,
        subcategory="全景三联一体化交互与光瀑氛围照明",
        aliases=[
            "三联屏",
            "问界三联屏",
            "问界m9大屏",
            "副驾娱乐屏",
            "光瀑氛围灯",
        ],
        summary="由12.3英寸全液晶仪表、15.6英寸2K中控大屏与16英寸副驾娱乐屏组成的一体化前排超宽三联屏，搭配无极光瀑氛围灯。",
        description=(
            "三块高清大屏完全嵌入在同一块高透光曲面玻璃下方，副驾娱乐屏支持独立蓝牙耳机音频与防窥视角设计，"
            "副驾看剧打游戏完全不影响主驾专注驾驶。配合随音乐节拍与车速流动的无级渐变星环光瀑氛围灯，奢华质感震撼视觉感官。"
        ),
        technical_principles=[
            "全贴合大尺寸低反射防指纹防爆前盖板玻璃",
            "三屏独立硬件渲染管线与跨屏无缝拖拽流转引擎",
        ],
        advantages=[
            "前排科技奢华感同级绝无仅有，各乘客娱乐办公互不干扰",
            "支持主驾将导航一键滑给中控，副驾将电影一键划给中控分享",
        ],
        limitations=[
            "前排大面积屏幕在夏季烈日下露天长时间暴晒中控台需注意防烫通风",
        ],
        sub_variants={},
        representative_vehicles=["问界M9全系"],
        standard_labels=["一体三联屏", "副驾专属娱乐", "防窥视屏幕", "光瀑氛围灯", "跨屏拖拽"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "向家庭男女主人同时展示：‘男主人开车看HUD和仪表，女主人在旁边16寸大屏上看热播剧，戴上耳机互不影响，长途再也不无聊！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 26. 智界 R7 鸿蒙超能空间与电吸电弹前备箱
    TechnologyEntity(
        id="hima_electric_frunk_space",
        name="智界 R7 超大电弹双击电吸前备箱与魔术空间",
        brand="鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="Luxeed R7 Smart Electric Frunk & Magic Space Architecture",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="轿跑SUV空间最大化与智能化车身开口",
        aliases=[
            "智界前备箱",
            "电弹前备箱",
            "双击开前盖",
            "敲击开前备箱",
            "电吸前备箱",
        ],
        summary="业内首创双击敲击车头机盖自动电弹开启的超大前备箱，支持全电控静音电吸关闭，配合轿跑溜背超大纵向头部空间。",
        description=(
            "传统前备箱开启往往需要在车内抠拉机械开关且盖上时要大力按压。智界R7前备箱支持手背双击机盖传感器自动电控弹起，"
            "容积高达数十升，放下一整个标准登机箱；轻按按键电吸静音闭合，彻底消除弄脏双手的烦恼。"
        ),
        technical_principles=[
            "车规级电容敲击微震动感应算法防误触机制",
            "微型电动撑杆与锁扣静音电吸自吸合电机",
        ],
        advantages=[
            "买菜或抱着箱子时用手肘或手背轻轻敲两下即开，极度优雅便捷",
            "溜背轿跑SUV外形下打破空间魔咒，后排头部腿部空间超越传统大SUV",
        ],
        limitations=[
            "极端严重撞击变形后需通过车内应急机械拉索开闭",
        ],
        sub_variants={},
        representative_vehicles=["智界R7", "智界S7"],
        standard_labels=["电弹前备箱", "敲击开启", "电吸关闭", "魔术大空间", "优雅开盖"],
        equivalence_group_id=None,
        sales_talking_points=[
            "现场演示双击敲车头：‘看！手里拿着外卖或者行李，手肘在机盖轻轻敲两下，前盖自动优雅升起，放进去轻轻一点自动电吸关上，手上干干净净！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 27. 问界 M9 车载 32 英寸光场升降巨幕激光投影
    TechnologyEntity(
        id="hima_laser_projection_screen",
        name="问界 M9 车规级 32 英寸升降激光投影巨幕",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="AITO M9 In-Car 32-Inch Retractable Laser Projection Theater",
        category=TechCategory.COCKPIT_OS,
        subcategory="车规级防眩升降巨幕与后舱私享影院",
        aliases=[
            "32英寸巨幕",
            "车载投影",
            "升降投影幕布",
            "激光巨幕",
            "车内电影院",
        ],
        summary="全球首款量产车规级32英寸电动折叠升降投影幕布与超短焦激光投影核心，100%遮光私密，后排秒变顶级移动私享影院。",
        description=(
            "幕布平时隐藏在车顶B柱横梁内，一键开启后通过超静音电机缓缓降下，展开达32英寸超大纯平视野。"
            "采用高流明车规级三色激光投影核心，配合后排HUAWEI SOUND全景声与电动车窗隐私遮阳帘，后排乘员可躺着看4K电影、打主机游戏或召开私密视频会议。"
        ),
        technical_principles=[
            "车规级抗震微型激光光机与超短焦广角反光镜系统",
            "防眩光柔性抗光幕布与张力电动自动平整绷紧机构",
        ],
        advantages=[
            "相比传统吸顶固定折叠屏，32英寸巨幅画面彻底带来影院级包围感",
            "收起完全隐藏平整，丝毫不遮挡全景天幕采光与车内通透视野",
        ],
        limitations=[
            "幕布降下后内后视镜无法通过传统镜面观察后方，需依赖流媒体后视镜",
        ],
        sub_variants={},
        representative_vehicles=["问界M9选装/高配"],
        standard_labels=["32英寸巨幕", "车载激光投影", "移动私享影院", "电动升降幕布", "后舱私密影音"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "带客户坐进后排按下观影模式：‘幕布自动降下、遮阳帘全关、音响变成全景声，32寸巨大屏幕在眼前亮起，这绝对是全家出游和商务接待的绝对王牌！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 28. 华为动态光影全场景交互迎宾灯语
    TechnologyEntity(
        id="hima_smart_projection_lights",
        name="鸿蒙智行全场景交互迎宾灯语矩阵",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="HIMA Full-Scenario Dynamic Interactive Welcome Light Matrix",
        category=TechCategory.COCKPIT_OS,
        subcategory="车外微米级灯光情景交互与艺术投影",
        aliases=[
            "智能灯语",
            "迎宾光毯",
            "凤舞九天灯语",
            "鲲鹏展翅",
            "车外交互灯",
        ],
        summary="结合前大灯与后贯穿尾灯矩阵，实现‘鲲鹏展翅’、‘凤舞九天’等多种艺术迎宾动态灯语投影，节日时支持自定义表白祝福语。",
        description=(
            "利用全车数千颗独立控光LED与智能大灯微镜，车主走近车辆时，车头大灯与地面光毯缓缓展开‘鲲鹏展翅’华丽光影迎宾；"
            "遇到情人节、生日等特殊节日，车灯可直接在地面投射爱心浪漫图案与‘生日快乐’定制动画，赋予汽车前所未有的情感温度。"
        ),
        technical_principles=[
            "高频PWM灰阶控制器与三维动画图形渲染引擎",
            "车端UWB位置感应触发与情景状态机自动匹配",
        ],
        advantages=[
            "极致仪式感与情绪价值，深受家庭与年轻用户喜爱",
            "倒车时尾灯矩阵可向后方行人投射‘倒车中请注意’文字提醒安全",
        ],
        limitations=[
            "定制动画需在中控屏或手机APP上提前下载或配置",
        ],
        sub_variants={},
        representative_vehicles=["问界M9", "享界S9", "智界S7"],
        standard_labels=["迎宾灯语", "鲲鹏展翅", "地面投影", "情绪价值", "交互尾灯"],
        equivalence_group_id=None,
        sales_talking_points=[
            "晚上带着客户看车钥匙靠近时的灯光秀：‘看这鲲鹏展翅的动态光影在大灯和地面上流动，每次回家下班停车，车子都在用最热烈的仪式感迎接你！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 29. 问界智能增程电驱系统 (增程器与发电机高匹配)
    TechnologyEntity(
        id="hima_extended_range_powertrain",
        name="问界增程智能电驱与高静音发动机总成",
        brand="华为 / 鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="AITO Intelligent Extended-Range EV Powertrain",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="高热效率增程发电机与无感启停",
        aliases=[
            "问界增程",
            "华为增程系统",
            "1.5t深度米勒增程器",
            "无感增程启停",
            "综合续航1400km",
        ],
        summary="专为问界全系打造的智能增程系统，一升油发3.4度电以上，增程器启动无任何震动与噪音，CLTC综合续航超1400公里。",
        description=(
            "采用1.5T深度米勒循环专用增程器，最高热效率突破41%，发电机直连曲轴集成设计。"
            "配合智能发电策略，在电量充足或拥堵低速时完全纯电行驶，高速巡航时增程器启动转速与风噪胎噪重叠，车内乘员几乎完全感觉不到发动机启动。"
        ),
        technical_principles=[
            "深度米勒循环与高滚流比进气系统",
            "整车NVH声学封装与液压双悬置主动减振隔振阻尼",
        ],
        advantages=[
            "一升油发电达3.4kWh业内标杆，综合续航突破1400公里无里程焦虑",
            "增程器启停完全无感，车内静谧度同纯电车完全无异",
        ],
        limitations=[
            "长途高速以130km/h以上超速行驶时油耗较中低速略有增加",
        ],
        sub_variants={},
        representative_vehicles=["问界M9增程版", "问界M7", "问界M5"],
        standard_labels=["智能增程", "1.5T增程器", "一升油发3.4度电", "无感启停", "1400km续航"],
        equivalence_group_id=EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM,
        sales_talking_points=[
            "向纠结纯电续航的买家打消顾虑：‘平时在市区纯电开，一公里一毛钱；放假全家开长途，加满油满电1400公里，去哪儿都不用排队等充电！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 30. 尊界 S800 百万级全轮线控转向系统
    TechnologyEntity(
        id="hima_maextro_s800_chassis",
        name="尊界 S800 全轮线控主动转向系统",
        brand="鸿蒙智行 (HIMA)",
        brand_key="hima",
        english_name="Maextro S800 Steer-by-Wire & All-Wheel Steering Architecture",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="航空级冗余线控前转向与大角度后轮独立转向",
        aliases=[
            "尊界转向",
            "全轮线控转向",
            "尊界后轮主动转向",
            "尊界后轮转向",
            "航空级线控",
            "5.4米大车小转弯",
            "蟹行模式",
        ],
        summary="专为超5.4米尊界S800打造的航空级全线控转向系统，后轮转向角度达双向±8度以上，大型行政旗舰轿车转弯半径仅5.2米。",
        description=(
            "前轮线控转向取消机械转向管柱，方向盘手感由多重力反馈伺服电机模拟；后轴配备双电控大扭矩转向执行机构。"
            "低速反向偏转实现不可思议的超小转弯半径与蟹行斜向泊车，高速同向偏转使5.4米长车变道如平移般优雅从容，后排贵宾完全感受不到甩动。"
        ),
        technical_principles=[
            "双通道三冗余线控转向电控与双向无刷伺服电机",
            "全车身六自由度运动学协调与车速自适应后轮偏角算法",
        ],
        advantages=[
            "车长超5.4米的大型行政旗舰，转弯掉头比紧凑级A级小车还轻松灵活",
            "彻底隔绝烂路路面颠簸打手，方向盘手感轻盈精准、路感高级",
        ],
        limitations=[
            "顶级超豪华硬件架构，搭载于尊界S800百万旗舰序列",
        ],
        sub_variants={},
        representative_vehicles=["尊界S800"],
        standard_labels=["全轮线控转向", "±8度后轮转向", "蟹行变道", "5.2米转弯半径", "国宾行政转向"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_CHASSIS_STEERING,
        sales_talking_points=[
            "让超豪华商务客户放心尺寸问题：‘车长虽然超过5米4气场非凡，但后轮能主动打8度大角度，开起来转弯掉头比普通小车还要灵巧，大老板自己开或者司机开都极其省心！’",
        ],
        maturity=TechMaturity.PRE_RESEARCH,
    ),
]
